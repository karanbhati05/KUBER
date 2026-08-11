import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database Shard URLs (Use MySQL if configured, fallback to built-in SQLite)
mumbai_url = os.getenv("MYSQL_MUMBAI_URL") or "sqlite:///./kuber_shard_mumbai.db"
delhi_url = os.getenv("MYSQL_DELHI_URL") or "sqlite:///./kuber_shard_delhi.db"

SHARD_URLS = {
    "mumbai": mumbai_url,
    "delhi": delhi_url,
}

# Geographic Bounding Boxes for Shard Selection
SHARD_BOUNDS = {
    "mumbai": {"min_lat": 18.5, "max_lat": 19.5, "min_lon": 72.5, "max_lon": 73.5},
    "delhi":  {"min_lat": 28.0, "max_lat": 29.0, "min_lon": 76.5, "max_lon": 77.5},
}

# Engines for each Shard
shard_engines = {
    shard_key: create_engine(
        url, 
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
        echo=False
    )
    for shard_key, url in SHARD_URLS.items()
}

# Session Factories for each Shard
shard_sessions = {
    shard_key: sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    for shard_key, engine in shard_engines.items()
}

def resolve_shard_key(lat: float, lon: float) -> str:
    """
    Determines target database shard key based on start_lat and start_lon payload coordinates.
    """
    for shard_key, bounds in SHARD_BOUNDS.items():
        if (bounds["min_lat"] <= lat <= bounds["max_lat"]) and \
           (bounds["min_lon"] <= lon <= bounds["max_lon"]):
            return shard_key
    return "mumbai"  # Default fallback shard

def get_db_for_shard(shard_key: str):
    """
    Yields Session bound to the target database shard engine.
    """
    session_factory = shard_sessions.get(shard_key, shard_sessions["mumbai"])
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

def init_shard_databases(metadata):
    """
    Initializes tables across all database shards on startup.
    """
    for shard_key, engine in shard_engines.items():
        try:
            metadata.create_all(bind=engine)
            print(f"[SHARD INITIALIZATION] Schema initialized for shard: {shard_key}")
        except Exception as e:
            print(f"[SHARD INITIALIZATION WARNING] Could not connect to shard '{shard_key}': {e}")
