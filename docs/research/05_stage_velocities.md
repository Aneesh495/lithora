# Stage velocities

Two velocity notions appear in plate kinematics and must not be confused.

## Instantaneous versus stage

An instantaneous angular velocity `omega` gives the present-day surface
velocity by `v = omega x r`. This is what GNSS observes. A stage rotation is the
finite rotation carrying a plate from one age to another; dividing its angle by
the time span gives an average angular rate over the interval, which approaches
the instantaneous `omega` only as the interval shrinks.

## The derivation and its check

Since the total pole `q(t)` carries present to age `t`, the stage from an older
age to a younger one maps `q(t_o) r_0` to `q(t_y) r_0`, giving the stage
rotation `q(t_y) q(t_o)^{-1}`. The average angular velocity is its axis times
its angle over the forward-time interval. A property test builds a plate
rotating at a known constant rate, takes a 1e-4 Ma stage near present, and
confirms the recovered Euler vector reproduces the analytic `v = omega x r` to
within 1e-7 over 10,000 random axes and positions. This is gate G03.

## Units, stated once and enforced

Angular velocity is stored in radians per million years. Surface speed in mm/yr
at unit radius is `|omega x r| R (1e-3)`, since rad/Myr times Earth radius gives
m/Myr and one m/Myr equals 1e-3 mm/yr. A plate rotating 1 degree per million
years has an equatorial speed near 111 mm/yr, which a test checks to within
2 mm/yr. Getting this factor wrong by a thousand is the mm-versus-metre error
that the semantic verifier specifically probes.

## Why it matters for honesty

A short GNSS time series measures the instantaneous velocity now. It says
nothing directly about where a plate sat hundreds of millions of years ago; that
comes from the reconstruction model and geological interpretation. Keeping the
instantaneous and stage notions separate is part of keeping the modern and
geological clocks separate.
