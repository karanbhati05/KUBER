import asyncio
import requests
import websockets
import json

LOCATION_URL = "http://127.0.0.1:8000"
DISPATCH_URL = "http://127.0.0.1:8001"
WS_URL = "ws://127.0.0.1:8002/ws/track/rider_karan_99"

def test_location_engine():
    print("--- 1. Testing Location Engine ---")
    
    # 1. Register a driver's location near Bandra
    driver_data = {
        "driver_id": "driver_alpha_77",
        "latitude": 19.0596,
        "longitude": 72.8400
    }
    res = requests.post(f"{LOCATION_URL}/driver/location", json=driver_data)
    print(f"Driver Registration Status: {res.status_code}, Response: {res.json()}")

    # 2. Query nearby drivers as a rider
    params = {
        "latitude": 19.0600,
        "longitude": 72.8350,
        "radius_km": 5
    }
    res = requests.get(f"{LOCATION_URL}/rider/nearby", params=params)
    print(f"Nearby Drivers Status: {res.status_code}")
    print("Drivers Found:", res.json())
    print("\n")

def test_dispatch_engine():
    print("--- 2. Testing Dispatch Engine (Kafka Queue) ---")
    
    # Send a ride request
    ride_data = {
        "rider_id": "rider_karan_99",
        "latitude": 19.0600,
        "longitude": 72.8350
    }
    res = requests.post(f"{DISPATCH_URL}/ride/request", json=ride_data)
    print(f"Ride Request Status: {res.status_code}, Response: {res.json()}")
    print("(Check your worker.py terminal to see the consumer pick this up!)\n")

async def test_websocket_stream():
    print("--- 3. Testing WebSocket Live Stream ---")
    print(f"Connecting to WebSocket stream at {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Receive 3 live coordinate updates streamed from the server
            for i in range(3):
                message = await websocket.recv()
                data = json.loads(message)
                print(f"WebSocket Ping {i+1} Received -> Status: {data['status']} | Lat: {data['driver_latitude']} | Lon: {data['driver_longitude']}")
    except Exception as e:
        print(f"WebSocket Connection Error (Is port 8002 running?): {e}")

if __name__ == "__main__":
    # Test HTTP APIs first
    test_location_engine()
    test_dispatch_engine()
    
    # Test WebSocket stream asynchronously
    asyncio.run(test_websocket_stream())