package com.antigravity.model;

import jakarta.persistence.*;

import java.time.Instant;

/**
 * ChargingSession — JPA entity tracking completed charging sessions.
 *
 * Used by BufferService to compute the historical idle-time buffer factor.
 * Each record represents one vehicle's full stay at a charger:
 *   plugIn → chargingComplete → disconnect
 *
 * The idle duration (chargingComplete → disconnect) is the key metric
 * for predicting how long drivers leave their car after it reaches 100%.
 */
@Entity
@Table(name = "charging_sessions", indexes = {
        @Index(name = "idx_station_id", columnList = "stationId"),
        @Index(name = "idx_timestamp", columnList = "timestamp")
})
public class ChargingSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Charging station identifier (e.g., "CP-001"). */
    @Column(nullable = false, length = 50)
    private String stationId;

    /** Connector number at the station. */
    @Column(nullable = false)
    private Integer connectorId;

    /** Optional vehicle identifier. */
    @Column(length = 50)
    private String vehicleId;

    /** SoC when the vehicle plugged in (%). */
    @Column(nullable = false)
    private Double startSoc;

    /** SoC when charging completed (%, typically 100). */
    @Column(nullable = false)
    private Double endSoc;

    /** Time spent actively charging (minutes). */
    @Column(nullable = false)
    private Double chargingDurationMinutes;

    /**
     * Time the vehicle sat idle after reaching target SoC (minutes).
     * This is the "buffer" that adjusts predicted ETAs.
     */
    @Column(nullable = false)
    private Double idleDurationMinutes;

    /** Total time at the charger: charging + idle (minutes). */
    @Column(nullable = false)
    private Double totalDurationMinutes;

    /** Charger's maximum output power (kW). */
    @Column(nullable = false)
    private Double chargerMaxKw;

    /** Vehicle's battery capacity (kWh). */
    @Column(nullable = false)
    private Double batteryCapacityKwh;

    /** Ambient temperature during the session (°C). */
    private Double ambientTempC;

    /** When the session was recorded. */
    @Column(nullable = false)
    private Instant timestamp;

    public ChargingSession() {}

    public ChargingSession(String stationId, Integer connectorId, String vehicleId, Double startSoc, Double endSoc, Double chargingDurationMinutes, Double idleDurationMinutes, Double chargerMaxKw, Double batteryCapacityKwh, Double ambientTempC, Instant timestamp) {
        this.stationId = stationId;
        this.connectorId = connectorId;
        this.vehicleId = vehicleId;
        this.startSoc = startSoc;
        this.endSoc = endSoc;
        this.chargingDurationMinutes = chargingDurationMinutes;
        this.idleDurationMinutes = idleDurationMinutes;
        this.chargerMaxKw = chargerMaxKw;
        this.batteryCapacityKwh = batteryCapacityKwh;
        this.ambientTempC = ambientTempC;
        this.timestamp = timestamp;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getStationId() { return stationId; }
    public void setStationId(String stationId) { this.stationId = stationId; }

    public Integer getConnectorId() { return connectorId; }
    public void setConnectorId(Integer connectorId) { this.connectorId = connectorId; }

    public String getVehicleId() { return vehicleId; }
    public void setVehicleId(String vehicleId) { this.vehicleId = vehicleId; }

    public Double getStartSoc() { return startSoc; }
    public void setStartSoc(Double startSoc) { this.startSoc = startSoc; }

    public Double getEndSoc() { return endSoc; }
    public void setEndSoc(Double endSoc) { this.endSoc = endSoc; }

    public Double getChargingDurationMinutes() { return chargingDurationMinutes; }
    public void setChargingDurationMinutes(Double chargingDurationMinutes) { this.chargingDurationMinutes = chargingDurationMinutes; }

    public Double getIdleDurationMinutes() { return idleDurationMinutes; }
    public void setIdleDurationMinutes(Double idleDurationMinutes) { this.idleDurationMinutes = idleDurationMinutes; }

    public Double getTotalDurationMinutes() { return totalDurationMinutes; }
    public void setTotalDurationMinutes(Double totalDurationMinutes) { this.totalDurationMinutes = totalDurationMinutes; }

    public Double getChargerMaxKw() { return chargerMaxKw; }
    public void setChargerMaxKw(Double chargerMaxKw) { this.chargerMaxKw = chargerMaxKw; }

    public Double getBatteryCapacityKwh() { return batteryCapacityKwh; }
    public void setBatteryCapacityKwh(Double batteryCapacityKwh) { this.batteryCapacityKwh = batteryCapacityKwh; }

    public Double getAmbientTempC() { return ambientTempC; }
    public void setAmbientTempC(Double ambientTempC) { this.ambientTempC = ambientTempC; }

    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }

    /**
     * Pre-persist hook: set timestamp if not already provided.
     */
    @PrePersist
    public void prePersist() {
        if (this.timestamp == null) {
            this.timestamp = Instant.now();
        }
        if (this.totalDurationMinutes == null && this.chargingDurationMinutes != null && this.idleDurationMinutes != null) {
            this.totalDurationMinutes = this.chargingDurationMinutes + this.idleDurationMinutes;
        }
    }
}
