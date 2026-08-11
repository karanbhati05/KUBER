import math
import numpy as np
from typing import List, Dict, Tuple
from scipy.optimize import linear_sum_assignment

# Base32 characters used in Geohash encoding
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode_geohash(latitude: float, longitude: float, precision: int = 6) -> str:
    """
    Encodes latitude and longitude into a string-based Geohash grid token.
    Precision 6 corresponds to approximately 1.2km x 0.6km grid cell.
    """
    lat_interval = (-90.0, 90.0)
    lon_interval = (-180.0, 180.0)

    geohash = []
    bits = [16, 8, 4, 2, 1]
    bit = 0
    ch = 0
    is_even = True

    while len(geohash) < precision:
        if is_even:
            mid = (lon_interval[0] + lon_interval[1]) / 2.0
            if longitude > mid:
                ch |= bits[bit]
                lon_interval = (mid, lon_interval[1])
            else:
                lon_interval = (lon_interval[0], mid)
        else:
            mid = (lat_interval[0] + lat_interval[1]) / 2.0
            if latitude > mid:
                ch |= bits[bit]
                lat_interval = (mid, lat_interval[1])
            else:
                lat_interval = (lat_interval[0], mid)

        is_even = not is_even

        if bit < 4:
            bit += 1
        else:
            geohash.append(BASE32[ch])
            bit = 0
            ch = 0

    return "".join(geohash)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def solve_bipartite_matching(riders: List[Dict], drivers: List[Dict]) -> List[Dict]:
    """
    Solves Minimum Weight Bipartite Matching using Hungarian Algorithm (linear_sum_assignment).
    Optimally pairs M riders and N drivers to minimize total combined pickup distance.
    """
    if not riders or not drivers:
        return []

    num_riders = len(riders)
    num_drivers = len(drivers)

    # Construct distance cost matrix (shape: M x N)
    cost_matrix = np.zeros((num_riders, num_drivers))

    for i, rider in enumerate(riders):
        r_lat, r_lon = rider['pickup_lat'], rider['pickup_lon']
        for j, driver in enumerate(drivers):
            d_lat, d_lon = driver['latitude'], driver['longitude']
            cost_matrix[i, j] = haversine_distance(r_lat, r_lon, d_lat, d_lon)

    # Solve optimal bipartite matching (Hungarian Algorithm)
    rider_indices, driver_indices = linear_sum_assignment(cost_matrix)

    matches = []
    for r_idx, d_idx in zip(rider_indices, driver_indices):
        dist = cost_matrix[r_idx, d_idx]
        matches.append({
            "rider_id": riders[r_idx]['rider_id'],
            "driver_id": drivers[d_idx]['driver_id'],
            "distance_km": round(float(dist), 3),
            "geohash": encode_geohash(riders[r_idx]['pickup_lat'], riders[r_idx]['pickup_lon'])
        })

    return matches
