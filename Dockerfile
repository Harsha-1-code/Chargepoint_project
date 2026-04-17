# --- Build Stage (Java) ---
FROM maven:3.9.6-eclipse-temurin-21-jammy AS java-build
WORKDIR /app
COPY spring-boot-service/pom.xml .
COPY spring-boot-service/src ./src
RUN mvn clean package -DskipTests

# --- Final Stage (Python + Java Runtime) ---
FROM python:3.11-slim-jammy

# 1. Install System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up User (Hugging Face Requirement: UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ML_SERVICE_URL=http://localhost:5000

WORKDIR $HOME/app

# 3. Setup Python ML Service
COPY --chown=user:user ml_model/requirements.txt ./ml_model/
RUN pip install --no-cache-dir --user -r ./ml_model/requirements.txt
RUN pip install --no-cache-dir --user gunicorn
COPY --chown=user:user ml_model/ ./ml_model/

# 4. Setup Spring Boot Service
COPY --chown=user:user --from=java-build /app/target/*.jar ./spring-boot-app.jar

# 5. Setup Orchestration
COPY --chown=user:user start.sh .
RUN chmod +x start.sh

# Hugging Face default port
EXPOSE 7860

# Entrypoint
CMD ["./start.sh"]
