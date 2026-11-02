from __future__ import annotations
import os
from pathlib import Path
import re
import numpy as np
import pandas as pd
import joblib

FEATURES = ["Lag_1", "Lag_2", "Lag_3", "Lag_4", "Bulan", "Tahun"]

def train_forecast(df_panel: pd.DataFrame, steps: int = 6) -> dict:
    if df_panel.empty:
        return {"forecast": [], "metrics": {}, "feature_importance": [], "actual_prediction": [], "status": "No Data"}

    # Load model
    model_path = Path(__file__).resolve().parent.parent / "models" / "model_random_forest_campak.pkl"
    if not model_path.exists():
        return {
            "forecast": [], "metrics": {}, "feature_importance": [], "actual_prediction": [],
            "status": "Model file not found"
        }

    try:
        model_data = joblib.load(model_path)
        model = model_data["model"]
        features = model_data.get("fitur", FEATURES)
        jumlah_lag = model_data.get("jumlah_lag", 4)
    except Exception as e:
        print("Error loading model:", e)
        return {
            "forecast": [], "metrics": {}, "feature_importance": [], "actual_prediction": [],
            "status": f"Error loading model: {e}"
        }

    # Ensure capitalization of columns
    df_panel = df_panel.rename(columns={
        "kecamatan": "Kecamatan",
        "tahun": "Tahun",
        "bulan": "Bulan",
        "jumlah_kasus": "Jumlah_Kasus",
        "periode": "Periode"
    })
    
    # Sort
    df_panel = df_panel.sort_values(["Kecamatan", "Periode"]).reset_index(drop=True)
    
    # Create Lags
    for lag in range(1, jumlah_lag + 1):
        df_panel[f"Lag_{lag}"] = df_panel.groupby("Kecamatan")["Jumlah_Kasus"].shift(lag)
        
    df_panel["Bulan"] = df_panel["Periode"].dt.month
    df_panel["Tahun"] = df_panel["Periode"].dt.year
    
    # Drop rows with NaNs in features
    df_clean = df_panel.dropna(subset=[f"Lag_{i}" for i in range(1, jumlah_lag + 1)]).copy()
    
    # Run predictions on all historical data
    if not df_clean.empty:
        df_clean["Prediksi"] = np.maximum(0.0, model.predict(df_clean[features]))
    else:
        df_clean["Prediksi"] = []

    # Calculate metrics on 2025 data as test set
    test_df = df_clean[df_clean["Tahun"] == 2025].copy()
    metrics = {}
    actual_prediction = []
    if not test_df.empty:
        y_true = test_df["Jumlah_Kasus"].to_numpy(dtype=float)
        y_pred = test_df["Prediksi"].to_numpy(dtype=float)
        mae = float(np.mean(np.abs(y_true - y_pred)))
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        denom = np.where(y_true == 0, 1, y_true)
        mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100)
        metrics = {
            "MAE": round(mae, 3),
            "RMSE": round(rmse, 3),
            "MAPE": round(mape, 3),
            "R2": "-"
        }
        for _, r in test_df.iterrows():
            actual_prediction.append({
                "kecamatan": r["Kecamatan"],
                "bulan": int(r["Bulan"]),
                "actual": int(r["Jumlah_Kasus"]),
                "predicted": round(float(r["Prediksi"]), 3)
            })

    # Feature Importance
    importances = model.feature_importances_ if hasattr(model, "feature_importances_") else np.zeros(len(features))
    feature_importance = [
        {"feature": f, "importance": round(float(v), 4)}
        for f, v in zip(features, importances)
    ]
    feature_importance = sorted(feature_importance, key=lambda x: x["importance"], reverse=True)

    # Multi-step sequential forecast
    periode_terakhir = df_panel["Periode"].max()
    current_panel = df_panel.copy()
    forecast = []
    kecs = current_panel["Kecamatan"].unique()
    
    for step in range(1, steps + 1):
        rows = []
        next_periode = periode_terakhir + pd.offsets.MonthBegin(step)
        
        for kec in kecs:
            sub = current_panel[current_panel["Kecamatan"] == kec].sort_values("Periode")
            last_vals = sub["Jumlah_Kasus"].values
            
            lag1 = float(last_vals[-1])
            lag2 = float(last_vals[-2]) if len(last_vals) >= 2 else 0.0
            lag3 = float(last_vals[-3]) if len(last_vals) >= 3 else 0.0
            lag4 = float(last_vals[-4]) if len(last_vals) >= 4 else 0.0
            
            rows.append({
                "Kecamatan": kec,
                "Periode": next_periode,
                "Tahun": next_periode.year,
                "Bulan": next_periode.month,
                "Lag_1": lag1,
                "Lag_2": lag2,
                "Lag_3": lag3,
                "Lag_4": lag4,
                "Jumlah_Kasus": 0.0
            })
            
        df_step = pd.DataFrame(rows)
        df_step["Jumlah_Kasus"] = np.maximum(0.0, model.predict(df_step[features]))
        
        for _, r in df_step.iterrows():
            forecast.append({
                "kecamatan": r["Kecamatan"],
                "bulan": int(r["Bulan"]),
                "step": step,
                "predicted": round(float(r["Jumlah_Kasus"]), 3)
            })
            
        current_panel = pd.concat([current_panel, df_step], ignore_index=True)

    return {
        "forecast": forecast,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "actual_prediction": actual_prediction,
        "status": "Baik"
    }


