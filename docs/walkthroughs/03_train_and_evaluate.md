# Walkthrough: training the graph model and evaluating it

This traces the learned residual model from raw velocities to a held-out score.

## The call

```
python -m lithora.cli train --frame IGS14 --region cal --seed 0
```

## Step by step

1. `cli.py::cmd_train` first checks `torch_available()`; without PyTorch it
   exits with a clear message rather than a stack trace, which is the
   torch-optional design (ADR 5).
2. It loads and filters the California stations, then builds an 80/20 train
   mask with a seeded RNG.
3. `train.train_graph_model` (`train.py`) calls `_prepare`, which fits the
   rigid Euler pole, subtracts it to get the residual field, builds the
   k-nearest-neighbour graph with `neighbor_features` (`transport.py`), and
   builds the per-edge transport matrices with `build_transport_matrices`
   (`graph_model.py`).
4. The model `SphericalGraphResidual` runs message passing: neighbour residuals
   are transported into the centre frame, concatenated with rotation-invariant
   edge features, passed through the message MLP, aggregated with degree
   normalisation, and read out as a 2-vector residual.
5. Training runs Adam for the requested epochs. The harness records the initial
   and final loss, the L2 change in parameters, and the first-step gradient
   norm, which are the gate-G06 evidence that learning actually happened.
6. `predict_training_nodes` evaluates the model, and the CLI compares the
   held-out graph RMSE against the held-out rigid RMSE.

## Observed result

On the California margin, parameters move (L2 delta about 25 to 35), loss drops,
and the trained model beats rigid on held-out stations in two of three seeds.
See research note 11 for the per-seed table and the honest caveat that the
simpler local model wins at this scale.

## Evaluation path

```
python -m lithora.cli spatial-evaluate --frame IGS14 --region cal
```

`evaluate.spatial_block_folds` builds spatially buffered folds (dropping
training stations within the buffer of any test station), and
`velocity_metrics` reports vector RMSE, coverage, and error versus distance to
the training network per fold.
