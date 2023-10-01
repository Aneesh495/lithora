# Robust Euler poles from GNSS velocities

## The problem

A rigid plate rotates about a single Euler pole. If a set of stations sits on
one rigid plate, their surface velocities all satisfy `v_i = omega x r_i` for a
common angular velocity `omega`. Estimating `omega` from the observed
velocities is the rigid inverse problem, and it is the baseline against which
every claim of deformation must be measured: a residual only means something
once the rigid part is removed correctly.

## Why it is linear

The cross product is linear in `omega`, so with the skew-matrix identity
`omega x r = -[r]_x omega` the model becomes a linear system `A omega = d`
after projecting each station's velocity onto its local east and north
directions (two rows per station). This matters in practice: there is no
iterative optimisation to get stuck, and the full covariance of the estimate
comes directly from the weighted normal matrix. The derivation is in
`docs/DERIVATIONS.md`.

## Weighting and conditioning

We weight each station by the inverse of its velocity covariance, so precise
stations count more. The condition number of the weighted normal matrix is
reported because it is the honest signal of identifiability: a network packed
into a small area, or strung along a line, leaves the rotation axis poorly
constrained. The code flags that as a large condition number rather than
returning a confident but meaningless pole. A synthetic test packs 50 stations
into a 5 km cluster and confirms the condition number explodes.

## Measured result on real data

Fitting the North America interior (1,374 IGS14 stations with at least five
years of data, latitude 32 to 49, longitude -104 to -85):

| Quantity | Value |
|---|---|
| Euler pole | 6.7 S, 88.3 W |
| Rate | 0.187 deg/Myr |
| Condition number | about 1.1e2 (well posed) |
| Median residual speed | 0.44 mm/yr |
| Median observed speed (IGS14) | 15.4 mm/yr |

A rigid rotation that collapses a 15 mm/yr field down to a sub-millimetre
median residual is the signature of a genuinely rigid interior, and it
validates the fit on real geodesy. The pole sits where published North America
relative to ITRF poles sit, at a southern latitude near 88 W with a rate close
to 0.19 deg/Myr.

## A caution on the uncertainty

The formal weighted uncertainty uses the MIDAS per-station velocity sigmas,
which are small. Those sigmas come from a robust trend estimator and do not
fully capture the correlated noise in daily series, so the formal pole
uncertainty is optimistic. Note 02 discusses the correlated-noise inflation we
apply when fitting raw series; for the velocity-product fit here we report the
condition number and residual scatter as the more trustworthy diagnostics.

## Reproduce

```
python -m lithora.cli fit-plates --frame IGS14 --region na
```
