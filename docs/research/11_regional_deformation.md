# Regional deformation: interior versus margin

The central question of Lithora is where rigid models explain motion and where
they do not. The cleanest way to answer it is to run the same pipeline over
regions chosen for their data coverage and tectonic setting, and to report what
the data support.

## North America interior (rigid)

Box: latitude 32 to 49, longitude -104 to -85, 1,374 eligible IGS14 stations.

A single Euler pole explains the field to a 0.44 mm/yr median residual against a
15.4 mm/yr observed field. Running spatially buffered cross-validation, no
residual model improves held-out prediction over rigid-only here. This is the
expected and correct outcome: a quiet plate interior has little deformation to
learn, so the rigid null hypothesis is not just adequate but best. A residual
model that claimed large structure here would be fitting noise.

## California transform margin (deforming)

Box: latitude 32 to 42, longitude -124 to -114, 1,552 eligible IGS14 stations.

Here the San Andreas system produces real, spatially structured deformation.
Buffered five-fold cross-validation (0.3 degree buffer, 1 degree local
bandwidth) gives held-out vector RMSE:

| Model | RMSE (mm/yr) |
|---|---|
| Rigid only | 14.8 |
| Nearest neighbor | 8.8 |
| Local regression | 6.4 |
| Gaussian process | 6.7 |

The residual models more than halve the error, which is the signature of a
region where deformation is the story. The simple distance-weighted local
regression is the best of the four at this scale, a reminder that complexity is
not automatically rewarded.

## The learned model, honestly

Three independent seeds of the spherical graph residual model on the California
margin, with 80 percent of stations in training and the rest held out:

| Seed | Graph held-out RMSE | Rigid held-out RMSE |
|---|---|---|
| 0 | 12.70 | 12.95 |
| 1 | 11.58 | 12.92 |
| 2 | 12.81 | 12.74 |

The graph model beats rigid in two of three seeds (mean about 12.4 versus
12.9 mm/yr), with real seed-to-seed variance, and one seed is slightly worse.
It also does not beat the local regression at this network size. The honest
reading: the learned model learns something, its parameters and loss move as
training evidence requires, and on average it helps a little, but at this scale
a simple local model is the stronger and cheaper choice. This is reported as it
is, not inflated.

## Why the absolute RMSE is large

These RMSE values are in the IGS14 global frame, where the whole plate moves at
roughly 15 to 40 mm/yr. The buffered folds remove nearby training stations, so
a held-out test station in a strongly sheared zone can be several mm/yr from any
prediction. The comparison across models on the same folds is what carries the
signal; the absolute level reflects the frame and the deliberate buffer.

## Reproduce

```
python -m lithora.cli spatial-evaluate --frame IGS14 --region na
python -m lithora.cli spatial-evaluate --frame IGS14 --region cal
python -m lithora.cli train --frame IGS14 --region cal --seed 0
```
