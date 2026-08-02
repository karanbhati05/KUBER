from fastapi import FastAPI , WebSocket , WebSocketDisconnect
import asyncio
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title = "KUBER WebSocket Hub",
    description = "Streams real-time GPS coordinates to the rider's app"
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str,WebSocket] = {}
    
    async def connect(self , websocket: WebSocket, rider_id: str):
        await websocket.accept()
        self.active_connections[rider_id] = websocket
        logger.info(f"Rider {rider_id} connected to live tracking...")
    
    def disconnect(self , rider_id: str):
        if rider_id in self.active_connections:
            del self.active_connections[rider_id]
            logger.info(f"Rider {rider_id} disconnected.")
        
    async def send_location(self, rider_id: str , data: dict):
        if rider_id in self.active_connections:
            websocket = self.active_connections[rider_id]
            await websocket.send_json(data)
manager = ConnectionManager()

@app.websocket("/ws/track/{rider_id}")
async def track_ride(websocket: WebSocket , rider_id: str):
    "the endopoint the riders phone connect to after a driver is matched"
    await manager.connect(websocket, rider_id)
    try:
        lat, lon = 19.0600, 72.8350
        while True:
            await asyncio.sleep(2)
            lat += 0.0002
            lon += 0.0001

            payload = {
                "status": "en_route",
                "driver_latitude": round(lat,6),
                "driver_longitude": round(lon,6),
            }

            await manager.send_location(rider_id, payload)
    except WebSocketDisconnect:
        manager.disconnect(rider_id)

    

    
