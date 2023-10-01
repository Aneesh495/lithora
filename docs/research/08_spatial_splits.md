# Spatial splits

Evaluating a spatial predictor with ordinary random cross-validation overstates
its accuracy, because a held-out station usually has a training station a few
kilometres away carrying almost the same velocity. The model then looks good by
copying a neighbour rather than by generalising.

## Buffered block folds

Lithora partitions stations into spatial blocks and, for each fold, holds out
one block and drops any training station within a buffer distance of a test
station. The buffer is the difference between honest spatial validation and
leaked validation. A test confirms that after the split no training station lies
within the buffer of any test station, so the guarantee is enforced, not
assumed.

## What the metrics expose

On each fold we report vector RMSE, a robust median error, directional error
conditioned on speed (direction is ill defined for near-zero velocities, so
those are excluded), interval coverage and sharpness where a model gives a
standard deviation, and error as a function of distance to the nearest training
station. That last metric is the one that catches overconfident extrapolation:
error grows with distance into empty regions, and a model whose intervals do not
grow with it is overconfident there.

## Why absolute error looks large

Because the buffer removes nearby training stations and the IGS14 frame carries
large bulk motion, absolute RMSE in a sheared margin can be over 10 mm/yr even
for the better models. The informative quantity is the paired comparison across
models on the same folds, which is why note 11 reports models side by side on
identical splits rather than in isolation.

## Plate and temporal holdouts

Beyond spatial blocks, the design supports leave-region-out (plate-level)
holdouts and, for time series, non-overlapping time windows so adjacent windows
do not leak. Forecasting a vector at a new location is a different task from
predicting a station's future temporal evolution, and the splits are chosen to
match whichever claim is being made.
