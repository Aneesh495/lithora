"""Tangent-frame construction and parallel transport on the sphere.

The learned residual model (capability L16) must respect the geometry: a
velocity is a tangent vector, and comparing velocities at two different points
means transporting one into the other's tangent plane along the connecting
great circle. Doing this explicitly is what makes the model rotationally
equivariant rather than fitting latitude/longitude artifacts.

This module provides, in NumPy so it can be used for both feature preparation
and tests:

* :func:`tangent_frame` -- an east/north orthonormal basis at a point;
* :func:`parallel_transport` -- move a tangent vector from one point to
  another along the great circle, preserving its length and its angle to the
  path (the Levi-Civita connection on the sphere);
* :func:`log_map` / :func:`exp_map` -- the Riemannian logarithm and
  exponential, used to encode a neighbor's relative position as a tangent
  vector at the centre point.

The learned model consumes these as fixed geometric operators; only the
message weights are trained.
"""

from __future__ import annotations

import numpy as np

from .sphere import latlon_to_unit


def tangent_frame(unit_pos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return orthonormal east and north tangent vectors at a unit position.

    Degenerates at the exact poles where east/north are undefined; there we
    fall back to a fixed basis so downstream math stays finite. Callers near
    the poles should expect reduced meaning in the azimuthal direction.
    """
    unit_pos = np.asarray(unit_pos, float)
    z = np.array([0.0, 0.0, 1.0])
    east = np.cross(z, unit_pos)
    norm = np.linalg.norm(east)
    if norm < 1e-9:
        # At a pole: pick an arbitrary but fixed basis.
        east = np.array([1.0, 0.0, 0.0])
        north = np.cross(unit_pos, east)
    else:
        east = east / norm
        north = np.cross(unit_pos, east)
    north = north / np.linalg.norm(north)
    return east, north


def log_map(center_unit: np.ndarray, other_unit: np.ndarray) -> np.ndarray:
    """Riemannian log: tangent vector at ``center`` pointing to ``other``.

    Its length equals the great-circle angle between the two points, and its
    direction is the initial heading of the geodesic from center to other.
    """
    center_unit = np.asarray(center_unit, float)
    other_unit = np.asarray(other_unit, float)
    dot = np.clip(np.dot(center_unit, other_unit), -1.0, 1.0)
    angle = np.arccos(dot)
    if angle < 1e-12:
        return np.zeros(3)
    direction = other_unit - dot * center_unit
    n = np.linalg.norm(direction)
    if n < 1e-12:
        return np.zeros(3)
    return (direction / n) * angle


def exp_map(center_unit: np.ndarray, tangent: np.ndarray) -> np.ndarray:
    """Riemannian exp: move from ``center`` along ``tangent`` on the sphere."""
    center_unit = np.asarray(center_unit, float)
    tangent = np.asarray(tangent, float)
    angle = np.linalg.norm(tangent)
    if angle < 1e-12:
        return center_unit
    unit_t = tangent / angle
    return np.cos(angle) * center_unit + np.sin(angle) * unit_t


def parallel_transport(
    from_unit: np.ndarray, to_unit: np.ndarray, vec: np.ndarray
) -> np.ndarray:
    """Parallel-transport a tangent vector along the great circle.

    Moves ``vec`` (tangent at ``from_unit``) to the tangent plane at
    ``to_unit`` using the sphere's Levi-Civita connection, which rotates the
    vector in the plane spanned by the two positions while keeping its
    component perpendicular to that plane fixed. Length is preserved.
    """
    from_unit = np.asarray(from_unit, float)
    to_unit = np.asarray(to_unit, float)
    vec = np.asarray(vec, float)
    dot = np.clip(np.dot(from_unit, to_unit), -1.0, 1.0)
    angle = np.arccos(dot)
    if angle < 1e-12:
        return vec
    # Axis of the great-circle rotation.
    axis = np.cross(from_unit, to_unit)
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-12:
        return vec
    axis = axis / axis_norm
    # Rodrigues rotation of vec by `angle` about `axis`.
    return (
        vec * np.cos(angle)
        + np.cross(axis, vec) * np.sin(angle)
        + axis * np.dot(axis, vec) * (1.0 - np.cos(angle))
    )


def neighbor_features(
    lat: np.ndarray, lon: np.ndarray, k: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build a k-nearest-neighbor graph and per-edge geometric features.

    Returns ``(edges, edge_feats)`` where ``edges`` is ``(m, 2)`` of
    (center, neighbor) indices and ``edge_feats`` is ``(m, 3)`` with the
    neighbor's relative position encoded in the center's tangent frame:
    (east offset, north offset, great-circle distance), all in radians.
    """
    from .baselines import great_circle_angles

    lat = np.asarray(lat, float).reshape(-1)
    lon = np.asarray(lon, float).reshape(-1)
    n = lat.size
    pos = latlon_to_unit(lat, lon)
    d = great_circle_angles(lat, lon, lat, lon)
    np.fill_diagonal(d, np.inf)
    kk = min(k, n - 1)
    nn = np.argsort(d, axis=1)[:, :kk]

    edges = []
    feats = []
    for i in range(n):
        east, north = tangent_frame(pos[i])
        for j in nn[i]:
            lv = log_map(pos[i], pos[j])
            e = np.dot(lv, east)
            no = np.dot(lv, north)
            dist = np.linalg.norm(lv)
            edges.append((i, j))
            feats.append((e, no, dist))
    return np.array(edges, dtype=np.int64), np.array(feats, dtype=np.float64)
