package com.antigravity.service;

import com.antigravity.repository.ChargingSessionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * BufferService — Adjusts raw ML predictions using historical idle-time data.
 *
 * The "buffer factor" accounts for the real-world behavior where drivers
 * leave their vehicle plugged in after it reaches 100% SoC. This idle time
 * is unpredictable by the ML model (which predicts charging time), so we
 * apply a multiplicative adjustment based on historical patterns.
 *
 * Algorithm:
 * ─────────
 *   bufferFactor = 1.0 + (avgIdleMinutes / avgChargingMinutes)
 *   adjustedEta  = rawEta × bufferFactor
 *
 *   Clamped to: bufferFactor ∈ [1.0, maxFactor]
 *
 * Example:
 *   If drivers at station CP-001 historically charge for 40 min
 *   and idle for 12 min afterwards:
 *     bufferFactor = 1.0 + (12 / 40) = 1.30
 *     rawEta = 35 min → adjustedEta = 35 × 1.30 = 45.5 min
 *
 * When insufficient history exists (< 5 sessions), the default factor
 * is used (configurable, default 1.15 = 15% buffer).
 */
@Service
public class BufferService {

    private static final Logger log = LoggerFactory.getLogger(BufferService.class);

    private final ChargingSessionRepository sessionRepository;
    private final double defaultFactor;
    private final double maxFactor;

    /** Minimum number of historical sessions to trust computed buffer. */
    private static final int MIN_SESSIONS_FOR_COMPUTED_BUFFER = 5;

    public BufferService(
            ChargingSessionRepository sessionRepository,
            @Value("${buffer.default-factor:1.15}") double defaultFactor,
            @Value("${buffer.max-factor:2.0}") double maxFactor) {
        this.sessionRepository = sessionRepository;
        this.defaultFactor = defaultFactor;
        this.maxFactor = maxFactor;
    }

    /**
     * Compute the buffer factor for a given station.
     *
     * @param stationId The charging station identifier
     * @return Buffer factor in range [1.0, maxFactor]
     */
    public double computeBufferFactor(String stationId) {
        long sessionCount = sessionRepository.countByStationId(stationId);

        if (sessionCount < MIN_SESSIONS_FOR_COMPUTED_BUFFER) {
            log.info("Station {} has {} sessions (< {}), using default buffer: {}",
                    stationId, sessionCount, MIN_SESSIONS_FOR_COMPUTED_BUFFER, defaultFactor);
            return defaultFactor;
        }

        Double avgIdle = sessionRepository.findAverageIdleDurationByStationId(stationId);
        Double avgCharging = sessionRepository.findAverageChargingDurationByStationId(stationId);

        if (avgIdle == null || avgCharging == null || avgCharging <= 0) {
            log.warn("Station {} has invalid averages (idle={}, charging={}), using default",
                    stationId, avgIdle, avgCharging);
            return defaultFactor;
        }

        double computedFactor = 1.0 + (avgIdle / avgCharging);

        // Clamp to valid range
        double clampedFactor = Math.max(1.0, Math.min(maxFactor, computedFactor));

        log.info("Station {} buffer factor: {:.3f} (avgIdle={:.1f}min, avgCharging={:.1f}min, " +
                        "sessions={})",
                stationId, clampedFactor, avgIdle, avgCharging, sessionCount);

        return clampedFactor;
    }

    /**
     * Apply the buffer factor to a raw ETA prediction.
     *
     * @param rawEtaMinutes The raw ML prediction in minutes
     * @param stationId     The station to look up history for
     * @return BufferResult with adjusted ETA and the factor used
     */
    public BufferResult applyBuffer(double rawEtaMinutes, String stationId) {
        double factor = computeBufferFactor(stationId);
        double adjustedEta = rawEtaMinutes * factor;

        return new BufferResult(
                Math.round(adjustedEta * 10.0) / 10.0,  // Round to 1 decimal
                Math.round(factor * 1000.0) / 1000.0     // Round to 3 decimals
        );
    }

    /**
     * Result record containing the adjusted ETA and the buffer factor used.
     */
    public record BufferResult(double adjustedEtaMinutes, double bufferFactor) {}

    /**
     * Get the default buffer factor (for transparency in responses).
     */
    public double getDefaultFactor() {
        return defaultFactor;
    }

    /**
     * Get the maximum allowed buffer factor.
     */
    public double getMaxFactor() {
        return maxFactor;
    }
}
