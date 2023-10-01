# Atlas time and scale semantics

The atlas is where the honesty constraints become visible to a viewer, so its
time and scale handling are deliberate design, not decoration.

## Two clocks, never merged

There are two independent clocks. The modern clock is present-day geodesy: GNSS
velocities, the rigid fit, the residual field, and its uncertainty. The
geological clock is reconstruction: a rotation model reconstructing geometry at
an age in millions of years before present, bounded by that model's valid
interval. Switching clocks changes which layers are shown, and the two are
linked only by geological interpretation, never by pretending a few years of GPS
measures deep-time plate position. The dual-clock diagram
(`docs/diagrams/dual_clock.svg`) states this link explicitly as interpretation,
not measurement.

## Exaggeration with a legend

Plate velocities are millimetres per year, far too small to see at globe scale,
so velocity arrows are exaggerated. The danger is that an exaggerated arrow
reads as a literal annual displacement. The atlas pairs the exaggeration control
with a prominent legend stating how long a reference 20 mm/yr vector is drawn in
kilometres at the current setting, so the exaggeration is always disclosed. The
arrow geometry itself is placed with the same east/north to ECEF transform the
analysis uses, so the picture is geometrically faithful even while exaggerated.

## Provenance on every layer

Each layer shows its reference frame, its source, and its citation. The observed
and residual layers are labelled distinctly so a viewer never mistakes a
frame-dependent observed field for the deformation signal. The station inspector
shows the raw observed velocity, its uncertainty, the rigid and local model
predictions, the residual, and the station's holdout fold, so a viewer can trace
exactly what each number is.

## Bounded, cancellable loading

Region loading uses a generation counter: each new selection increments it, and
a fetch that returns after a newer selection was made is discarded. This is the
small but real form of the cancellation requirement, ensuring a slow load for an
old region never overwrites the newer one the viewer actually asked for.
