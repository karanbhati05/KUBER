import asyncio
import httpx

API_URL = "http://127.0.0.1:8000"

# Sample driver locations around Bandra / BKC area
DRIVERS = [
    {"driver_id": "driver_alpha", "latitude": 19.0596, "longitude": 72.8400},
    {"driver_id": "driver_beta",  "latitude": 19.0650, "longitude": 72.8680},
    {"driver_id": "driver_gamma", "latitude": 19.2300, "longitude": 72.8596}, # Further away (Juhu)
]

# Rider looking for a cab near Bandra West
RIDER_LOCATION = {"latitude": 19.0600, "longitude": 72.8350, "radius_km": 5}

async def run_simulation():
    async with httpx.AsyncClient() as client:
        print("--- 1. Simulating Driver GPS Pings ---")
        for driver in DRIVERS:
            response = await client.post(f"{API_URL}/driver/location", json=driver)
            print(f"Pinged location for {driver['driver_id']}: Status {response.status_code}")

        print("\n--- 2. Rider Searching for Nearby Cabs (5km radius) ---")
        response = await client.get(
            f"{API_URL}/rider/nearby",
            params=RIDER_LOCATION
        )
        print("API Response:")
        print(response.json())

if __name__ == "__main__":
    # Ensure httpx is installed: pip install httpx
    asyncio.run(run_simulation())