# start.sh — Orchestrator for Antigravity Unified Demo
echo "🚀 Starting Project Antigravity Unified Stack (Hugging Face Mode)..."

# 1. Start Python ML API (Background)
echo "Starting Python ML API on localhost:5000..."
cd /app/ml_model
gunicorn --bind 0.0.0.0:5000 --timeout 120 serve:app &

# 2. Wait a few seconds for the model to load
sleep 5

# 3. Start Spring Boot Service (Foreground)
echo "Starting Spring Boot Service on port ${PORT:-7860}..."
cd /app
exec java -Xmx512m -Dserver.port=${PORT:-7860} -jar spring-boot-app.jar
