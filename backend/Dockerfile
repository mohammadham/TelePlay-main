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

# Copy application code and create template .env so build never crashes (panel is source of truth)
COPY app/ ./app/
RUN printf "DATABASE_URL=sqlite:///./data/teleplay.db\nJWT_SECRET=change-me-via-panel\nTELEGRAM_API_ID=0\nTELEGRAM_API_HASH=\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_STORAGE_CHANNEL_ID=0\n" > .env
RUN mkdir -p /app/session /app/data && chmod 777 /app/session /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
