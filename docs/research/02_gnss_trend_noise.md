# GNSS trend and noise

A station's velocity is the slope of its daily position series, but that series
is not a clean line. It carries annual and semi-annual seasonal cycles, offsets
from equipment changes and earthquakes, and noise that is strongly correlated
day to day.

## Modelling the signal

The parametric fit in `timeseries.py` includes an intercept, a linear trend,
sine and cosine terms at the annual and semi-annual periods, and a step at each
supplied offset epoch. A test injects a 15 mm step mid-series and confirms the
recovered trend stays within 0.5 mm/yr of the truth, so the offset term does
its job rather than corrupting the slope.

## The correlated-noise trap

The headline danger in GNSS velocity uncertainty is treating thousands of daily
samples as independent. White-noise least squares then reports a tiny standard
error that is not believable: geodetic series are closer to flicker or
random-walk noise, and the effective number of independent samples is far
smaller than the count of days. Lithora inflates the white-noise standard error
by `sqrt((1+r)/(1-r))` using the lag-1 autocorrelation `r` of the residuals.
This is a transparent AR(1) effective-sample-size correction, not a hidden
constant, and it is labelled an approximation rather than a full stochastic
model. The inflated sigma is always at least the white-noise sigma, which a
test checks.

## A model-free cross-check

Alongside the parametric fit we compute a MIDAS-style robust velocity: the
median of slopes between samples separated by about one year. Pairing samples a
year apart cancels the annual cycle, and the median resists outliers and
undetected steps. Because it assumes no noise model at all, agreement between it
and the parametric trend is evidence the trend is real. Tests confirm both
recover a known 12 mm/yr synthetic velocity within about 1 mm/yr.

## Distinguishing the products

A daily position series, an estimated station velocity, and an instantaneous
derivative are three different things. Lithora keeps the published MIDAS
velocity product (what the NGL files contain) distinct from a velocity it would
estimate from raw daily series, and never presents one as the other.
