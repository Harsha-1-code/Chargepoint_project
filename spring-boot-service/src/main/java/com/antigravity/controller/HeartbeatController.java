package com.antigravity.controller;

import com.antigravity.dto.HeartbeatRequest;
import com.antigravity.dto.MlPredictionResponse;
import com.antigravity.dto.PredictionResponse;
import com.antigravity.service.BufferService;
import com.antigravity.service.PredictionService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

/**
 * HeartbeatController — REST endpoint for charger telemetry ingestion.
 *
 * This controller serves as the entry point for simulated OCPP heartbeat
 * data from charging stations. In a production OCPP integration, this would
 * be replaced by a WebSocket handler processing MeterValues messages.
 *
 * Flow:
 *   1. Receive HeartbeatRequest with current SoC, charger specs, etc.
 *   2. Call PredictionService → Python ML model → raw ETA
 *   3. Call BufferService → apply historical idle-time adjustment
 *   4. Return PredictionResponse with both raw and adjusted ETAs
 *
 * Endpoints:
 *   POST /api/telemetry/heartbeat  — process a single heartbeat
 *   GET  /api/telemetry/status     — service status check
 */
@RestController
@RequestMapping("/api/telemetry")
@CrossOrigin(origins = "*") // Allow all origins for development
public class HeartbeatController {

    private static final Logger log = LoggerFactory.getLogger(HeartbeatController.class);

    private final PredictionService predictionService;
    private final BufferService bufferService;

    public HeartbeatController(PredictionService predictionService,
                                BufferService bufferService) {
        this.predictionService = predictionService;
        this.bufferService = bufferService;
    }

    /**
     * Process an incoming heartbeat from a charging station.
     *
     * Accepts real-time telemetry, runs an ML prediction for
     * time-to-disconnect, and adjusts it with a historical buffer factor.
     *
     * @param request Validated heartbeat telemetry data
     * @return PredictionResponse with raw ETA, buffer factor, and adjusted ETA
     */
    @PostMapping("/heartbeat")
    public ResponseEntity<PredictionResponse> handleHeartbeat(
            @Valid @RequestBody HeartbeatRequest request) {

        log.info("Heartbeat received: station={}, connector={}, SoC={}%, charger={}kW",
                request.getStationId(), request.getConnectorId(),
                request.getCurrentSoc(), request.getChargerMaxKw());

        // Default timestamp to now if not provided
        Instant requestTime = request.getTimestamp() != null
                ? request.getTimestamp()
                : Instant.now();

        // ── Step 1: Get ML prediction ──
        MlPredictionResponse mlResponse = predictionService.predict(request);
        double rawEta = mlResponse.getPredicted_eta_minutes();

        // ── Step 2: Apply buffer factor ──
        BufferService.BufferResult bufferResult =
                bufferService.applyBuffer(rawEta, request.getStationId());

        // ── Step 3: Compute predicted disconnect time ──
        Instant disconnectTime = requestTime.plusSeconds(
                (long) (bufferResult.adjustedEtaMinutes() * 60));

        // ── Step 4: Determine charging status ──
        String status = determineStatus(request.getCurrentSoc());

        // ── Step 5: Build response ──
        PredictionResponse response = PredictionResponse.builder()
                .stationId(request.getStationId())
                .connectorId(request.getConnectorId())
                .rawEtaMinutes(rawEta)
                .bufferFactor(bufferResult.bufferFactor())
                .adjustedEtaMinutes(bufferResult.adjustedEtaMinutes())
                .predictedDisconnectTime(disconnectTime)
                .confidence(mlResponse.getConfidence())
                .currentSoc(request.getCurrentSoc())
                .status(status)
                .timestamp(Instant.now())
                .build();

        log.info("Prediction for station {}: raw={}min, buffer={}x, adjusted={}min, " +
                        "disconnect={}, status={}",
                request.getStationId(), rawEta, bufferResult.bufferFactor(),
                bufferResult.adjustedEtaMinutes(), disconnectTime, status);

        return ResponseEntity.ok(response);
    }

    /**
     * Service status endpoint.
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getStatus() {
        return ResponseEntity.ok(Map.of(
                "service", "Antigravity Charging ETA Service",
                "status", "UP",
                "version", "1.0.0",
                "timestamp", Instant.now().toString(),
                "bufferConfig", Map.of(
                        "defaultFactor", bufferService.getDefaultFactor(),
                        "maxFactor", bufferService.getMaxFactor()
                )
        ));
    }

    /**
     * Determine the charging status based on current SoC.
     */
    private String determineStatus(double currentSoc) {
        if (currentSoc >= 100.0) return "IDLE";
        if (currentSoc >= 95.0)  return "NEAR_FULL";
        if (currentSoc >= 80.0)  return "TAPERING";
        return "CHARGING";
    }
}
