"""Uncertainty budget: separating the sources of velocity error (L18).

A plate-motion prediction carries error from several distinct sources, and
adding them as independent variances is only valid when they are actually
independent, which they often are not. This module makes the budget explicit
and keeps two categorically different kinds of uncertainty separate:

* Heteroscedastic (aleatoric) noise: the per-station measurement uncertainty,
  which varies by station and is reported by the data product. It does not
  shrink with more model capacity.
* Epistemic uncertainty: the model's ignorance, which grows away from data and
  can shrink with more or better-placed stations. We estimate it from the
  spread across an ensemble of independently seeded models and from the
  distance to the nearest training station.

The budget function returns the components separately and a combined estimate,
and it refuses to simply sum components that the caller has not asserted are
independent. This directly supports the heteroscedastic-versus-epistemic
separation the report requires.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class UncertaintyBudget:
    """Separated uncertainty components for a prediction, all in mm/yr.

    aleatoric:
        Per-component measurement noise std (heteroscedastic).
    epistemic_ensemble:
        Std across an ensemble of independently seeded predictions.
    epistemic_distance:
        A distance-to-network term that grows with how far the query is from
        the training stations.
    combined:
        A combined std. Components are combined in quadrature ONLY when the
        caller passes ``assume_independent=True``; otherwise the combined value
        is the maximum of the components, which does not assume independence.
    independent_assumed:
        Whether quadrature combination was used.
    """

    aleatoric: float
    epistemic_ensemble: float
    epistemic_distance: float
    combined: float
    independent_assumed: bool


def ensemble_spread(predictions: np.ndarray) -> float:
    """Std across an ensemble of predictions for one query.

    ``predictions`` has shape ``(n_members, 2)`` (east, north per member). We
    report the mean per-component standard deviation across members, which is
    the epistemic spread the ensemble exposes.
    """
    preds = np.asarray(predictions, float).reshape(-1, 2)
    if preds.shape[0] < 2:
        return 0.0
    return float(np.mean(np.std(preds, axis=0)))


def distance_term(dist_to_train_rad: float, scale_rad: float, floor: float, growth: float) -> float:
    """An epistemic term that grows with distance to the training network.

    It starts at ``floor`` mm/yr at zero distance and increases by ``growth``
    mm/yr per ``scale_rad`` of great-circle distance. This is a transparent,
    monotone model of extrapolation uncertainty, not a learned calibration; it
    is labelled as such and used only as a lower bound on epistemic error far
    from data.
    """
    return float(floor + growth * (dist_to_train_rad / max(scale_rad, 1e-9)))


def budget(
    aleatoric_mm_yr: float,
    ensemble_predictions: np.ndarray,
    dist_to_train_rad: float,
    distance_scale_deg: float = 3.0,
    distance_floor: float = 0.3,
    distance_growth: float = 1.0,
    assume_independent: bool = False,
) -> UncertaintyBudget:
    """Assemble the uncertainty budget from its separated sources."""
    epi_ens = ensemble_spread(ensemble_predictions)
    epi_dist = distance_term(
        dist_to_train_rad, np.radians(distance_scale_deg), distance_floor, distance_growth
    )
    comps = np.array([aleatoric_mm_yr, epi_ens, epi_dist])
    if assume_independent:
        combined = float(np.sqrt(np.sum(comps**2)))
    else:
        # Without an independence assumption, do not sum variances; use the
        # dominant component as a conservative combined estimate.
        combined = float(np.max(comps))
    return UncertaintyBudget(
        aleatoric=float(aleatoric_mm_yr),
        epistemic_ensemble=epi_ens,
        epistemic_distance=epi_dist,
        combined=combined,
        independent_assumed=assume_independent,
    )
