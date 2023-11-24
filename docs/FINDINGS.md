# Findings and limitations

A consolidated, honest summary of what Lithora has established and what it has
not. Each finding links to the note and command behind it.

## Findings

1. A single rigid Euler pole explains the North America interior to a
   0.44 mm/yr median residual against a 15.4 mm/yr field (note 03). The
   interior behaves as rigid to sub-millimetre precision.

2. On the California transform margin, residual models cut held-out vector
   RMSE from 14.8 (rigid) to 6.4 mm/yr (local regression), with the GP and NN
   in between (note 11). Deformation is real and learnable where it exists.

3. No residual model improves on rigid-only in the North America interior
   (note 11). The null hypothesis wins where there is nothing to learn; added
   complexity is not automatically justified.

4. The Gaussian process is overconfident on the California margin (1-sigma
   coverage about 0.09), a measured calibration failure under strong spatial
   structure (note 10). Exchangeability-based coverage does not transfer to a
   deforming margin.

5. The learned spherical graph model beats rigid on held-out stations in two
   of three seeds (mean 12.4 vs 12.9 mm/yr) but does not beat the simpler local
   model at this network scale (note 11). Its learning is real (gradients and
   parameters move) but its benefit is modest and seed-dependent.

6. Cross-region transfer is poor: a model fit on the interior tested on the
   margin gives 22.8 mm/yr RMSE, with test stations a median 12 degrees from
   any training station (leave-region-out). Local structure does not
   interpolate across a continent.

7. Inferred strain rate depends strongly on smoothing scale: central San
   Andreas max shear runs from about 196 ns/yr at 0.3 degrees to 43 ns/yr at
   2.0 degrees (note 11, strain command). The scale must always be reported.

8. The geometry engine agrees with an independent Rodrigues reference below
   1e-7 radians over 20,000 random rigid reconstructions (G02), and the full
   property campaign passes over 100,000 cases (G01).

## Limitations

- Deep-time reconstruction disagreement between two published models has not
  been measured at scale, because pinning two licensed EarthByte models is
  pending (note 07). The engine and comparison machinery are built and tested
  on synthetic models.
- The pyGPlates differential check for real models (the external half of G02)
  requires that dependency and is not yet run.
- The full acceptance campaign (many folds x three seeds x leave-region-out)
  and the 12-hour stress run are declared but run only at diagnostic scale so
  far.
- The browser FPS benchmark needs a real desktop GPU; the headless environment
  renders the globe but cannot measure representative frame times.
- MIDAS velocity uncertainties understate correlated noise; the correlated-
  noise inflation is an AR(1) approximation, not a full stochastic model.

## What Lithora does not claim

It does not predict earthquake dates or magnitudes, does not bridge modern
geodesy and deep-time reconstruction as if one measured the other, and does not
present exaggerated vectors as literal per-year motion. Negative and null
results above are findings, not failures.
