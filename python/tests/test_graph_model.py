"""Tests for the learned graph model: gradients, checkpointing, and
rotational equivariance (gates G06 and G09).

Skipped cleanly when PyTorch is not installed so the suite still runs on a
torch-free environment.
"""

import os

import numpy as np
import pytest

from lithora.graph_model import torch_available
from lithora.synthetic import make_rigid_plate

pytestmark = pytest.mark.skipif(not torch_available(), reason="PyTorch not installed")


def _world(seed=0):
    return make_rigid_plate(
        n_stations=120,
        pole_lat_deg=45.0,
        pole_lon_deg=-100.0,
        rate_deg_per_myr=0.6,
        region_center=(38.0, -110.0),
        region_half_width_deg=10.0,
        noise_mm_yr=0.3,
        seed=seed,
        deform_fraction=0.35,
        deform_amp_mm_yr=5.0,
    )


def test_training_changes_parameters_and_reduces_loss():
    from lithora.train import train_graph_model

    w = _world(1)
    _, _, res = train_graph_model(
        w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr, epochs=200, seed=1
    )
    # Gates: parameters actually moved, gradient was nonzero, loss decreased.
    assert res.n_params > 100
    assert res.param_delta_l2 > 1e-4
    assert res.grad_norm_first_step > 0
    assert res.final_loss < res.initial_loss


def test_trained_beats_untrained_on_held_out():
    from lithora.train import predict_training_nodes, train_graph_model

    w = _world(2)
    n = w.lat_deg.size
    rng = np.random.default_rng(0)
    mask = rng.random(n) < 0.7  # 70% train, 30% held out

    model, ctx, _ = train_graph_model(
        w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr,
        train_mask=mask, epochs=250, seed=2,
    )
    pred = predict_training_nodes(model, ctx)

    # Untrained model with the same architecture/seed offset.
    untrained, uctx, _ = train_graph_model(
        w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr,
        train_mask=mask, epochs=0, seed=2,
    )
    upred = predict_training_nodes(untrained, uctx)

    held = ~mask
    truth = w.truth_vel_en_mm_yr
    trained_err = np.linalg.norm(pred[held] - truth[held], axis=1).mean()
    untrained_err = np.linalg.norm(upred[held] - truth[held], axis=1).mean()
    assert trained_err < untrained_err


def test_checkpoint_round_trip(tmp_path):
    from lithora.train import (
        load_checkpoint,
        predict_training_nodes,
        save_checkpoint,
        train_graph_model,
    )

    w = _world(3)
    model, ctx, res = train_graph_model(
        w.lat_deg, w.lon_deg, w.vel_en_mm_yr, w.cov_en_mm_yr, epochs=100, seed=3
    )
    pred_before = predict_training_nodes(model, ctx)

    path = os.path.join(tmp_path, "ckpt.pt")
    save_checkpoint(path, model, ctx, res)
    assert os.path.exists(path)

    loaded, payload = load_checkpoint(path)
    # Rebuild the inference context from the loaded metadata.
    from lithora.graph_model import build_transport_matrices
    from lithora.transport import neighbor_features
    import torch

    edges, edge_feats = neighbor_features(payload["lat"], payload["lon"], payload["k"])
    transport = build_transport_matrices(payload["lat"], payload["lon"], edges)
    n = payload["lat"].size
    ctx2 = {
        "omega": payload["omega"],
        "node_init": torch.zeros(n, 3),
        "edges": torch.tensor(edges, dtype=torch.long),
        "edge_feats": torch.tensor(edge_feats, dtype=torch.float32),
        "transport": torch.tensor(transport, dtype=torch.float32),
        "neighbor_resid0": torch.zeros(n, 2),
        "lat": payload["lat"],
        "lon": payload["lon"],
    }
    pred_after = predict_training_nodes(loaded, ctx2)
    assert np.allclose(pred_before, pred_after, atol=1e-5)


def test_rotational_equivariance_of_frame_features():
    # Gate G09 flavour at the geometry level: rotating the whole network about
    # the Earth's axis (a longitude shift) leaves the tangent-frame edge
    # features unchanged, so the model's inputs are rotation invariant and its
    # outputs rotate with the frame.
    from lithora.transport import neighbor_features

    w = _world(4)
    e1, f1 = neighbor_features(w.lat_deg, w.lon_deg, k=6)
    shifted_lon = (w.lon_deg + 37.0 + 180.0) % 360.0 - 180.0
    e2, f2 = neighbor_features(w.lat_deg, shifted_lon, k=6)
    # Same graph connectivity and same tangent-frame features.
    assert np.array_equal(e1, e2)
    assert np.allclose(f1, f2, atol=1e-9)
