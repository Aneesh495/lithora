# Vector graph learning

The learned component predicts the deformation residual, the part of a station
velocity left after removing the rigid Euler-pole motion. Its design is where
geometry meets learning, and the design choices are what keep it from learning
coordinate artifacts instead of physics.

## Why a plain network is wrong here

A velocity is a tangent vector on a curved surface. Feeding raw longitude and a
raw east/north pair into a network lets it key on absolute position and on the
fact that east points in different Cartesian directions at different places. The
model would then fit a longitude artifact that does not generalise under a
change of coordinates.

## The equivariant design

Every vector in the model lives in a local east/north tangent frame, and
messages transport a neighbour's residual into the centre's frame by parallel
transport along the connecting great circle before mixing. Edge features are the
neighbour's tangent-frame offset and great-circle distance, which are invariant
to a global rotation of the coordinate system. As a result, rotating the whole
network in longitude leaves the model's inputs unchanged and rotates its outputs
correspondingly. A test shifts every station's longitude by 37 degrees and
confirms the graph connectivity and tangent-frame edge features are identical to
machine precision, which is the feature-level form of gate G09.

## The equivariance versus invariance distinction

Rotational equivariance (outputs rotate with a global rotation) is different
from station-order invariance (the prediction does not depend on the arbitrary
order stations are listed). The message-passing aggregation is a sum normalised
by degree, which is order invariant, while the tangent-frame transport provides
the equivariance. Both properties are intended and separate.

## Measured behaviour and its honest limits

Training from random initialisation on the real California margin, across three
seeds, the model's parameters and loss move substantially and it beats the rigid
baseline on held-out stations in two of three seeds (note 11). It does not beat
the simpler distance-weighted local regression at this network scale. The
takeaway is not that the learned model is useless but that its benefit is real,
modest, and seed-dependent, and that a simpler method can win. A downloaded
checkpoint or a large parameter count would not be evidence of learning; the
moving gradients, changing parameters, and held-out gains are.

## What it does not do

The model forecasts a velocity at a new location. That is a spatial
interpolation of present-day motion, not a prediction of a station's future
temporal evolution, and it is never presented as the latter.
