package com.antigravity.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * MlPredictionResponse — Response from the Python ML service.
 *
 * Maps to the Flask /predict endpoint's JSON response.
 * Uses snake_case field names with Jackson deserialization.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MlPredictionResponse {

    private Double predicted_eta_minutes;
    private String confidence;

    public MlPredictionResponse() {}

    public MlPredictionResponse(Double predicted_eta_minutes, String confidence) {
        this.predicted_eta_minutes = predicted_eta_minutes;
        this.confidence = confidence;
    }

    public Double getPredicted_eta_minutes() { return predicted_eta_minutes; }
    public void setPredicted_eta_minutes(Double predicted_eta_minutes) { this.predicted_eta_minutes = predicted_eta_minutes; }

    public String getConfidence() { return confidence; }
    public void setConfidence(String confidence) { this.confidence = confidence; }
}
