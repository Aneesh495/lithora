"""Research registry (capability L35).

A reproducible study must record exactly what was run: the seeds, the model
hyperparameters and regularizers, the spatial folds, and the precise identities
of the held-out stations. Without the held-out identities, a later reader
cannot check that a reported score was truly out of sample. This module writes
a registry entry capturing all of that for one experiment run, so the figures
in the research notes trace to an exact configuration and station set.

The registry is written under `runs/registry/` (gitignored, since it can be
large and is regenerated), and a small summary can be committed when it is part
of final evidence.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field


@dataclass
class RegistryEntry:
    """One experiment run's full, reproducible configuration."""

    experiment: str
    frame: str
    region: str
    seed: int
    model: str
    hyperparameters: dict
    regularizers: dict
    n_folds: int
    buffer_deg: float
    # The decisive part: the exact station identities held out per fold.
    holdout_station_ids: dict[int, list[str]] = field(default_factory=dict)
    created_unix: float = field(default_factory=time.time)
    notes: str = ""

    def write(self, out_dir: str = "runs/registry") -> str:
        os.makedirs(out_dir, exist_ok=True)
        name = f"{self.experiment}_{self.region}_seed{self.seed}_{int(self.created_unix)}.json"
        path = os.path.join(out_dir, name)
        with open(path, "w") as fh:
            json.dump(asdict(self), fh, indent=2, sort_keys=True)
        return path


def station_ids_for_folds(station_ids, folds) -> dict[int, list[str]]:
    """Map each fold index to the ids of its held-out (test) stations.

    ``station_ids`` is the list of ids in the same order as the arrays passed
    to the fold builder; ``folds`` are the Fold objects from
    ``evaluate.spatial_block_folds``. Recording ids (not just indices) means
    the holdout set is reproducible even if the station ordering changes.
    """
    out: dict[int, list[str]] = {}
    for i, f in enumerate(folds):
        out[i] = [station_ids[j] for j in f.test_idx]
    return out
