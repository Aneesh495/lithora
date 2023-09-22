# Mathematical derivations

This note derives the kinematics Lithora implements, fixing every convention so
the code and the math agree. It is the reference the Rust core comments point
back to.

## Conventions

- Angles in radians internally; degrees only at boundaries.
- Geological age `t` in millions of years before present (Ma), increasing into
  the past; present is `t = 0`.
- Positions are unit vectors on the sphere. A geographic point `(phi, lambda)`
  (latitude, longitude) maps to

      r = (cos phi cos lambda, cos phi sin lambda, sin phi).

  This latitude is geocentric spherical, not the geodetic latitude of the
  WGS84 ellipsoid; the two differ by up to about 0.19 degrees near 45 N and the
  conversion `tan(phi_gc) = (1 - e^2) tan(phi_gd)` is applied where the
  ellipsoid matters.
- Rotations are active and right-handed about the Euler axis.

## Finite rotations as unit quaternions

A rotation by angle `theta` about a unit axis `u` is the unit quaternion

    q = (cos(theta/2), sin(theta/2) u).

Applying it to a vector `v` uses the sandwich product `v' = q v q*`, which
expands to the matrix-free form the code uses:

    v' = v + 2 w (u_vec x v) + 2 u_vec x (u_vec x v),

where `w = cos(theta/2)` and `u_vec = sin(theta/2) u`. This form is exact at
`theta = 0` (it returns `v`) and well conditioned for the very small stage
angles typical of short intervals, which the naive rotation matrix built from
`cos`/`sin` is not.

Composition is where plate circuits live. If rotation `A` is applied first and
then `B`, the combined rotation is `q_B q_A` (note the order). Because
quaternion multiplication is not commutative, `q_B q_A != q_A q_B` in general,
and this non-commutativity is physical: rotating about two different axes in a
different order lands a plate in a different place. The code method `then`
takes the temporal order ("A then B") and performs `q_B q_A` internally, so the
call site reads in the order events happen.

`q` and `-q` represent the same rotation (the half-angle makes the map two to
one). The code canonicalises to `w >= 0` for stable comparison but treats them
as equal everywhere.

## Interpolating finite rotations

A rotation model gives total reconstruction poles at sampled ages:
`q(t_k)` carries a plate from present to its position at `t_k`. To reconstruct
at an age `t` with `t_a <= t <= t_b`, interpolate the rotation, not the point.
Spherical linear interpolation (slerp) gives

    slerp(q_a, q_b, s) = (sin((1-s) Omega) q_a + sin(s Omega) q_b) / sin(Omega),
    s = (t - t_a) / (t_b - t_a),   cos(Omega) = q_a . q_b.

The reason the point must not be interpolated directly: a linear blend of two
reconstructed Cartesian points cuts a chord through the sphere, so the
intermediate point has radius less than one and the implied motion path dips
below the surface. Slerp keeps the interpolant on the rotation group, and the
reconstructed point stays on the sphere. A unit test enforces exactly this by
comparing the slerp midpoint of a 90-degree rotation (a 45-degree rotation) to
the chord midpoint (norm about 0.707).

When `q_a . q_b < 0` we negate `q_b` first so slerp takes the short way around,
and when the two are nearly identical we fall back to normalised linear
interpolation to avoid dividing by a vanishing `sin(Omega)`.

## Plate circuits

Plates form a time-dependent forest: each moving plate `M` has a parent (fixed)
plate `F`, up to an anchor `A`. The total reconstruction rotation of `M`
relative to `A` at age `t` is the temporal composition up the chain

    q(M -> A, t) = q(M -> F, t) then q(F -> ... , t) then q(... -> A, t).

Three facts the implementation respects:

1. A changed anchor must rotate the whole reconstruction consistently. From the
   chain rule, `q(M -> A') = q(M -> A) then q(A -> A')`, so re-anchoring
   multiplies every plate's rotation by the same `q(A -> A')`. The test
   `reanchoring_is_consistent` checks `q(2->0) = q(2->1) then q(1->0)`.
2. A missing interval on any link makes the whole query unanswerable; the code
   returns `AgeOutOfRange` or `NoBracket` rather than skipping the link.
3. A cycle in the declared parent relationships is a data error; the traversal
   detects revisited plates and returns `CircuitCycle`.

## Stage rotations and angular velocity

The stage rotation from an older age `t_o` to a younger age `t_y` carries the
plate from its position at `t_o` to its position at `t_y`. Since `q(t)` carries
present to `t`, the point at `t_o` is `q(t_o) r_0` and at `t_y` is
`q(t_y) r_0`, so the stage rotation (old to young) is

    q_stage = q(t_y) q(t_o)^{-1},

which in temporal-composition form is `q(t_o)^{-1} then q(t_y)`. Its angle
divided by the forward-time interval `t_o - t_y` gives the average angular
rate, and its axis gives the average pole over the interval.

## Surface velocity: v = omega x r

For an instantaneous angular velocity (Euler vector) `omega`, the surface
velocity of a point at `r` is the time derivative of a rotating position:

    d/dt (R(t) r) = omega x (R(t) r)  =>  v = omega x r.

The velocity is tangent to the sphere (`v . r = 0`) and vanishes at the
rotation poles (`r = +/- u`). As the stage interval shrinks, the stage angular
velocity approaches the instantaneous `omega`; the test
`finite_difference_approaches_analytic_cross_product` confirms the two agree to
1e-7 for a 1e-4 Ma stage.

### Units

`omega` is stored in radians per million years. The surface speed in mm/yr at
unit radius is `|omega x r| R (1e-3)`, since `|v|` in rad/Myr times Earth radius
`R` in metres gives m/Myr, and `1 m/Myr = 1e-3 mm/yr` (one metre is 1e3 mm and
one million years is 1e6 years). A plate rotating 1 deg/Myr has an equatorial
speed near 111 mm/yr, which the unit test checks to within 2 mm/yr.

## The rigid inverse problem and covariance propagation

Given station velocities `v_i = omega x r_i`, estimating `omega` is linear:
writing the cross product as `omega x r = -[r]_x omega` with `[r]_x` the skew
matrix, and projecting onto the local east/north basis `(e_i, n_i)` gives two
rows per station,

    [ v_{e,i} ]   [ -e_i^T [r_i]_x ]
    [ v_{n,i} ] = [ -n_i^T [r_i]_x ] omega  (scaled to mm/yr).

Stacking all stations yields `A omega = d`. With per-station velocity
covariance `C_i`, the weighted normal equations are

    (sum_i A_i^T C_i^{-1} A_i) omega = sum_i A_i^T C_i^{-1} d_i,

and the estimate covariance is the inverse of the normal matrix, rescaled by
the reduced chi-square so it reflects observed scatter when the weights are
only relative. The condition number of the normal matrix is reported: a
clustered or colinear network leaves the rotation axis poorly constrained, and
a large condition number is the honest signal of that, not a confident wrong
pole.

## Parallel transport and the learned residual

A velocity is a tangent vector, so comparing velocities at two points requires
transporting one into the other's tangent plane along the connecting great
circle. On the sphere this is a rotation by the arc angle about the axis
`r_from x r_to`, applied by the Rodrigues formula. Transport preserves length
and the angle to the path. Because the learned model expresses every vector in
a local east/north frame and transports neighbour vectors before mixing them,
a global rotation of the coordinate system rotates the model's outputs
correspondingly and leaves its inputs unchanged, which is the rotational
equivariance checked at the feature level and required by gate G09.
