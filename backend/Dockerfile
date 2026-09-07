# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Generate JWT_SECRET at build time if not provided via build arg
# This ensures the container never starts without a valid encryption key
ARG JWT_SECRET=""
RUN if [ -z "$JWT_SECRET" ]; then \
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))") \
    fi && \
    printf "DATABASE_URL=sqlite:///./data/teleplay.db\nJWT_SECRET=%s\nTELEGRAM_API_ID=0\nTELEGRAM_API_HASH=\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_STORAGE_CHANNEL_ID=0\n" "$JWT_SECRET" > .env && \
    mkdir -p /app/session /app/data && chmod 777 /app/session /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]