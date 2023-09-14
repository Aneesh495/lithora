"""Training harness for the spherical graph residual model (L06, L16, L18).

This trains :class:`SphericalGraphResidual` from random initialisation to
predict the horizontal deformation residual at held-out stations. It exists to
provide the gate-G06 evidence: gradients and parameters change during training,
checkpoints save and reload atomically, and held-out inference improves over
the untrained model.

The input is a station network with observed velocities. We first remove the
rigid Euler-pole part (so the model learns only deformation) and build the
spherical graph and transport operators once. Training minimises the mean
squared residual-velocity error on the training nodes. Everything is
deterministic given a seed so ensemble members (L18) differ only by their
initialisation seed.

PyTorch is required here; the module imports lazily and raises a clear error
otherwise.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

import numpy as np

from .euler_fit import fit_euler_pole, predict_velocities
from .graph_model import _require_torch, build_transport_matrices, torch_available
from .transport import neighbor_features


@dataclass
class TrainResult:
    initial_loss: float
    final_loss: float
    param_delta_l2: float
    grad_norm_first_step: float
    n_params: int
    epochs: int


def _prepare(lat, lon, vel_en, cov_en, k):
    f = fit_euler_pole(lat, lon, vel_en, cov_en)
    rigid = predict_velocities(f.omega, lat, lon)
    residual = np.asarray(vel_en, float).reshape(-1, 2) - rigid
    edges, edge_feats = neighbor_features(lat, lon, k)
    transport = build_transport_matrices(lat, lon, edges)
    return f.omega, residual, edges, edge_feats, transport


def train_graph_model(
    lat,
    lon,
    vel_en,
    cov_en=None,
    train_mask=None,
    k: int = 6,
    hidden: int = 32,
    layers: int = 2,
    epochs: int = 300,
    lr: float = 1e-2,
    seed: int = 0,
    device: str = "cpu",
):
    """Train one model and return ``(model, context, TrainResult)``.

    ``context`` bundles the tensors needed for later inference so callers do
    not rebuild the graph. ``train_mask`` selects which nodes contribute to the
    loss; the rest are effectively held out.
    """
    _require_torch()
    import torch

    from .graph_model import SphericalGraphResidual, count_parameters

    torch.manual_seed(seed)
    np.random.seed(seed)

    omega, residual, edges, edge_feats, transport = _prepare(lat, lon, vel_en, cov_en, k)
    n = residual.shape[0]
    if train_mask is None:
        train_mask = np.ones(n, dtype=bool)

    dev = torch.device(device)
    res_t = torch.tensor(residual, dtype=torch.float32, device=dev)
    edges_t = torch.tensor(edges, dtype=torch.long, device=dev)
    ef_t = torch.tensor(edge_feats, dtype=torch.float32, device=dev)
    tr_t = torch.tensor(transport, dtype=torch.float32, device=dev)
    mask_t = torch.tensor(train_mask, dtype=torch.bool, device=dev)

    # Node init: zeros for state; the model infers residuals from structure.
    node_init = torch.zeros(n, 3, dtype=torch.float32, device=dev)
    neighbor_resid0 = torch.zeros(n, 2, dtype=torch.float32, device=dev)

    model = SphericalGraphResidual(hidden=hidden, layers=layers).to(dev)
    n_params = count_parameters(model)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    params_before = torch.cat([p.detach().flatten().clone() for p in model.parameters()])

    def forward():
        return model(node_init, edges_t, ef_t, tr_t, neighbor_resid0)

    model.train()
    initial_loss = None
    grad_norm_first = None
    for epoch in range(epochs):
        opt.zero_grad()
        pred = forward()
        loss = loss_fn(pred[mask_t], res_t[mask_t])
        loss.backward()
        if epoch == 0:
            initial_loss = float(loss.detach())
            grad_norm_first = float(
                torch.sqrt(sum((p.grad.detach() ** 2).sum() for p in model.parameters() if p.grad is not None))
            )
        opt.step()
    model.eval()
    with torch.no_grad():
        final_loss = float(loss_fn(forward()[mask_t], res_t[mask_t]).detach())

    params_after = torch.cat([p.detach().flatten().clone() for p in model.parameters()])
    delta = float(torch.linalg.norm(params_after - params_before))

    context = {
        "omega": omega,
        "node_init": node_init,
        "edges": edges_t,
        "edge_feats": ef_t,
        "transport": tr_t,
        "neighbor_resid0": neighbor_resid0,
        "lat": np.asarray(lat, float).reshape(-1),
        "lon": np.asarray(lon, float).reshape(-1),
        "device": device,
        "k": k,
    }
    result = TrainResult(
        initial_loss=initial_loss,
        final_loss=final_loss,
        param_delta_l2=delta,
        grad_norm_first_step=grad_norm_first,
        n_params=n_params,
        epochs=epochs,
    )
    return model, context, result


def predict_training_nodes(model, context):
    """Predict residual-corrected (east, north) velocities at all graph nodes."""
    import torch

    model.eval()
    with torch.no_grad():
        resid = model(
            context["node_init"],
            context["edges"],
            context["edge_feats"],
            context["transport"],
            context["neighbor_resid0"],
        ).cpu().numpy()
    rigid = predict_velocities(context["omega"], context["lat"], context["lon"])
    return rigid + resid


def save_checkpoint(path: str, model, context, result: TrainResult, extra: dict | None = None):
    """Atomically save model state plus the metadata needed to reproduce it.

    Writes to a temp file in the same directory and renames, so an interrupted
    save never leaves a half-written checkpoint that would silently corrupt a
    run.
    """
    import torch

    payload = {
        "model_state": model.state_dict(),
        "omega": context["omega"],
        "lat": context["lat"],
        "lon": context["lon"],
        "k": context["k"],
        "result": result.__dict__,
        "extra": extra or {},
        "format_version": 1,
    }
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    os.close(fd)
    torch.save(payload, tmp)
    os.replace(tmp, path)


def load_checkpoint(path: str):
    """Load a checkpoint saved by :func:`save_checkpoint`."""
    import torch

    from .graph_model import SphericalGraphResidual

    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = SphericalGraphResidual()
    model.load_state_dict(payload["model_state"])
    model.eval()
    return model, payload
