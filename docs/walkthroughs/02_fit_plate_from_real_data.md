# Walkthrough: fitting a plate from real GNSS data

This traces the path from a cached MIDAS file to a rigid Euler pole on the
North America interior.

## The call

```
python -m lithora.cli fit-plates --frame IGS14 --region na
```

## Step by step

1. `python/src/lithora/cli.py::cmd_fit_plates` calls `_load_field("IGS14")`,
   which reads `data/raw/gnss/midas.IGS14.txt`. If the cache is missing it
   exits with a clear message pointing to `acquire-gnss` rather than failing
   deep in the parser.
2. `parse_midas` (`data/ngl.py`) parses the 27-column MIDAS format, converting
   velocities from m/yr to mm/yr and normalising longitudes to (-180, 180]. The
   reference frame is attached to the returned `GnssVelocityField`.
3. `.eligible(5.0)` keeps only stations with at least five years of data,
   freezing the eligibility rule explicitly.
4. `_region_mask` selects the North America interior box, and `arrays()`
   produces lat, lon, velocity, and diagonal covariance arrays.
5. `fit_euler_pole` (`euler_fit.py`) builds the 2n x 3 design matrix for
   `v = -[r]_x omega` projected onto east/north, weights by inverse velocity
   covariance (via `_safe_inverse_2x2`, which degrades gracefully on a singular
   covariance), and solves the weighted normal equations. It reports the pole,
   rate, condition number, and rescaled covariance.
6. `predict_velocities` reconstructs the fitted velocities, and the residual
   norms are summarised. The CLI prints pole, condition number, and median
   residual as JSON.

## Observed result

1,374 stations, pole near 6.7 S / 88.3 W at 0.187 deg/Myr, condition number
about 100, median residual 0.44 mm/yr against a 15.4 mm/yr field. The small
residual is the signature of a rigid interior. See research note 03.
