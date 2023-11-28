"""Tests for the uncertainty budget."""

import numpy as np

from lithora.uncertainty import budget, distance_term, ensemble_spread


def test_ensemble_spread_zero_for_identical_members():
    preds = np.tile([2.0, -1.0], (5, 1))
    assert ensemble_spread(preds) == 0.0


def test_ensemble_spread_positive_for_varied_members():
    preds = np.array([[1.0, 0.0], [3.0, 0.0], [2.0, 0.0]])
    assert ensemble_spread(preds) > 0.0


def test_distance_term_grows_with_distance():
    near = distance_term(0.0, np.radians(3.0), 0.3, 1.0)
    far = distance_term(np.radians(9.0), np.radians(3.0), 0.3, 1.0)
    assert near == 0.3
    assert far > near
    # 9 degrees at 3-degree scale with growth 1 -> 0.3 + 3.0 = 3.3
    assert abs(far - 3.3) < 1e-9


def test_budget_does_not_sum_without_independence():
    preds = np.array([[1.0, 0.0], [2.0, 0.0]])
    b = budget(0.5, preds, dist_to_train_rad=np.radians(3.0), assume_independent=False)
    # Combined is the max component, not the quadrature sum.
    assert b.combined == max(b.aleatoric, b.epistemic_ensemble, b.epistemic_distance)
    assert not b.independent_assumed


def test_budget_quadrature_when_independent_asserted():
    preds = np.array([[1.0, 0.0], [2.0, 0.0]])
    b = budget(0.5, preds, dist_to_train_rad=0.0, assume_independent=True)
    expected = np.sqrt(b.aleatoric**2 + b.epistemic_ensemble**2 + b.epistemic_distance**2)
    assert abs(b.combined - expected) < 1e-9
    assert b.independent_assumed


def test_aleatoric_and_epistemic_kept_separate():
    preds = np.array([[5.0, 0.0], [5.0, 0.0]])  # zero ensemble spread
    b = budget(2.0, preds, dist_to_train_rad=0.0)
    # Aleatoric is reported independently of the (zero) epistemic spread.
    assert b.aleatoric == 2.0
    assert b.epistemic_ensemble == 0.0
