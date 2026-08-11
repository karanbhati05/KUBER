import os
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import redis.asyncio as redis
try:
    from matchmaker import encode_geohash, solve_bipartite_matching
except ModuleNotFoundError:
    from services.dispatch_engine.matchmaker import encode_geohash, solve_bipartite_matching


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="KUBER Dispatch Engine (Upstash QStash Integrated)",
    description="Handles ride requests via Upstash QStash HTTP message queues and Redis Streams"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Environment Variables for Upstash Services
QSTASH_URL = os.getenv("QSTASH_URL", "https://qstash-eu-central-1.upstash.io").rstrip('/')
QSTASH_TOKEN = os.getenv("QSTASH_TOKEN", None)
DISPATCH_WORKER_URL = os.getenv("DISPATCH_WORKER_URL", "http://localhost:8001/dispatch/process")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LOCATION_ENGINE_URL = os.getenv("LOCATION_ENGINE_URL", "http://localhost:8000")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class RideRequest(BaseModel):
    rider_id: str
    latitude: float
    longitude: float

@app.on_event("startup")
async def startup_event():
    """Startup check for Redis and QStash configuration."""
    try:
        await redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        logger.warning(f"Redis connection warning: {e}. Operating in fallback mode.")

    if QSTASH_TOKEN:
        logger.info(f"Upstash QStash Active -> Endpoint: {QSTASH_URL} | Webhook Target: {DISPATCH_WORKER_URL}")
    else:
        logger.info("QSTASH_TOKEN not set -> Operating in Dispatch fallback mode")


@app.post("/ride/request")
async def request_ride(request: RideRequest):
    """
    Accepts ride request and publishes to Upstash QStash Serverless HTTP Queue.
    """
    event_data = {
        "rider_id": request.rider_id,
        "pickup_lat": request.latitude,
        "pickup_lon": request.longitude,
        "status": "SEARCHING"
    }

    # Publish via Upstash QStash if token is present
    if QSTASH_TOKEN:
        try:
            target_url = f"{QSTASH_URL}/v2/publish/{DISPATCH_WORKER_URL}"
            headers = {
                "Authorization": f"Bearer {QSTASH_TOKEN}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient() as client:
                res = await client.post(target_url, headers=headers, json=event_data, timeout=5.0)

            if res.status_code in (200, 201, 202):
                qstash_res = res.json()
                return {
                    "status": "processing",
                    "queue_provider": "Upstash QStash",
                    "message_id": qstash_res.get("messageId"),
                    "event": event_data
                }
            else:
                raise HTTPException(status_code=500, detail=f"QStash publish error: {res.text}")
        except Exception as e:
            logger.error(f"Failed to publish to Upstash QStash: {e}")
            raise HTTPException(status_code=500, detail=f"QStash Queue Error: {str(e)}")

    # Fallback to Redis Stream
    try:
        msg_id = await redis_client.xadd("ride_requests_stream", {
            "rider_id": request.rider_id,
            "pickup_lat": str(request.latitude),
            "pickup_lon": str(request.longitude),
            "status": "SEARCHING"
        })
        return {
            "status": "processing",
            "queue_provider": "Redis Stream",
            "stream_id": msg_id,
            "event": event_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Queue Error: {str(e)}")

@app.post("/dispatch/process")
async def process_qstash_webhook(req: Request):
    """
    QStash Webhook Receiver: Asynchronously called by Upstash QStash to process ride requests.
    Executes Geohashing & Bipartite Driver Matchmaking.
    """
    try:
        body = await req.json()
        rider_id = body.get("rider_id")
        lat = float(body.get("pickup_lat", 0.0))
        lon = float(body.get("pickup_lon", 0.0))

        logger.info(f"[QSTASH WEBHOOK RECEIVED] Processing rider '{rider_id}' at ({lat}, {lon})")

        # Encode Geohash
        gh = encode_geohash(lat, lon, precision=6)

        # Fetch nearby drivers
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{LOCATION_ENGINE_URL.rstrip('/')}/rider/nearby",
                params={"latitude": lat, "longitude": lon, "radius_km": 5.0},
                timeout=5.0
            )
            nearby_data = resp.json()
            drivers = nearby_data.get("drivers", [])

        if not drivers:
            logger.warning(f"No available drivers in Geohash Grid '{gh}' for Rider '{rider_id}'")
            return {"status": "no_drivers", "geohash": gh}

        formatted_drivers = [
            {
                "driver_id": d["driver_id"],
                "latitude": d.get("latitude", lat + 0.001),
                "longitude": d.get("longitude", lon + 0.001),
                "distance_km": d.get("distance_km", 0.0)
            }
            for d in drivers
        ]

        # Execute Bipartite Matching
        riders_batch = [{"rider_id": rider_id, "pickup_lat": lat, "pickup_lon": lon}]
        optimal_matches = solve_bipartite_matching(riders_batch, formatted_drivers)

        if optimal_matches:
            match = optimal_matches[0]
            matched_driver_id = match['driver_id']

            # Acquire Redis Distributed Lock
            lock_acquired = await redis_client.set(f"lock:driver:{matched_driver_id}", "locked", nx=True, ex=30)
            if lock_acquired:
                logger.info(f"SUCCESS [QSTASH MATCHED]: Driver '{matched_driver_id}' -> Rider '{rider_id}' (Dist: {match['distance_km']}km)")
                return {
                    "status": "matched",
                    "rider_id": rider_id,
                    "driver_id": matched_driver_id,
                    "distance_km": match['distance_km'],
                    "geohash": gh
                }

        return {"status": "lock_contention", "message": "Matched driver busy"}

    except Exception as e:
        logger.error(f"Error processing QStash webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))