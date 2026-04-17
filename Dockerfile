# --- Build Stage (Java) ---
FROM maven:3.9.6-eclipse-temurin-21-jammy AS java-build
WORKDIR /app
COPY spring-boot-service/pom.xml .
COPY spring-boot-service/src ./src
RUN mvn clean package -DskipTests

# --- Final Stage (Python + Java Runtime) ---
FROM python:3.11-slim-jammy

# Install OpenJDK 21 Runtime (headless for smaller image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Setup Python ML Service
COPY ml_model/requirements.txt ./ml_model/
RUN pip install --no-cache-dir -r ./ml_model/requirements.txt
RUN pip install --no-cache-dir gunicorn
COPY ml_model/ ./ml_model/

# 2. Setup Spring Boot Service
COPY --from=java-build /app/target/*.jar ./spring-boot-app.jar

# 3. Setup Orchestration
COPY start.sh .
RUN chmod +x start.sh

# Expose only the Spring Boot port (Gateway)
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV ML_SERVICE_URL=http://localhost:5000

# Entrypoint
CMD ["./start.sh"]
