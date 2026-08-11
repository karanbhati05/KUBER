import os
import asyncio
import json
import logging
import time
import httpx
import redis.asyncio as redis
from matchmaker import encode_geohash, solve_bipartite_matching

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LOCATION_ENGINE_URL = os.getenv("LOCATION_ENGINE_URL", "http://localhost:8000")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

BATCH_INTERVAL_SECONDS = 3.0  # 3-Second Batch Window

async def fetch_nearby_drivers(lat: float, lon: float, radius_km: float = 5.0) -> list:
    """Fetch nearby active drivers from Location Engine."""
    async with httpx.AsyncClient() as client:
        try:
            target_url = f"{LOCATION_ENGINE_URL.rstrip('/')}/rider/nearby"
            response = await client.get(
                target_url,
                params={"latitude": lat, "longitude": lon, "radius_km": radius_km},
                timeout=5.0
            )
            data = response.json()
            drivers = data.get("drivers", [])
            formatted = []
            for d in drivers:
                formatted.append({
                    "driver_id": d["driver_id"],
                    "latitude": d.get("latitude", lat + 0.001),
                    "longitude": d.get("longitude", lon + 0.001),
                    "distance_km": d.get("distance_km", 0.0)
                })
            return formatted
        except Exception as e:
            logger.error(f"Error connecting to Location Engine ({LOCATION_ENGINE_URL}): {e}")
            return []

async def process_batch_queue(batch_queue: list):
    """
    Groups requests by Geohash grids and applies Hungarian Bipartite Matching
    to minimize total wait distance across all batched riders.
    """
    if not batch_queue:
        return

    logger.info(f"=== BATCH WINDOW TRIGGERED: Processing {len(batch_queue)} Ride Requests ===")

    geohash_clusters: dict[str, list] = {}
    for req in batch_queue:
        gh = encode_geohash(req['pickup_lat'], req['pickup_lon'], precision=6)
        req['geohash'] = gh
        geohash_clusters.setdefault(gh, []).append(req)

    for gh, riders in geohash_clusters.items():
        logger.info(f"Geohash Grid '{gh}': {len(riders)} batched rider(s)")

        center_lat = riders[0]['pickup_lat']
        center_lon = riders[0]['pickup_lon']

        drivers = await fetch_nearby_drivers(center_lat, center_lon, radius_km=5.0)

        if not drivers:
            logger.warning(f"No available drivers in Geohash Grid '{gh}' for {len(riders)} rider(s)")
            continue

        optimal_matches = solve_bipartite_matching(riders, drivers)
        logger.info(f"Optimal Bipartite Solver produced {len(optimal_matches)} matches for grid '{gh}'")

        for match in optimal_matches:
            driver_id = match['driver_id']
            rider_id = match['rider_id']

            lock_acquired = await redis_client.set(f"lock:driver:{driver_id}", "locked", nx=True, ex=30)
            if lock_acquired:
                logger.info(
                    f"SUCCESS [BIPARTITE MATCHED]: Driver '{driver_id}' -> Rider '{rider_id}' "
                    f"(Distance: {match['distance_km']}km, Geohash: {match['geohash']})"
                )
            else:
                logger.warning(f"Lock Contention: Driver '{driver_id}' already locked by another match worker")

async def start_batch_dispatch_worker():
    """
    Redis Stream Worker collecting ride requests over a 3-second window.
    Reads from stream 'ride_requests_stream'.
    """
    logger.info(f"Geohash & Bipartite Matchmaking Worker Connected to Redis Stream at {REDIS_URL}...")

    batch_queue = []
    last_batch_time = time.time()
    last_stream_id = "$"  # Start listening for new stream messages

    try:
        while True:
            # Poll Redis Stream with 500ms block
            response = await redis_client.xread(
                streams={"ride_requests_stream": last_stream_id},
                count=50,
                block=500
            )

            if response:
                for stream_name, messages in response:
                    for msg_id, payload in messages:
                        last_stream_id = msg_id
                        rider_data = {
                            "rider_id": payload.get("rider_id"),
                            "pickup_lat": float(payload.get("pickup_lat", 0.0)),
                            "pickup_lon": float(payload.get("pickup_lon", 0.0)),
                            "status": payload.get("status")
                        }
                        batch_queue.append(rider_data)
                        logger.info(f"Buffered request for Rider '{rider_data['rider_id']}' into 3s batch window")

            current_time = time.time()
            if (current_time - last_batch_time) >= BATCH_INTERVAL_SECONDS:
                if batch_queue:
                    await process_batch_queue(batch_queue)
                    batch_queue.clear()
                last_batch_time = current_time

    except Exception as e:
        logger.error(f"Redis Stream Consumer Error: {e}")

if __name__ == "__main__":
    asyncio.run(start_batch_dispatch_worker())
