"""
serve.py — Flask REST API for ChargingETANet Inference

Serves the trained PyTorch model via:
  POST /predict   — single prediction
  POST /batch     — batch predictions
  GET  /health    — health check

Usage:
  python serve.py                 # Production mode (port 5000)
  python serve.py --debug         # Debug mode with auto-reload
  python serve.py --port 8000     # Custom port
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timezone

import numpy as np
import torch
import joblib
from flask import Flask, request, jsonify

from model import ChargingETANet

# ──────────────────────── Configuration ────────────────────────

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(MODEL_DIR, "charging_eta_model.pth")
SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.joblib")

# Input validation ranges
INPUT_RANGES = {
    "current_soc":          (0.0, 100.0),
    "charger_max_kw":       (1.0, 400.0),
    "battery_capacity_kwh": (10.0, 200.0),
    "ambient_temp_c":       (-30.0, 55.0),
}

REQUIRED_FIELDS = list(INPUT_RANGES.keys())

# ──────────────────────── App Setup ────────────────────────────

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Global model and scaler (loaded once at startup)
model = None
scaler = None
device = "cpu"  # Inference on CPU for low-latency serving


def load_model():
    """Load the trained model and scaler into memory."""
    global model, scaler

    if not os.path.exists(MODEL_PATH):
        logger.error(f"Model file not found: {MODEL_PATH}")
        logger.error("Run 'python train.py' first to train the model.")
        sys.exit(1)

    if not os.path.exists(SCALER_PATH):
        logger.error(f"Scaler file not found: {SCALER_PATH}")
        sys.exit(1)

    # Load model
    model = ChargingETANet()
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Load scaler
    scaler = joblib.load(SCALER_PATH)

    logger.info(f"Model loaded from: {MODEL_PATH}")
    logger.info(f"  Trained for {checkpoint.get('epoch', '?')} epochs")
    logger.info(f"  Val MAE: {checkpoint.get('val_mae', '?'):.2f} min")
    logger.info(f"Scaler loaded from: {SCALER_PATH}")


def validate_input(data: dict) -> tuple:
    """
    Validate input data.
    Returns (is_valid, error_message, warnings).
    """
    errors = []
    warnings = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")
            continue

        value = data[field]
        if not isinstance(value, (int, float)):
            errors.append(f"'{field}' must be a number, got {type(value).__name__}")
            continue

        low, high = INPUT_RANGES[field]
        if value < low or value > high:
            errors.append(f"'{field}' = {value} is outside valid range [{low}, {high}]")

    # Warnings for edge cases
    if "current_soc" in data and isinstance(data["current_soc"], (int, float)):
        if data["current_soc"] > 95:
            warnings.append("SoC > 95%: vehicle is nearly full, ETA may be very short")
        if data["current_soc"] < 5:
            warnings.append("SoC < 5%: extremely low charge, consider emergency charging")

    if errors:
        return False, "; ".join(errors), warnings
    return True, None, warnings


def compute_confidence(data: dict) -> str:
    """
    Estimate prediction confidence based on how typical the inputs are.
    
    Returns: 'high', 'medium', or 'low'
    """
    soc = data["current_soc"]
    charger_kw = data["charger_max_kw"]
    battery_kwh = data["battery_capacity_kwh"]
    temp_c = data["ambient_temp_c"]

    score = 0

    # SoC: most data is 10-80%
    if 10 <= soc <= 80:
        score += 2
    elif 5 <= soc <= 95:
        score += 1

    # Charger: common ranges
    if 7 <= charger_kw <= 350:
        score += 2
    elif charger_kw <= 400:
        score += 1

    # Battery: common sizes
    if 30 <= battery_kwh <= 120:
        score += 2
    elif 20 <= battery_kwh <= 150:
        score += 1

    # Temperature: trained range
    if -10 <= temp_c <= 45:
        score += 2
    elif -20 <= temp_c <= 50:
        score += 1

    if score >= 7:
        return "high"
    elif score >= 4:
        return "medium"
    return "low"


@torch.no_grad()
def predict_single(data: dict) -> dict:
    """
    Run inference for a single input.
    Returns prediction dict with ETA and metadata.
    """
    features = np.array([[
        data["current_soc"],
        data["charger_max_kw"],
        data["battery_capacity_kwh"],
        data["ambient_temp_c"],
    ]], dtype=np.float32)

    input_tensor = torch.tensor(features, dtype=torch.float32).to(device)
    prediction = model(input_tensor)
    eta_minutes = max(0.0, float(prediction.item()))

    confidence = compute_confidence(data)

    return {
        "predicted_eta_minutes": round(eta_minutes, 1),
        "confidence": confidence,
        "input_received": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ──────────────────────── API Routes ──────────────────────────

@app.route("/", methods=["GET"])
def index():
    """Root endpoint for the API."""
    return jsonify({
        "message": "ChargingETANet ML API is running",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "batch": "/batch (POST)",
            "info": "/model/info"
        },
        "status": "online"
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    })


@app.route("/predict", methods=["POST"])
def predict():
    """
    Single prediction endpoint.
    
    Request body:
    {
        "current_soc": 45.0,
        "charger_max_kw": 150.0,
        "battery_capacity_kwh": 75.0,
        "ambient_temp_c": 22.0
    }
    
    Response:
    {
        "predicted_eta_minutes": 38.7,
        "confidence": "high",
        "input_received": { ... },
        "timestamp": "2026-04-16T..."
    }
    """
    if model is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    is_valid, error_msg, warnings = validate_input(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 422

    try:
        result = predict_single(data)
        if warnings:
            result["warnings"] = warnings
        return jsonify(result)
    except Exception as e:
        logger.exception("Prediction failed")
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/batch", methods=["POST"])
def batch_predict():
    """
    Batch prediction for multiple vehicles.
    
    Request body:
    {
        "predictions": [
            { "current_soc": 45.0, "charger_max_kw": 150.0, ... },
            { "current_soc": 80.0, "charger_max_kw": 50.0, ... }
        ]
    }
    """
    if model is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json()
    if not data or "predictions" not in data:
        return jsonify({"error": "Expected JSON with 'predictions' array"}), 400

    items = data["predictions"]
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "'predictions' must be a non-empty array"}), 400

    if len(items) > 100:
        return jsonify({"error": "Maximum 100 predictions per batch"}), 400

    results = []
    for i, item in enumerate(items):
        is_valid, error_msg, warnings = validate_input(item)
        if not is_valid:
            results.append({"index": i, "error": error_msg})
        else:
            try:
                result = predict_single(item)
                result["index"] = i
                if warnings:
                    result["warnings"] = warnings
                results.append(result)
            except Exception as e:
                results.append({"index": i, "error": str(e)})

    return jsonify({
        "results": results,
        "total": len(items),
        "successful": sum(1 for r in results if "error" not in r),
    })


@app.route("/model/info", methods=["GET"])
def model_info():
    """Return model metadata and input schema."""
    return jsonify({
        "model_name": "ChargingETANet",
        "version": "1.0.0",
        "description": "EV charging time-to-disconnect prediction",
        "input_schema": {
            field: {"type": "float", "range": list(rng)}
            for field, rng in INPUT_RANGES.items()
        },
        "output_schema": {
            "predicted_eta_minutes": "float (minutes until vehicle disconnects)",
            "confidence": "string (high | medium | low)",
        },
    })


# ──────────────────────── Entry Point ─────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChargingETANet Inference API")
    parser.add_argument("--port", type=int, default=5000, help="Port to serve on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    load_model()

    logger.info(f"Starting ChargingETANet API on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
