# Uncertainty calibration

A prediction without a trustworthy uncertainty is only half a result. This note
reports where Lithora's uncertainty holds and, more importantly, where it does
not.

## What we measure

For the Gaussian-process residual model, which returns a predictive standard
deviation, we check interval coverage: the fraction of held-out velocity
components that fall within one predicted standard deviation of the truth. A
well-calibrated 1-sigma interval covers about 68 percent. We measure this on
the spatially buffered folds, not on the training stations, because coverage on
training data is meaningless.

## The finding: overconfidence under spatial structure

On the California transform margin the GP's mean 1-sigma coverage is about
0.09, far below the nominal 0.68. The GP is badly overconfident there. The
reason is structural and worth stating plainly: the squared-exponential kernel
assumes a smooth stationary field, but a transform margin has a sharp velocity
gradient across the fault. Held-out stations across the buffer from their
nearest training neighbours sit in exactly the regime the kernel underestimates,
so the intervals are too tight.

This is the concrete form of a general warning: coverage guarantees that rely
on exchangeability do not transfer automatically to a new region with different
covariate structure. A model calibrated on a dense interior network will be
overconfident when asked about a sparsely sampled or strongly deforming margin.
Lithora measures this rather than assuming it away.

## Heteroscedastic versus epistemic

Two different uncertainties are in play and must not be merged. Heteroscedastic
noise is the per-station measurement uncertainty, which the GP absorbs through
the observation-noise term. Epistemic uncertainty is the model's ignorance away
from data, which the GP expresses as growing predictive variance far from
training stations. The error-versus-distance-to-network metric in the evaluator
exposes the epistemic part directly: error grows with distance to the nearest
training station, and a model whose intervals do not grow correspondingly is
overconfident in empty regions.

## Implication for claims

Because of the measured overconfidence, Lithora does not claim calibrated
prediction regions hold uniformly. It reports coverage by region and flags the
margin as a region where the intervals fail. A deep-ensemble treatment across
seeds (the learned model supports at least three independent seeds) is the route
to a more honest epistemic band, and the seed spread reported in note 11 is a
first look at that variance.

## Reproduce

```
python -m lithora.cli spatial-evaluate --frame IGS14 --region cal
```
