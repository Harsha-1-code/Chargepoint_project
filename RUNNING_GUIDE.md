# Antigravity Charging Service — Running Guide

This guide explains how to set up, verify, and run the Antigravity Charging ETA Service, which consists of a Python ML Model (Flask) and a Spring Boot Backend.

---

## 1. Prerequisites

### Environment Variables
Ensure the following are set in your system/user variables:
- **JAVA_HOME**: `C:\Program Files\Java\jdk-24`
- **MAVEN_HOME**: `C:\apache-maven-3.9.14`
- **Path**: Add `%MAVEN_HOME%\bin` to your Path.

### Software
- **Java 24** (or 17+)
- **Maven 3.9+**
- **Python 3.10+**

---

## 2. ML Model Setup & Verification

The ML model predicts the Time-to-Disconnect (ETA) based on charger telemetry.

### Step 2.1: Virtual Environment
Navigate to the `ml_model` directory and set up a virtual environment:
```powershell
cd ml_model
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2.2: Generate Synthetic Data
Generate a sample dataset (100 sessions by default for verification):
```powershell
python generate_dataset.py
```

### Step 2.3: Train the Model (Smoke Train)
Verify the training loop works with a quick run:
```powershell
python train.py --quick
```
*The model will be saved to `ml_model/saved_models/charging_eta_model.pth`.*

### Step 2.4: Start the ML Service
Start the Flask API to serve predictions:
```powershell
python serve.py
```
*The service runs on `http://localhost:5000` by default.*

---

## 3. Spring Boot Backend Setup

The backend ingests telemetry from chargers and calls the ML service.

### Step 3.1: Build the Project
Navigate to the `spring-boot-service` directory and build using Maven:
```powershell
cd spring-boot-service
mvn clean compile
```
*Note: We have removed Lombok to ensure compatibility with JDK 24.*

### Step 3.2: Run the Service
```powershell
mvn spring-boot:run
```
*The backend runs on `http://localhost:8080`.*

---

## 4. End-to-End Verification

Once both services are running:
1. **ML Service**: Confirm `http://localhost:5000/predict` is active.
2. **Spring Boot**: Confirm `http://localhost:8080/api/telemetry/heartbeat` is active.

### Sample Heartbeat Request
You can test the integration using a tool like Postman or `curl`:
```bash
POST http://localhost:8080/api/telemetry/heartbeat
Content-Type: application/json

{
  "stationId": "CP-001",
  "connectorId": 1,
  "currentSoc": 45.0,
  "chargerMaxKw": 50.0,
  "batteryCapacityKwh": 75.0,
  "ambientTempC": 22.0
}
```

---

## Troubleshooting
- **Lombok Errors**: If you see compilation errors related to Lombok, ensure you are using the latest version of the code where Lombok was replaced with standard Java POJOs (required for JDK 24).
- **Python Unicode Errors**: If `train.py` fails with a Unicode error in the terminal, the code has been updated to use ASCII status symbols (`* BEST` instead of stars).
