# Spherical polygons

Plate polygons are closed rings of latitude/longitude vertices. Deciding whether
a point lies inside one is harder on a sphere than on a plane, and the naive
approaches fail in ways that matter.

## Point in polygon on a sphere

Lithora sums the signed angle each edge subtends at the test point, using the
dihedral form `atan2((a x b) . p, a.b - (a.p)(b.p))`. Summed over a closed ring
this is the signed solid angle the ring encloses as seen from the point: about
`2*pi` for a point inside and `0` for a point outside. This form stays well
conditioned even when a vertex is near the antipode of the test point, where a
tangent-plane projection collapses and winds spuriously.

## The orientation subtlety

A ring divides the sphere into two regions, and the dihedral sum is `+2*pi` for
one and `-2*pi` for the other. Which region is the intended interior is set by
the ring's winding, so containment compares the signed sum against the sign of
the ring's signed area. Without this, a small box near the antimeridian would
report its antipodal region as a second interior. A test places a box straddling
the dateline and confirms the dateline point is inside while the antipode is
outside.

## Area, distance, and holes

Area uses the spherical excess via L'Huilier's half-angle form, which is stable
for thin triangles, summed as a fan from the first vertex with a sign from the
triple product. Holes are separate rings subtracted from the outer area and
excluded from containment. Great-circle distance uses the `atan2` form for
stability at small and large separations. Tests cover polar caps, the
antimeridian, holes, and a quarter-arc distance checked against the analytic
value.

## What is certified

Only a documented rigid-polygon subset is treated as certified. Deforming
topologies, which a published model may provide, are not rendered as certified
rigid reconstructions; where the topology is unavailable, classification is
reported as unavailable rather than guessed.
