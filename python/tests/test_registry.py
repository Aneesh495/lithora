"""Tests for the research registry."""

import json
import os

import numpy as np

from lithora.evaluate import spatial_block_folds
from lithora.registry import RegistryEntry, station_ids_for_folds


def test_station_ids_for_folds_records_exact_holdouts():
    rng = np.random.default_rng(0)
    lat = rng.uniform(30, 40, 60)
    lon = rng.uniform(-120, -110, 60)
    ids = [f"ST{i:03d}" for i in range(60)]
    folds = spatial_block_folds(lat, lon, n_folds=4, buffer_deg=0.5, seed=1)
    mapping = station_ids_for_folds(ids, folds)
    # Every held-out id is a real station id, and folds are disjoint in test.
    all_test = [sid for v in mapping.values() for sid in v]
    assert all(sid in ids for sid in all_test)
    assert len(all_test) == len(set(all_test)), "test sets must be disjoint"


def test_registry_entry_round_trip(tmp_path):
    entry = RegistryEntry(
        experiment="graph_vs_rigid",
        frame="IGS14",
        region="cal",
        seed=2,
        model="SphericalGraphResidual",
        hyperparameters={"hidden": 32, "layers": 2, "epochs": 300, "lr": 0.01, "k": 6},
        regularizers={"weight_decay": 0.0},
        n_folds=5,
        buffer_deg=0.3,
        holdout_station_ids={0: ["ST001", "ST002"], 1: ["ST010"]},
        notes="diagnostic profile",
    )
    path = entry.write(out_dir=str(tmp_path))
    assert os.path.exists(path)
    loaded = json.load(open(path))
    assert loaded["seed"] == 2
    assert loaded["hyperparameters"]["hidden"] == 32
    assert loaded["holdout_station_ids"]["0"] == ["ST001", "ST002"]
