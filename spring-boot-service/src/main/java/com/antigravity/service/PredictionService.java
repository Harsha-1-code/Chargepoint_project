package com.antigravity.service;

import com.antigravity.dto.HeartbeatRequest;
import com.antigravity.dto.MlPredictionRequest;
import com.antigravity.dto.MlPredictionResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * PredictionService — Calls the Python ML model via REST API.
 *
 * Responsibilities:
 *   1. Build the request payload from heartbeat data
 *   2. Call the Flask /predict endpoint
 *   3. Handle timeouts and failures with a linear fallback estimator
 *
 * The fallback ensures the system remains functional even when
 * the ML service is temporarily unavailable.
 */
@Service
public class PredictionService {

    private static final Logger log = LoggerFactory.getLogger(PredictionService.class);

    private final RestTemplate restTemplate;
    private final String mlServiceUrl;

    /** Track consecutive failures for circuit-breaker logic. */
    private int consecutiveFailures = 0;
    private static final int CIRCUIT_BREAKER_THRESHOLD = 5;
    private long circuitOpenUntil = 0;

    public PredictionService(
            RestTemplate restTemplate,
            @Value("${ml-service.url:http://localhost:5000}") String mlServiceUrl) {
        this.restTemplate = restTemplate;
        this.mlServiceUrl = mlServiceUrl;
    }

    /**
     * Get an ETA prediction for the given heartbeat data.
     *
     * @param request The incoming heartbeat telemetry
     * @return ML prediction response, or fallback estimate if ML service is down
     */
    public MlPredictionResponse predict(HeartbeatRequest request) {
        // Circuit breaker: skip ML call if too many recent failures
        if (isCircuitOpen()) {
            log.warn("Circuit breaker OPEN — using fallback estimator for station {}",
                    request.getStationId());
            return fallbackEstimate(request);
        }

        try {
            MlPredictionResponse response = callMlService(request);
            consecutiveFailures = 0; // Reset on success
            return response;
        } catch (RestClientException e) {
            consecutiveFailures++;
            log.error("ML service call failed (attempt {}/{}): {}",
                    consecutiveFailures, CIRCUIT_BREAKER_THRESHOLD, e.getMessage());

            if (consecutiveFailures >= CIRCUIT_BREAKER_THRESHOLD) {
                // Open circuit for 30 seconds
                circuitOpenUntil = System.currentTimeMillis() + Duration.ofSeconds(30).toMillis();
                log.warn("Circuit breaker OPENED — will retry after 30s");
            }

            return fallbackEstimate(request);
        }
    }

    /**
     * Call the Python Flask ML service.
     */
    private MlPredictionResponse callMlService(HeartbeatRequest request) {
        String url = mlServiceUrl + "/predict";

        MlPredictionRequest mlRequest = MlPredictionRequest.fromHeartbeat(request);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<MlPredictionRequest> entity = new HttpEntity<>(mlRequest, headers);

        log.info("Calling ML service: {} with SoC={}%, charger={}kW",
                url, request.getCurrentSoc(), request.getChargerMaxKw());

        ResponseEntity<MlPredictionResponse> responseEntity =
                restTemplate.postForEntity(url, entity, MlPredictionResponse.class);

        MlPredictionResponse response = responseEntity.getBody();
        if (response == null || response.getPredicted_eta_minutes() == null) {
            throw new RestClientException("ML service returned null prediction");
        }

        log.info("ML prediction: {} minutes (confidence: {})",
                response.getPredicted_eta_minutes(), response.getConfidence());

        return response;
    }

    /**
     * Fallback linear estimator when the ML service is unavailable.
     *
     * Uses simplified physics:
     *   - CC phase (≤80%): linear based on energy remaining / power
     *   - CV phase (>80%): adds exponential penalty
     *   - Temperature derating: 1.2% per °C outside 20-35°C
     *
     * This is intentionally conservative (overestimates) to avoid
     * giving users an ETA that's too short.
     */
    private MlPredictionResponse fallbackEstimate(HeartbeatRequest request) {
        double soc = request.getCurrentSoc();
        double chargerKw = request.getChargerMaxKw();
        double batteryKwh = request.getBatteryCapacityKwh();
        double tempC = request.getAmbientTempC();

        // Temperature derating
        double tempFactor = 1.0;
        if (tempC < 20) tempFactor = Math.max(0.5, 1.0 - 0.012 * (20 - tempC));
        if (tempC > 35) tempFactor = Math.max(0.6, 1.0 - 0.012 * (tempC - 35));

        // Effective charging power (with efficiency losses)
        double effectivePower = chargerKw * 0.92 * tempFactor;

        // Energy remaining to 100%
        double energyRemaining = (1.0 - soc / 100.0) * batteryKwh;

        // CC phase: energy up to 80%
        double ccEnergy = Math.max(0, (0.80 - soc / 100.0) * batteryKwh);
        double ccTimeHours = ccEnergy / effectivePower;

        // CV phase: 80% to 100% takes roughly 2x longer per kWh due to taper
        double cvEnergy = energyRemaining - ccEnergy;
        double cvTimeHours = (cvEnergy > 0) ? (cvEnergy / effectivePower) * 2.5 : 0;

        double totalMinutes = (ccTimeHours + cvTimeHours) * 60.0;
        totalMinutes = Math.max(1.0, totalMinutes); // At least 1 minute

        MlPredictionResponse response = new MlPredictionResponse();
        response.setPredicted_eta_minutes(Math.round(totalMinutes * 10.0) / 10.0);
        response.setConfidence("low"); // Fallback is always low confidence

        log.info("Fallback prediction: {} minutes", response.getPredicted_eta_minutes());
        return response;
    }

    private boolean isCircuitOpen() {
        if (consecutiveFailures < CIRCUIT_BREAKER_THRESHOLD) return false;
        if (System.currentTimeMillis() > circuitOpenUntil) {
            // Half-open: allow one retry
            consecutiveFailures = CIRCUIT_BREAKER_THRESHOLD - 1;
            return false;
        }
        return true;
    }
}
