# Project Antigravity — EV Charging Time-to-Disconnect Prediction Engine

Predict how long an EV will remain at a charging stall by combining real-time telemetry with a physics-informed neural network and historical idle-time adjustments.

## User Review Required

> [!IMPORTANT]
> **Model Serving Strategy**: The plan uses a **Flask REST API** to serve the PyTorch model, which the Spring Boot backend calls over HTTP. An alternative is **ONNX Runtime in Java** (no Python dependency at runtime). Which approach do you prefer?

> [!IMPORTANT]
> **Simulated vs. Real Data**: This initial version generates **synthetic training data** using the CC-CV (Constant Current → Constant Voltage) charging physics model. Should we also scaffold a data pipeline for real ChargePoint CSV data?

> [!WARNING]
> **JNI Alternative**: JNI integration with PyTorch (via LibTorch C++) is significantly more complex and fragile. The plan avoids it in favour of HTTP microservice communication. Confirm if this is acceptable.

---

## Architecture Overview

```mermaid
graph LR
    subgraph "Charging Station (Simulated)"
        CS[OCPP Heartbeat / MeterValues]
    end

    subgraph "Java Spring Boot Service"
        HC[HeartbeatController<br>REST Endpoint]
        BS[BufferService<br>Idle-Time Adjustment]
        PC[PredictionClient<br>HTTP → Python]
    end

    subgraph "Python ML Service (Flask)"
        API[/predict endpoint]
        MODEL[PyTorch Model<br>ChargingETANet]
    end

    CS -->|POST /api/telemetry/heartbeat| HC
    HC --> PC
    PC -->|POST /predict| API
    API --> MODEL
    MODEL -->|ETA minutes| API
    API -->|raw_eta| PC
    PC --> BS
    BS -->|adjusted_eta| HC
```

---

## Proposed Changes

### Component 1: PyTorch ML Model & Training Pipeline (Python)

This component handles synthetic data generation, model architecture, training, and persistence.

---

#### [NEW] [charging_physics.py](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/charging_physics.py)

Physics-based EV charging simulator that models the **CC-CV curve** (constant-current below ~80% SoC, then exponential taper):

- `simulate_charging_session()` — generates a complete session with time-to-100% given `(soc_start, charger_kw, battery_kwh, temp_c)`
- Temperature derating: charging speed reduced by ~1% per °C below 20°C and above 40°C
- Outputs: `time_to_full_minutes`, `time_to_disconnect_minutes` (includes random idle tail)

#### [NEW] [generate_dataset.py](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/generate_dataset.py)

Generates **50,000 synthetic charging sessions** using `charging_physics.py`:

| Feature | Range |
|---|---|
| `current_soc` | 5% – 95% |
| `charger_max_kw` | 7 – 350 kW |
| `battery_capacity_kwh` | 30 – 120 kWh |
| `ambient_temp_c` | -10 – 45 °C |

Target: `time_to_disconnect_minutes` (float)

Saves to `data/training_data.csv`.

#### [NEW] [model.py](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/model.py)

**`ChargingETANet`** — A feed-forward regression network:

```
Input (4) → Linear(64) → ReLU → BatchNorm
          → Linear(128) → ReLU → Dropout(0.2) → BatchNorm
          → Linear(64) → ReLU
          → Linear(1)  [output: minutes]
```

Key design decisions:
- **Physics-informed feature engineering**: Adds derived features inside `forward()`:
  - `energy_remaining = (1 - soc/100) * battery_kwh`
  - `effective_charge_rate = charger_kw * temp_factor`
  - `taper_indicator = max(0, (soc - 80) / 20)`  (captures the non-linear slowdown)
- Input expands from 4 raw → 7 engineered features before the first linear layer
- BatchNorm for training stability across varied input scales
- Dropout for regularization

#### [NEW] [train.py](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/train.py)

Full training pipeline:
- Loads `data/training_data.csv`, splits 80/20 train/val
- Standardizes features with `sklearn.StandardScaler` (saved via `joblib`)
- Training: **Adam optimizer**, **MSE loss**, **100 epochs**, batch size 256
- Learning rate scheduler: `ReduceLROnPlateau`
- Early stopping after 10 epochs of no improvement
- Saves best model to `saved_models/charging_eta_model.pth`
- Saves scaler to `saved_models/feature_scaler.joblib`
- Prints final MAE (Mean Absolute Error) on validation set

#### [NEW] [serve.py](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/serve.py)

Flask REST API serving the trained model:

```
POST /predict
Body: { "current_soc": 45.0, "charger_max_kw": 150.0,
        "battery_capacity_kwh": 75.0, "ambient_temp_c": 22.0 }

Response: { "predicted_eta_minutes": 38.7, "confidence": "medium" }
```

- Loads model + scaler on startup
- Returns confidence level based on input range coverage
- Health check at `GET /health`

#### [NEW] [requirements.txt](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/ml_model/requirements.txt)

```
torch>=2.0
numpy
pandas
scikit-learn
joblib
flask
```

---

### Component 2: Java Spring Boot Backend

Handles charger telemetry ingestion, calls the ML prediction service, and applies the buffer factor.

---

#### [NEW] [pom.xml](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/pom.xml)

