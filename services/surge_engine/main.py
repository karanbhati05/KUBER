from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import joblib
import os
try:
    from train_model import train_and_save_model, MODEL_PATH
except ModuleNotFoundError:
    from services.surge_engine.train_model import train_and_save_model, MODEL_PATH


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="KUBER Surge Pricing Engine",
    description="ML-powered microservice serving dynamic surge pricing multipliers using Scikit-Learn RandomForest"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global model instance
model = None

class SurgePredictRequest(BaseModel):
    active_riders: int = Field(..., ge=0, description="Count of active riders seeking rides in the zone")
    available_drivers: int = Field(..., ge=0, description="Count of available drivers in the zone")
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    is_weekend: int = Field(0, ge=0, le=1, description="1 if weekend, 0 if weekday")

@app.on_event("startup")
async def startup():
    """Load pre-trained model or train model if not present."""
    global model
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            print(f"[SURGE ENGINE] Successfully loaded pre-trained model from {MODEL_PATH}")
        except Exception as e:
            print(f"[SURGE ENGINE] Error loading model: {e}. Retraining...")
            model, _ = train_and_save_model()
    else:
        print("[SURGE ENGINE] Model file not found. Initializing training...")
        model, _ = train_and_save_model()

@app.post("/surge/predict")
async def predict_surge(request: SurgePredictRequest):
    """
    Predicts real-time surge pricing multiplier based on demand-supply ratio and temporal features.
    """
    global model
    if model is None:
        raise HTTPException(status_code=500, detail="ML model is not loaded.")

    demand_supply_ratio = request.active_riders / max(request.available_drivers, 1)

    # Feature vector matching training columns
    feature_df = pd.DataFrame([{
        "active_riders": request.active_riders,
        "available_drivers": request.available_drivers,
        "demand_supply_ratio": demand_supply_ratio,
        "hour_of_day": request.hour_of_day,
        "is_weekend": request.is_weekend
    }])

    try:
        raw_pred = model.predict(feature_df)[0]
        clamped_multiplier = float(np.clip(raw_pred, 1.0, 4.0))
        final_multiplier = round(clamped_multiplier, 2)

        # Categorize surge level
        if final_multiplier <= 1.2:
            category = "NORMAL"
        elif final_multiplier <= 2.0:
            category = "MODERATE_SURGE"
        else:
            category = "HIGH_SURGE"

        return {
            "status": "success",
            "surge_multiplier": final_multiplier,
            "demand_supply_ratio": round(demand_supply_ratio, 2),
            "surge_category": category,
            "input_metrics": {
                "active_riders": request.active_riders,
                "available_drivers": request.available_drivers,
                "hour_of_day": request.hour_of_day,
                "is_weekend": request.is_weekend
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")

@app.post("/surge/retrain")
async def retrain_model():
    """
    Triggers model retraining on new historical data and updates memory model reference.
    """
    global model
    try:
        new_model, metrics = train_and_save_model()
        model = new_model
        return {
            "status": "success",
            "message": "Surge pricing model retrained successfully.",
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")
