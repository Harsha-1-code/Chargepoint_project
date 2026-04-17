package com.antigravity.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * WebController — Root endpoint for the Spring Boot service.
 */
@RestController
public class WebController {

    @GetMapping("/")
    public Map<String, Object> index() {
        return Map.of(
            "message", "Antigravity Charging Service is UP",
            "documentation", "https://github.com/your-repo-link",
            "endpoints", Map.of(
                "status", "/api/telemetry/status",
                "heartbeat", "/api/telemetry/heartbeat (POST)"
            ),
            "timestamp", Instant.now().toString()
        );
    }
}
