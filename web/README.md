# Lithora atlas (web globe)

An interactive CesiumJS globe for Lithora's present-day deformation fields. It
loads the real station velocities exported by `lithora.export_web` and renders
them as tangent-plane velocity arrows, with model-layer switching, exaggeration
plus a scale legend, station uncertainty, spatial holdout coloring, a station
inspector, and a provenance panel that always states the reference frame and
source.

## Run

```
npm install
npm run dev
```

Then open the printed local URL. The sample data under `public/data` is
committed so the globe runs from a fresh checkout. Regenerate or add regions:

```
# from the repo root, with the python venv and a GNSS cache present
python -m lithora.export_web --frame IGS14 --region cal --out web/public/data/cal.json
```

## What the controls mean

- Vector layer: observed velocity, the rigid Euler-pole prediction, the
  residual (observed minus rigid, where deformation lives), or the local
  model.
- Exaggeration: arrows are scaled up to be visible. The legend states how long
  a 20 mm/yr vector is drawn so the exaggeration is never mistaken for literal
  per-year motion.
- Holdout folds: colors the stations by their spatially buffered test fold,
  making the evaluation split visible on the globe.

## Honesty

The reference frame is shown for every layer. Residual and rigid layers are
labeled distinctly so a viewer never confuses a frame-dependent observed field
with the deformation signal.
