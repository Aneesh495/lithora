# Reference frames

A GNSS velocity is only meaningful relative to a reference frame. The same
station has one velocity in the global IGS14 frame and a different velocity in a
North-America-fixed frame, because the second subtracts the bulk plate motion.
Neither is wrong, but they are not comparable, and subtracting one from the
other is meaningless.

## Why mixing frames is a silent error

Mixing an IGS14 file with a plate-fixed file, or IGS14 with IGS20, produces
numbers that look like velocities and are nonsense. Nothing in the arithmetic
complains. Lithora makes this a hard error: a velocity field carries its frame
as a typed attribute, and the merge function refuses to combine fields with
different frames (`data/ngl.py::merge_same_frame`). The NGL file naming encodes
the frame, and the acquisition layer records it in the provenance manifest, so
the frame travels with the bytes.

## Geodetic versus geocentric latitude

A second frame-like subtlety is latitude. Station coordinates are geodetic
(the angle of the ellipsoidal normal), while the reconstruction math works in
geocentric spherical latitude (the angle of the radius vector). They differ by
up to about 0.19 degrees near 45 degrees, which is not negligible at
plate-motion scales. The conversion `tan(phi_gc) = (1 - e^2) tan(phi_gd)` is
implemented in `geo/ellipsoid.rs` and tested at the poles, equator, and
mid-latitudes.

## What this enables and forbids

Transformations between frames are allowed only with verified published
parameters and epochs; absent those, Lithora preserves the separate frames and
rejects the join. This is capability L12, and it is enforced in code, not just
documented.
