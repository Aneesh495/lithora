"""Original spherical graph residual model (capability L16).

The model predicts the horizontal deformation residual (the part of a station
velocity not explained by the rigid Euler pole) at each station from its
neighbourhood. Its design choices are what make it a geometry-aware model
rather than a lat/lon curve fit:

* Every vector quantity lives in a *local tangent frame* (east, north). The
  network never sees absolute longitude or a raw Cartesian direction, so a
  global rotation of the coordinate system does not change its predictions
  beyond the corresponding rotation of the outputs. This is the rotational
  equivariance checked in :mod:`tests` and in gate G09.
* Messages transport a neighbour's residual into the centre's frame by
  parallel transport before mixing, so the model compares vectors correctly
  on the curved surface instead of adding east/north components that mean
  different directions at different places.
* The graph is the k-nearest-neighbour graph on great-circle distance, and
  edge features are the neighbour's tangent-frame offset and distance, which
  are invariant to global rotation.

Only the message and update weights are learned; the geometry (frames,
transport, log map) is fixed. Training is from random initialisation.

PyTorch is an optional dependency. Importing this module without torch raises
a clear error so the rest of the package keeps working on a torch-free install.
"""

from __future__ import annotations

import numpy as np

try:  # pragma: no cover - exercised by availability, not logic
    import torch
    import torch.nn as nn

    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    _HAS_TORCH = False


def torch_available() -> bool:
    """Whether PyTorch is importable in this environment."""
    return _HAS_TORCH


def _require_torch() -> None:
    if not _HAS_TORCH:
        raise ImportError(
            "the spherical graph model requires PyTorch; install the 'learn' "
            "extra: pip install -e '.[learn]'"
        )


if _HAS_TORCH:

    class SphericalGraphResidual(nn.Module):
        """Message-passing residual predictor on a spherical kNN graph.

        Parameters
        ----------
        hidden:
            Hidden width of the message and update MLPs.
        layers:
            Number of message-passing rounds.
        """

        def __init__(self, hidden: int = 32, layers: int = 2):
            super().__init__()
            self.layers = layers
            # Node state carries a 2-vector (the current residual estimate in
            # the node's tangent frame) plus a scalar confidence-like feature.
            self.node_dim = 3
            # Message MLP input: neighbor state (3) transported residual (2) +
            # edge features (3) = 8.
            self.msg = nn.Sequential(
                nn.Linear(self.node_dim + 2 + 3, hidden),
                nn.SiLU(),
                nn.Linear(hidden, hidden),
                nn.SiLU(),
                nn.Linear(hidden, self.node_dim),
            )
            self.update = nn.Sequential(
                nn.Linear(self.node_dim * 2, hidden),
                nn.SiLU(),
                nn.Linear(hidden, self.node_dim),
            )
            # Read out a 2-vector residual (east, north) from the node state.
            self.readout = nn.Linear(self.node_dim, 2)

        def forward(
            self,
            node_init: "torch.Tensor",  # (n, node_dim)
            edges: "torch.Tensor",  # (m, 2) long
            edge_feats: "torch.Tensor",  # (m, 3)
            transport: "torch.Tensor",  # (m, 2, 2) rotation of neighbor frame->center frame
            neighbor_resid: "torch.Tensor",  # (n, 2) current residual estimate per node
        ) -> "torch.Tensor":
            n = node_init.shape[0]
            state = node_init
            src = edges[:, 1]
            dst = edges[:, 0]
            for _ in range(self.layers):
                # Transport each neighbor's residual estimate into the center frame.
                nb_resid = neighbor_resid[src]  # (m, 2)
                transported = torch.einsum("mij,mj->mi", transport, nb_resid)  # (m, 2)
                msg_in = torch.cat([state[src], transported, edge_feats], dim=1)
                messages = self.msg(msg_in)  # (m, node_dim)
                agg = torch.zeros(n, self.node_dim, dtype=state.dtype, device=state.device)
                agg.index_add_(0, dst, messages)
                # Normalise by degree.
                deg = torch.zeros(n, 1, dtype=state.dtype, device=state.device)
                deg.index_add_(0, dst, torch.ones(dst.shape[0], 1, dtype=state.dtype, device=state.device))
                agg = agg / deg.clamp_min(1.0)
                state = state + self.update(torch.cat([state, agg], dim=1))
                neighbor_resid = self.readout(state)
            return self.readout(state)

    def count_parameters(model: "SphericalGraphResidual") -> int:
        """Number of trainable parameters, used to prove the model has weights."""
        return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_transport_matrices(lat, lon, edges) -> np.ndarray:
    """Per-edge 2x2 rotation mapping a neighbor's east/north frame to the
    center's east/north frame, via parallel transport.

    For each edge (center i, neighbor j) we transport the neighbor's east and
    north basis vectors to i's tangent plane and express them in i's frame.
    The result is a proper rotation (plus possible reflection handled by the
    transport), applied to a neighbor residual to compare it in i's frame.
    """
    from .sphere import latlon_to_unit
    from .transport import parallel_transport, tangent_frame

    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    pos = latlon_to_unit(lat, lon)
    mats = np.zeros((len(edges), 2, 2))
    for e, (i, j) in enumerate(edges):
        ei, ni = tangent_frame(pos[i])
        ej, nj = tangent_frame(pos[j])
        tej = parallel_transport(pos[j], pos[i], ej)
        tnj = parallel_transport(pos[j], pos[i], nj)
        # Columns: image of neighbor east, image of neighbor north, in i frame.
        mats[e, 0, 0] = np.dot(tej, ei)
        mats[e, 1, 0] = np.dot(tej, ni)
        mats[e, 0, 1] = np.dot(tnj, ei)
        mats[e, 1, 1] = np.dot(tnj, ni)
    return mats
