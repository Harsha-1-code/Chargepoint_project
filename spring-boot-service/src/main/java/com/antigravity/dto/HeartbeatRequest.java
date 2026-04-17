package com.antigravity.dto;

import jakarta.validation.constraints.*;

import java.time.Instant;

/**
 * HeartbeatRequest — Incoming telemetry from a charging station.
 *
 * Maps to the OCPP MeterValues / StatusNotification data that a real
 * charger would send. For this simplified REST integration, we accept
 * the essential fields needed for ETA prediction.
 *
 * Example JSON:
 * {
 *   "stationId": "CP-001",
 *   "connectorId": 1,
 *   "currentSoc": 45.0,
 *   "chargerMaxKw": 150.0,
 *   "batteryCapacityKwh": 75.0,
 *   "ambientTempC": 22.0,
 *   "vehicleId": "VH-ABC-123",
 *   "timestamp": "2026-04-16T15:00:00Z"
 * }
 */
public class HeartbeatRequest {

    @NotBlank(message = "stationId is required")
    private String stationId;

    @NotNull(message = "connectorId is required")
    @Min(value = 1, message = "connectorId must be >= 1")
    private Integer connectorId;

    @NotNull(message = "currentSoc is required")
    @DecimalMin(value = "0.0", message = "currentSoc must be >= 0")
    @DecimalMax(value = "100.0", message = "currentSoc must be <= 100")
    private Double currentSoc;

    @NotNull(message = "chargerMaxKw is required")
    @DecimalMin(value = "1.0", message = "chargerMaxKw must be >= 1.0")
    @DecimalMax(value = "400.0", message = "chargerMaxKw must be <= 400")
    private Double chargerMaxKw;

    @NotNull(message = "batteryCapacityKwh is required")
    @DecimalMin(value = "10.0", message = "batteryCapacityKwh must be >= 10")
    @DecimalMax(value = "200.0", message = "batteryCapacityKwh must be <= 200")
    private Double batteryCapacityKwh;

    @NotNull(message = "ambientTempC is required")
    @DecimalMin(value = "-30.0", message = "ambientTempC must be >= -30")
    @DecimalMax(value = "55.0", message = "ambientTempC must be <= 55")
    private Double ambientTempC;

    /** Optional vehicle identifier for session tracking. */
    private String vehicleId;

    /** Timestamp from the charger. Defaults to server time if null. */
    private Instant timestamp;

    public HeartbeatRequest() {}

    public HeartbeatRequest(String stationId, Integer connectorId, Double currentSoc, Double chargerMaxKw, Double batteryCapacityKwh, Double ambientTempC, String vehicleId, Instant timestamp) {
        this.stationId = stationId;
        this.connectorId = connectorId;
        this.currentSoc = currentSoc;
        this.chargerMaxKw = chargerMaxKw;
        this.batteryCapacityKwh = batteryCapacityKwh;
        this.ambientTempC = ambientTempC;
        this.vehicleId = vehicleId;
        this.timestamp = timestamp;
    }

    // Getters and Setters
    public String getStationId() { return stationId; }
    public void setStationId(String stationId) { this.stationId = stationId; }

    public Integer getConnectorId() { return connectorId; }
    public void setConnectorId(Integer connectorId) { this.connectorId = connectorId; }

    public Double getCurrentSoc() { return currentSoc; }
    public void setCurrentSoc(Double currentSoc) { this.currentSoc = currentSoc; }

    public Double getChargerMaxKw() { return chargerMaxKw; }
    public void setChargerMaxKw(Double chargerMaxKw) { this.chargerMaxKw = chargerMaxKw; }

    public Double getBatteryCapacityKwh() { return batteryCapacityKwh; }
    public void setBatteryCapacityKwh(Double batteryCapacityKwh) { this.batteryCapacityKwh = batteryCapacityKwh; }

    public Double getAmbientTempC() { return ambientTempC; }
    public void setAmbientTempC(Double ambientTempC) { this.ambientTempC = ambientTempC; }

    public String getVehicleId() { return vehicleId; }
    public void setVehicleId(String vehicleId) { this.vehicleId = vehicleId; }

    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }

    // Builder pattern (simplified) replacement if needed, but constructors are usually enough.
}
