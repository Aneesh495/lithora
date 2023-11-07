# Model card: spherical graph residual model

## What it predicts

The horizontal deformation residual at a GNSS station: the east/north velocity
left after removing the best-fit rigid Euler-pole motion. It does not predict
absolute velocity, earthquake timing, or temporal evolution of a station.

## Architecture

A message-passing graph network on the k-nearest-neighbour graph of stations by
great-circle distance. Every vector lives in a local east/north tangent frame;
neighbour residuals are parallel-transported into the centre frame before
mixing; edge features are rotation-invariant tangent offsets and distance. Only
the message and update MLP weights are learned (about 1,774 parameters at the
default width); the geometry is fixed. See `graph_model.py` and research note
09.

## Training

From random initialisation with Adam. At least three independent seeds for any
decisive comparison. Preprocessing (the rigid fit and graph construction) is
done per training set; test stations are held out of the loss. Checkpoints save
the model state, the rigid pole, and the station identities atomically.

## Equivariance

Rotating the station network in longitude leaves the model's tangent-frame
inputs unchanged and rotates its outputs correspondingly (feature-level test in
`test_graph_model.py`). This is the intended rotational equivariance; it is
distinct from station-order invariance, which the degree-normalised aggregation
provides.

## Measured performance and limits

On the California margin across three seeds the trained model beats the rigid
baseline on held-out stations in two of three seeds (mean held-out RMSE about
12.4 versus 12.9 mm/yr) but does not beat the simpler distance-weighted local
regression at this network scale. Its parameters and loss move during training,
which is the evidence that learning occurred; a downloaded checkpoint or a
large parameter count would not be. See research note 11 for the per-seed
table.

## Intended use and misuse

Intended: interpolating present-day deformation residuals within a well-sampled
region, with uncertainty treated honestly. Not intended: extrapolating into
unsampled regions (error grows with distance to the training network),
predicting future temporal evolution, or any earthquake forecast.
