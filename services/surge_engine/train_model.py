import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "surge_model.joblib")

def generate_synthetic_data(num_samples: int = 2000):
    """
    Generates synthetic historical ride data simulating rider demand and driver availability.
    """
    np.random.seed(42)

    active_riders = np.random.randint(5, 250, size=num_samples)
    available_drivers = np.random.randint(2, 100, size=num_samples)
    hour_of_day = np.random.randint(0, 24, size=num_samples)
    is_weekend = np.random.choice([0, 1], size=num_samples, p=[0.7, 0.3])

    demand_supply_ratio = active_riders / np.maximum(available_drivers, 1)

    # Peak hour bonus (e.g., 8-10 AM and 5-8 PM)
    peak_hour_flag = ((hour_of_day >= 8) & (hour_of_day <= 10)) | ((hour_of_day >= 17) & (hour_of_day <= 20))
    peak_bonus = np.where(peak_hour_flag, 0.35, 0.0)

    weekend_bonus = np.where(is_weekend == 1, 0.2, 0.0)

    # Calculate target surge multiplier with noise
    raw_surge = 1.0 + (0.25 * demand_supply_ratio) + peak_bonus + weekend_bonus + np.random.normal(0, 0.05, size=num_samples)
    surge_multiplier = np.clip(raw_surge, 1.0, 4.0)

    df = pd.DataFrame({
        "active_riders": active_riders,
        "available_drivers": available_drivers,
        "demand_supply_ratio": demand_supply_ratio,
        "hour_of_day": hour_of_day,
        "is_weekend": is_weekend,
        "surge_multiplier": surge_multiplier
    })

    return df

def train_and_save_model():
    """
    Trains a RandomForestRegressor model on historical ride data and persists the model.
    """
    print("Generating synthetic historical ride dataset...")
    df = generate_synthetic_data(num_samples=3000)

    features = ["active_riders", "available_drivers", "demand_supply_ratio", "hour_of_day", "is_weekend"]
    X = df[features]
    y = df["surge_multiplier"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training RandomForestRegressor model...")
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    r2 = r2_score(y_test, predictions)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))

    print(f"Model Training Complete!")
    print(f" - R2 Score: {r2:.4f}")
    print(f" - RMSE:     {rmse:.4f}")

    joblib.dump(model, MODEL_PATH)
    print(f"Model successfully saved to: {MODEL_PATH}")

    return model, {"r2_score": r2, "rmse": rmse}

if __name__ == "__main__":
    train_and_save_model()
