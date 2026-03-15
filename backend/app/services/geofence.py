"""
Geofence service.

Pure Haversine distance utility for building-level geofence validation.
No I/O, no database — keeps this testable in isolation.
"""

import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance in meters between two WGS-84 coordinates.

    Uses the Haversine formula, which is accurate to within ~0.5% for
    short distances (< 1 km) — more than sufficient for building-level
    geofencing.

    Args:
        lat1, lon1: First point in decimal degrees.
        lat2, lon2: Second point in decimal degrees.

    Returns:
        Distance in meters.
    """
    R = 6_371_000  # Earth mean radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def check_geofence(
    submitted_lat: float,
    submitted_lon: float,
    building_lat: float,
    building_lon: float,
    radius_meters: float,
) -> tuple[float, bool]:
    """
    Determine whether a submitted coordinate is within a building's geofence.

    Args:
        submitted_lat, submitted_lon: Student's reported location.
        building_lat, building_lon: Building centroid coordinates.
        radius_meters: Allowed radius (from Building.geofence_radius_meters).

    Returns:
        (distance_meters, within_geofence) tuple.
    """
    distance = haversine_distance(
        submitted_lat, submitted_lon, building_lat, building_lon
    )
    return round(distance, 2), distance <= radius_meters
