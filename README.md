# Project Antigravity 🚀⚡

**AI-Driven EV Charging Occupancy & ETA Prediction Engine**

Predict how long an electric vehicle will occupy a charging stall by combining real-time telemetry with a physics-informed neural network and historical idle-time adjustments.

---

## Architecture

```
┌──────────────────────┐     POST /heartbeat     ┌─────────────────────────────┐
│  Charging Station    │ ──────────────────────▶  │  Spring Boot Service        │
│  (Simulated OCPP)    │                          │                             │
└──────────────────────┘                          │  ┌─ HeartbeatController     │
                                                  │  │    ↓                     │
                                                  │  │  PredictionService ──────┼──▶ POST /predict
                                                  │  │    ↓                     │    ┌──────────────┐
                                                  │  │  BufferService           │    │ Flask ML API │
                                                  │  │    ↓                     │    │ PyTorch Net  │
                                                  │  │  PredictionResponse      │◀───│              │
                                                  │  └─────────────────────────│    └──────────────┘
                                                  └─────────────────────────────┘
```

## Components

### 🧠 ML Model (`ml_model/`)

| File | Description |
|---|---|
| `charging_physics.py` | CC-CV charging curve simulator with temperature derating |
| `generate_dataset.py` | Generates 50K synthetic training sessions |
| `model.py` | `ChargingETANet` — physics-informed feed-forward network |
| `train.py` | Training loop with early stopping, LR scheduling, checkpointing |
| `serve.py` | Flask REST API serving the trained model |

**Key Innovation:** The model computes **derived physics features** inside `forward()`:
- `energy_remaining = (1 - SoC/100) × battery_capacity`
- `effective_charge_rate = charger_kW × temp_factor`  
- `taper_indicator = max(0, (SoC - 80) / 20)` — captures CC→CV transition

### ☕ Spring Boot Service (`spring-boot-service/`)

| File | Description |
|---|---|
| `HeartbeatController` | REST endpoint for charger telemetry ingestion |
| `PredictionService` | Calls Python ML API with circuit breaker & fallback |
| `BufferService` | Adjusts ETA using historical idle-time buffer factor |
| `ChargingSession` | JPA entity tracking completed sessions |

**Buffer Factor Algorithm:**
```
bufferFactor = 1.0 + (avgIdleMinutes / avgChargingMinutes)
adjustedETA  = rawETA × bufferFactor
Clamped to:    bufferFactor ∈ [1.0, 2.0]
```

---

## Quick Start

### Prerequisites
- **Python 3.10+** with pip
- **Java 17+** with Maven
- ~2 GB disk space for PyTorch

### 1. Train the ML Model

```bash
cd ml_model

# Install dependencies
pip install -r requirements.txt

# Generate synthetic training data (50K sessions)
python generate_dataset.py

# Train the model (full run: ~100 epochs)
python train.py

# Or quick smoke test (10 epochs)
python train.py --quick
```

### 2. Start the ML API

```bash
cd ml_model
python serve.py --port 5000
```

Test it:
```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "current_soc": 45.0,
    "charger_max_kw": 150.0,
    "battery_capacity_kwh": 75.0,
    "ambient_temp_c": 22.0
  }'
```

### 3. Start the Spring Boot Service

```bash
cd spring-boot-service
mvn spring-boot:run
```

### 4. Send a Heartbeat

```bash
curl -X POST http://localhost:8080/api/telemetry/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "stationId": "CP-001",
    "connectorId": 1,
    "currentSoc": 45.0,
    "chargerMaxKw": 150.0,
    "batteryCapacityKwh": 75.0,
    "ambientTempC": 22.0,
    "vehicleId": "VH-TESLA-M3"
  }'
```

**Expected Response:**
```json
{
  "stationId": "CP-001",
  "connectorId": 1,
  "rawEtaMinutes": 38.7,
  "bufferFactor": 1.15,
  "adjustedEtaMinutes": 44.5,
  "predictedDisconnectTime": "2026-04-16T15:44:30Z",
  "confidence": "high",
  "currentSoc": 45.0,
  "status": "CHARGING"
}
```

---

## API Reference

### Python ML Service (port 5000)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/model/info` | Model metadata and input schema |
| `POST` | `/predict` | Single ETA prediction |
| `POST` | `/batch` | Batch predictions (up to 100) |

### Spring Boot Service (port 8080)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/telemetry/heartbeat` | Process charger heartbeat |
| `GET` | `/api/telemetry/status` | Service status |
| `GET` | `/actuator/health` | Spring Actuator health check |
| `GET` | `/h2-console` | H2 database console (dev only) |

---

## Charging Physics

The CC-CV (Constant Current → Constant Voltage) model:

```
Power
  │
  │  ┌────────────────────┐
  │  │   CC Phase          │╲
  │  │   (Full Power)      │  ╲  CV Phase
  │  │                     │    ╲  (Taper)
  │  │                     │      ╲
  │  │                     │        ╲───────
  └──┴─────────────────────┴────────────────── SoC %
     0%                   80%              100%
```

- **CC Phase (0-80%)**: Charger delivers maximum power
- **CV Phase (80-100%)**: BMS reduces current exponentially to protect cell voltage
- **Temperature**: Derates by ~1.2% per °C outside 20-35°C optimal range

---

## Project Structure

```
Chargepoint_project/
├── README.md
├── ml_model/
│   ├── requirements.txt
│   ├── charging_physics.py
│   ├── generate_dataset.py
│   ├── model.py
│   ├── train.py
│   ├── serve.py
│   ├── data/                    # Generated CSV (gitignored)
│   └── saved_models/            # Trained weights (gitignored)
└── spring-boot-service/
    ├── pom.xml
    └── src/main/
        ├── java/com/antigravity/
        │   ├── AntigravityApplication.java
        │   ├── config/AppConfig.java
        │   ├── controller/HeartbeatController.java
        │   ├── dto/
        │   │   ├── HeartbeatRequest.java
        │   │   ├── PredictionResponse.java
        │   │   ├── MlPredictionRequest.java
        │   │   └── MlPredictionResponse.java
        │   ├── exception/GlobalExceptionHandler.java
        │   ├── model/ChargingSession.java
        │   ├── repository/ChargingSessionRepository.java
        │   └── service/
        │       ├── PredictionService.java
        │       └── BufferService.java
        └── resources/
            └── application.yml
```

---

## License

Internal project — ChargePoint Technologies
