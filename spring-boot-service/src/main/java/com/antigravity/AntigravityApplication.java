package com.antigravity;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Project Antigravity — EV Charging Occupancy & ETA Prediction Engine
 *
 * Main Spring Boot application entry point.
 * Starts the embedded Tomcat server and initializes all components:
 *   - HeartbeatController: ingests charger telemetry
 *   - PredictionService:   calls the Python ML model API
 *   - BufferService:       adjusts ETA with historical idle-time data
 */
@SpringBootApplication
public class AntigravityApplication {

    public static void main(String[] args) {
        SpringApplication.run(AntigravityApplication.class, args);
    }
}
