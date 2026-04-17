# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application code and model
COPY . .

# Create directory for models if not exists (though it should be copied)
RUN mkdir -p saved_models

# Expose the API port
EXPOSE 5000

# Start Flask with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "serve:app"]
