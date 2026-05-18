"""Geospatial utility functions."""
import numpy as np


def haversine_m(lat1, lon1, lat2, lon2):
    """
    Vectorised Haversine distance in metres between two WGS84 coordinates.
    Accepts numpy arrays or scalars.
    """
    R = 6_371_000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
