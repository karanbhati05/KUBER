import numpy as np
from matchmaker import encode_geohash, haversine_distance, solve_bipartite_matching

def run_matchmaking_benchmark():
    print("==========================================================================")
    print("   KUBER MATCHMAKING BENCHMARK: Greedy Radius vs. Bipartite Optimal")
    print("==========================================================================\n")

    # Sample Riders in Mumbai Bandra Region (19.0600, 72.8350)
    riders = [
        {"rider_id": "rider_1", "pickup_lat": 19.0610, "pickup_lon": 72.8360},
        {"rider_id": "rider_2", "pickup_lat": 19.0650, "pickup_lon": 72.8400},
        {"rider_id": "rider_3", "pickup_lat": 19.0580, "pickup_lon": 72.8310},
        {"rider_id": "rider_4", "pickup_lat": 19.0700, "pickup_lon": 72.8450},
        {"rider_id": "rider_5", "pickup_lat": 19.0550, "pickup_lon": 72.8290},
    ]

    # Sample Available Drivers in the same zone
    drivers = [
        {"driver_id": "driver_A", "latitude": 19.0690, "longitude": 72.8440},
        {"driver_id": "driver_B", "latitude": 19.0605, "longitude": 72.8355},
        {"driver_id": "driver_C", "latitude": 19.0545, "longitude": 72.8285},
        {"driver_id": "driver_D", "latitude": 19.0645, "longitude": 72.8395},
        {"driver_id": "driver_E", "latitude": 19.0575, "longitude": 72.8305},
    ]

    # Print Geohash Grid Encoding
    print("--- 1. GEOHASH GRID INDEXING (Precision 6) ---")
    for r in riders:
        gh = encode_geohash(r['pickup_lat'], r['pickup_lon'], precision=6)
        print(f"Rider {r['rider_id']} @ ({r['pickup_lat']}, {r['pickup_lon']}) -> Geohash Grid: '{gh}'")
    print("\n--------------------------------------------------------------------------\n")

    # 2. Greedy Matching
    print("--- 2. GREEDY RADIUS MATCHING (First-Come, First-Served) ---")
    greedy_distance = 0.0
    used_drivers = set()

    for r in riders:
        r_lat, r_lon = r['pickup_lat'], r['pickup_lon']
        best_driver = None
        min_dist = float('inf')

        for d in drivers:
            if d['driver_id'] in used_drivers:
                continue
            dist = haversine_distance(r_lat, r_lon, d['latitude'], d['longitude'])
            if dist < min_dist:
                min_dist = dist
                best_driver = d['driver_id']

        if best_driver:
            used_drivers.add(best_driver)
            greedy_distance += min_dist
            print(f"Greedy Match: {r['rider_id']} -> {best_driver} ({round(min_dist, 3)} km)")

    print(f"--> Total Greedy Fleet Wait Distance: {round(greedy_distance, 3)} km\n")
    print("--------------------------------------------------------------------------\n")

    # 3. Bipartite Optimal Matching (Hungarian Algorithm)
    print("--- 3. OPTIMAL BIPARTITE MATCHING (SciPy Hungarian Algorithm) ---")
    optimal_matches = solve_bipartite_matching(riders, drivers)
    optimal_distance = sum(m['distance_km'] for m in optimal_matches)

    for m in optimal_matches:
        print(f"Optimal Match: {m['rider_id']} -> {m['driver_id']} ({m['distance_km']} km) [Geohash: {m['geohash']}]")

    print(f"--> Total Optimal Fleet Wait Distance: {round(optimal_distance, 3)} km\n")
    print("==========================================================================")
    saved = greedy_distance - optimal_distance
    percent_saved = (saved / greedy_distance) * 100 if greedy_distance > 0 else 0
    print(f"   SUMMARY: Bipartite Matching saved {round(saved, 3)} km ({round(percent_saved, 1)}% reduction in wait distance!)")
    print("==========================================================================\n")

if __name__ == "__main__":
    run_matchmaking_benchmark()
