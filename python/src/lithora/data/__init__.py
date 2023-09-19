"""Data acquisition with provenance for Lithora.

Every acquired dataset carries where it came from, when it was fetched, the
exact query, and the caveats that matter for interpretation (reference frame
for GNSS, catalog completeness for earthquakes). Raw downloads are cached
under ``data/raw`` and are never committed; only the provenance manifests and
the code that reproduces the download live in the repository.
"""

from __future__ import annotations