Spring Boot 3.2+ project with dependencies:
- `spring-boot-starter-web`
- `spring-boot-starter-data-jpa` (for session history)
- `spring-boot-starter-validation`
- `lombok`
- `h2` (in-memory DB for demo)

#### [NEW] [HeartbeatController.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/controller/HeartbeatController.java)

```java
@RestController
@RequestMapping("/api/telemetry")
public class HeartbeatController {
    @PostMapping("/heartbeat")
    public ResponseEntity<PredictionResponse> handleHeartbeat(
        @Valid @RequestBody HeartbeatRequest request) { ... }
}
```

- Accepts: `stationId`, `connectorId`, `currentSoc`, `chargerMaxKw`, `batteryCapacityKwh`, `ambientTempC`, `timestamp`
- Calls `PredictionService` → which calls the Python Flask API
- Applies `BufferService` to adjust raw ETA
- Returns `PredictionResponse` with `rawEtaMinutes`, `adjustedEtaMinutes`, `bufferFactor`

#### [NEW] [HeartbeatRequest.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/dto/HeartbeatRequest.java)

DTO with Bean Validation annotations (`@NotNull`, `@Min`, `@Max`).

#### [NEW] [PredictionResponse.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/dto/PredictionResponse.java)

Response DTO with `rawEtaMinutes`, `adjustedEtaMinutes`, `bufferFactor`, `predictedDisconnectTime`.

#### [NEW] [PredictionService.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/service/PredictionService.java)

Calls the Python ML service via `RestTemplate` / `WebClient`:
- Timeout: 2 seconds
- Fallback: simple linear estimation if ML service is unavailable
- Circuit breaker pattern (basic)

#### [NEW] [BufferService.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/service/BufferService.java)

**Buffer Factor Algorithm**:

```
bufferFactor = 1.0 + (avgIdleMinutes / avgChargingMinutes)

adjustedEta = rawEta × bufferFactor

Clamped to: bufferFactor ∈ [1.0, 2.0]
```

- Queries historical `ChargingSession` records for the given station
- If no history → default buffer = 1.15 (15% overshoot)
- Updates as more sessions complete

#### [NEW] [ChargingSession.java](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/java/com/antigravity/model/ChargingSession.java)

JPA entity tracking completed sessions:
- `sessionId`, `stationId`, `startSoc`, `endSoc`, `chargingDurationMinutes`, `idleDurationMinutes`, `totalDurationMinutes`, `timestamp`

#### [NEW] [application.yml](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/spring-boot-service/src/main/resources/application.yml)

```yaml
server:
  port: 8080
ml-service:
  url: http://localhost:5000
  timeout-ms: 2000
buffer:
  default-factor: 1.15
  max-factor: 2.0
```

---

### Component 3: Project Documentation

#### [NEW] [README.md](file:///c:/Users/harsh/OneDrive/Documents/Chargepoint_project/README.md)

Project overview, architecture diagram, setup instructions for both Python and Java components, and example API calls.

---

## Project Structure

```
Chargepoint_project/
├── README.md
├── ml_model/
│   ├── requirements.txt
│   ├── charging_physics.py        # CC-CV simulator
│   ├── generate_dataset.py        # Synthetic data generator
│   ├── model.py                   # ChargingETANet architecture
│   ├── train.py                   # Training loop
│   ├── serve.py                   # Flask REST API
│   ├── data/                      # Generated CSV (gitignored)
│   └── saved_models/              # Trained weights (gitignored)
└── spring-boot-service/
    ├── pom.xml
    └── src/main/java/com/antigravity/
        ├── AntigravityApplication.java
        ├── controller/
        │   └── HeartbeatController.java
        ├── dto/
        │   ├── HeartbeatRequest.java
        │   └── PredictionResponse.java
        ├── service/
        │   ├── PredictionService.java
        │   └── BufferService.java
        └── model/
            └── ChargingSession.java
```

---

## Open Questions

> [!IMPORTANT]
> 1. **Model serving**: REST (Flask) vs ONNX Runtime (pure Java)? REST is simpler but adds a network hop. ONNX eliminates the Python runtime dependency.

> [!NOTE]
> 2. **Database**: The plan uses H2 (embedded, in-memory) for demo purposes. Should we scaffold PostgreSQL configs for production?

> [!NOTE]
> 3. **OCPP Protocol**: The current design uses a simplified REST endpoint to simulate heartbeats. True OCPP 1.6/2.0 integration would require WebSocket handlers. Should we add that layer?

---

## Verification Plan

### Automated Tests
1. **Python model**: Generate dataset → train for 10 epochs → assert MAE < 30 minutes on validation set
2. **Flask API**: `curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d '{"current_soc": 45, "charger_max_kw": 150, "battery_capacity_kwh": 75, "ambient_temp_c": 22}'` → verify valid JSON response
3. **Spring Boot**: Run `mvn spring-boot:run` → test heartbeat endpoint with sample payloads

### Manual Verification
- Verify the charging curve physics: a 50 kW charger on a 75 kWh battery from 20% SoC should predict ~45-55 min (matches real-world CCS charging)
- Verify taper behavior: predictions from 85% → 100% should be significantly longer per % than 20% → 80%
- Verify buffer factor: default 1.15x multiplier applied when no history exists
