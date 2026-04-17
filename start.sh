#!/bin/bash

# start.sh — Orchestrator for Antigravity Unified Demo
echo "🚀 Starting Project Antigravity Unified Stack..."

# 1. Start Python ML API (Background)
echo "Starting Python ML API on localhost:5000..."
cd /app/ml_model
gunicorn --bind 0.0.0.0:5000 serve:app &

# 2. Wait a few seconds for the model to load
sleep 5

# 3. Start Spring Boot Service (Foreground)
echo "Starting Spring Boot Service on port 8080..."
cd /app
java -Xmx256m -jar spring-boot-app.jar
