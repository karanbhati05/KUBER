import os
import sys
import time
import subprocess

print("======================================================================")
print("🚀 KUBER MASTER PYTHON FASTAPI MICROSERVICES LAUNCHER")
print("======================================================================")

services = [
    {"name": "Auth & RBAC Engine", "dir": "services/auth_engine", "port": 8006},
    {"name": "Surge Pricing Engine", "dir": "services/surge_engine", "port": 8004},
    {"name": "Verification Engine", "dir": "services/verification_engine", "port": 8005},
    {"name": "Location Engine", "dir": "services/location_engine", "port": 8000},
    {"name": "Dispatch Engine", "dir": "services/dispatch_engine", "port": 8001},
    {"name": "WebSocket Hub", "dir": "services/websocket_hub", "port": 8002},
    {"name": "Billing & Sharding Engine", "dir": "services/billing_engine", "port": 8003},
]

processes = []
base_dir = os.path.dirname(os.path.abspath(__file__))

for svc in services:
    svc_dir = os.path.join(base_dir, svc["dir"])
    if not os.path.exists(svc_dir):
        os.makedirs(svc_dir, exist_ok=True)

    cmd = [
        sys.executable, "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0",
        "--port", str(svc["port"]),
        "--reload"
    ]

    try:
        p = subprocess.Popen(cmd, cwd=svc_dir)
        processes.append((svc["name"], svc["port"], p))
        print(f"🟢 Started {svc['name']} on http://localhost:{svc['port']}")
    except Exception as e:
        print(f"🔴 Failed to start {svc['name']}: {e}")

print("----------------------------------------------------------------------")
print("✅ All Microservices launched successfully!")
print("🌐 Auth & RBAC Endpoint: http://localhost:8006")
print("🌐 Open login.html or index.html in your browser to interact with KUBER.")
print("======================================================================")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Shutting down KUBER Microservices...")
    for name, port, p in processes:
        p.terminate()
    print("👋 KUBER shutdown complete.")
