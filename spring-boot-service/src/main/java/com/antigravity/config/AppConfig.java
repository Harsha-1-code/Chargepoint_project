package com.antigravity.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

// import java.time.Duration;

/**
 * AppConfig — Application-wide Spring configuration.
 *
 * Configures shared beans like RestTemplate with proper timeouts
 * for calling external services (Python ML API).
 */
@Configuration
public class AppConfig {

    @Value("${ml-service.timeout-ms:2000}")
    private int timeoutMs;

    /**
     * RestTemplate bean with connect and read timeouts.
     * Used by PredictionService to call the Flask ML API.
     */
    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        // Using the setConnectTimeout(Duration) signature as required by the classpath version
        return builder
                .setConnectTimeout(java.time.Duration.ofMillis(timeoutMs))
                .setReadTimeout(java.time.Duration.ofMillis(timeoutMs * 2L))
                .build();
    }
}
