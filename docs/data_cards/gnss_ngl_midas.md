# Data card: NGL MIDAS GNSS velocities

## Source

Nevada Geodetic Laboratory (NGL), University of Nevada, Reno. MIDAS robust
trend velocity product, downloaded from `https://geodesy.unr.edu/velocities/`.

## Citation

Blewitt, G., C. Kreemer, W. C. Hammond, and J. Gazeaux (2016), MIDAS robust
trend estimator for accurate GPS station velocities without step detection,
J. Geophys. Res. Solid Earth, 121, doi:10.1002/2015JB012552. Cite this in any
publication that uses these velocities.

## What it is

One robust velocity per continuous-GNSS station: east, north, and up mode
velocities in m/yr with uncertainties, the first and last epoch, the series
duration, the number of steps assumed from the NGL steps database, and the
station latitude, longitude, and height. The MIDAS estimator is designed to be
insensitive to undetected offsets and seasonal signals.

## Reference frame

The frame is encoded in the filename (for example `midas.IGS14.txt` is the
IGS14 frame) and is carried as a typed attribute on the parsed field. Lithora
refuses to merge velocities from different frames. Do not mix IGS14 with IGS20
or with a plate-fixed frame.

## Acquired snapshot

The development snapshot of `midas.IGS14.txt` contained 20,168 stations, of
which 16,002 have at least five years of data. The exact bytes are recorded by
SHA256 in `data/raw/gnss/midas.IGS14.provenance.json` when acquired. The file
is weekly-updated upstream, so a later download will differ; pin the snapshot
by its hash for reproducible evidence.

## Caveats

- The reported per-station velocity uncertainties are small and do not fully
  capture correlated (flicker/random-walk) noise in the daily series. See
  research note 02 on the correlated-noise inflation Lithora applies when
  fitting raw series.
- This is a velocity product, not a daily position series. Lithora keeps the
  two distinct and never presents one as the other.
- Station coordinates are geodetic (WGS84); the reconstruction math converts to
  geocentric spherical latitude where needed.

## Redistribution

The raw file is not committed to the repository (it is gitignored). It is
reproduced on demand by `make acquire-gnss`, which records provenance. A small
derived sample for the atlas is committed under `web/public/data`.
