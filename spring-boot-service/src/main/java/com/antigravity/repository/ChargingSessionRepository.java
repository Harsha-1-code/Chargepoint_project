package com.antigravity.repository;

import com.antigravity.model.ChargingSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * ChargingSessionRepository — Data access for charging session history.
 *
 * Provides queries needed by BufferService to compute the idle-time
 * buffer factor from historical data.
 */
@Repository
public interface ChargingSessionRepository extends JpaRepository<ChargingSession, Long> {

    /**
     * Find the most recent N sessions for a given station.
     * Used to compute a rolling buffer factor.
     */
    List<ChargingSession> findTop50ByStationIdOrderByTimestampDesc(String stationId);

    /**
     * Compute the average idle duration for a station.
     * Returns null if no sessions exist.
     */
    @Query("SELECT AVG(cs.idleDurationMinutes) FROM ChargingSession cs " +
           "WHERE cs.stationId = :stationId")
    Double findAverageIdleDurationByStationId(@Param("stationId") String stationId);

    /**
     * Compute the average charging duration for a station.
     * Returns null if no sessions exist.
     */
    @Query("SELECT AVG(cs.chargingDurationMinutes) FROM ChargingSession cs " +
           "WHERE cs.stationId = :stationId")
    Double findAverageChargingDurationByStationId(@Param("stationId") String stationId);

    /**
     * Count sessions for a station (used to determine data confidence).
     */
    long countByStationId(String stationId);

    /**
     * Find all sessions for a station (for analytics/debugging).
     */
    List<ChargingSession> findByStationIdOrderByTimestampDesc(String stationId);
}
