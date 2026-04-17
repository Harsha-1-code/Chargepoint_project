package com.antigravity.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.Instant;

/**
 * PredictionResponse — ETA prediction result returned to the caller.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PredictionResponse {

    private String stationId;
    private Integer connectorId;
    private Double rawEtaMinutes;
    private Double bufferFactor;
    private Double adjustedEtaMinutes;
    private Instant predictedDisconnectTime;
    private String confidence;
    private Double currentSoc;
    private String status;
    private String message;
    private Instant timestamp;

    public PredictionResponse() {}

    public PredictionResponse(String stationId, Integer connectorId, Double rawEtaMinutes, Double bufferFactor, Double adjustedEtaMinutes, Instant predictedDisconnectTime, String confidence, Double currentSoc, String status, String message, Instant timestamp) {
        this.stationId = stationId;
        this.connectorId = connectorId;
        this.rawEtaMinutes = rawEtaMinutes;
        this.bufferFactor = bufferFactor;
        this.adjustedEtaMinutes = adjustedEtaMinutes;
        this.predictedDisconnectTime = predictedDisconnectTime;
        this.confidence = confidence;
        this.currentSoc = currentSoc;
        this.status = status;
        this.message = message;
        this.timestamp = timestamp;
    }

    // Getters and Setters
    public String getStationId() { return stationId; }
    public void setStationId(String stationId) { this.stationId = stationId; }

    public Integer getConnectorId() { return connectorId; }
    public void setConnectorId(Integer connectorId) { this.connectorId = connectorId; }

    public Double getRawEtaMinutes() { return rawEtaMinutes; }
    public void setRawEtaMinutes(Double rawEtaMinutes) { this.rawEtaMinutes = rawEtaMinutes; }

    public Double getBufferFactor() { return bufferFactor; }
    public void setBufferFactor(Double bufferFactor) { this.bufferFactor = bufferFactor; }

    public Double getAdjustedEtaMinutes() { return adjustedEtaMinutes; }
    public void setAdjustedEtaMinutes(Double adjustedEtaMinutes) { this.adjustedEtaMinutes = adjustedEtaMinutes; }

    public Instant getPredictedDisconnectTime() { return predictedDisconnectTime; }
    public void setPredictedDisconnectTime(Instant predictedDisconnectTime) { this.predictedDisconnectTime = predictedDisconnectTime; }

    public String getConfidence() { return confidence; }
    public void setConfidence(String confidence) { this.confidence = confidence; }

    public Double getCurrentSoc() { return currentSoc; }
    public void setCurrentSoc(Double currentSoc) { this.currentSoc = currentSoc; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }

    // Simplified Builder
    public static PredictionResponseBuilder builder() {
        return new PredictionResponseBuilder();
    }

    public static class PredictionResponseBuilder {
        private String stationId;
        private Integer connectorId;
        private Double rawEtaMinutes;
        private Double bufferFactor;
        private Double adjustedEtaMinutes;
        private Instant predictedDisconnectTime;
        private String confidence;
        private Double currentSoc;
        private String status;
        private String message;
        private Instant timestamp;

        public PredictionResponseBuilder stationId(String stationId) { this.stationId = stationId; return this; }
        public PredictionResponseBuilder connectorId(Integer connectorId) { this.connectorId = connectorId; return this; }
        public PredictionResponseBuilder rawEtaMinutes(Double rawEtaMinutes) { this.rawEtaMinutes = rawEtaMinutes; return this; }
        public PredictionResponseBuilder bufferFactor(Double bufferFactor) { this.bufferFactor = bufferFactor; return this; }
        public PredictionResponseBuilder adjustedEtaMinutes(Double adjustedEtaMinutes) { this.adjustedEtaMinutes = adjustedEtaMinutes; return this; }
        public PredictionResponseBuilder predictedDisconnectTime(Instant predictedDisconnectTime) { this.predictedDisconnectTime = predictedDisconnectTime; return this; }
        public PredictionResponseBuilder confidence(String confidence) { this.confidence = confidence; return this; }
        public PredictionResponseBuilder currentSoc(Double currentSoc) { this.currentSoc = currentSoc; return this; }
        public PredictionResponseBuilder status(String status) { this.status = status; return this; }
        public PredictionResponseBuilder message(String message) { this.message = message; return this; }
        public PredictionResponseBuilder timestamp(Instant timestamp) { this.timestamp = timestamp; return this; }

        public PredictionResponse build() {
            return new PredictionResponse(stationId, connectorId, rawEtaMinutes, bufferFactor, adjustedEtaMinutes, predictedDisconnectTime, confidence, currentSoc, status, message, timestamp);
        }
    }
}
