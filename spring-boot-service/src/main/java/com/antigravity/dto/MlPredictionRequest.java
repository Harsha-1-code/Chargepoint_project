package com.antigravity.dto;

/**
 * MlPredictionRequest — Payload sent to the Python ML service.
 *
 * Maps directly to the Flask /predict endpoint's expected JSON body.
 * Field names use snake_case to match the Python API contract.
 */
public class MlPredictionRequest {

    private Double current_soc;
    private Double charger_max_kw;
    private Double battery_capacity_kwh;
    private Double ambient_temp_c;

    public MlPredictionRequest() {}

    public MlPredictionRequest(Double current_soc, Double charger_max_kw, Double battery_capacity_kwh, Double ambient_temp_c) {
        this.current_soc = current_soc;
        this.charger_max_kw = charger_max_kw;
        this.battery_capacity_kwh = battery_capacity_kwh;
        this.ambient_temp_c = ambient_temp_c;
    }

    /**
     * Factory method to create from a HeartbeatRequest.
     */
    public static MlPredictionRequest fromHeartbeat(HeartbeatRequest heartbeat) {
        return new MlPredictionRequest(
                heartbeat.getCurrentSoc(),
                heartbeat.getChargerMaxKw(),
                heartbeat.getBatteryCapacityKwh(),
                heartbeat.getAmbientTempC()
        );
    }

    // Getters and Setters
    public Double getCurrent_soc() { return current_soc; }
    public void setCurrent_soc(Double current_soc) { this.current_soc = current_soc; }

    public Double getCharger_max_kw() { return charger_max_kw; }
    public void setCharger_max_kw(Double charger_max_kw) { this.charger_max_kw = charger_max_kw; }

    public Double getBattery_capacity_kwh() { return battery_capacity_kwh; }
    public void setBattery_capacity_kwh(Double battery_capacity_kwh) { this.battery_capacity_kwh = battery_capacity_kwh; }

    public Double getAmbient_temp_c() { return ambient_temp_c; }
    public void setAmbient_temp_c(Double ambient_temp_c) { this.ambient_temp_c = ambient_temp_c; }
}
