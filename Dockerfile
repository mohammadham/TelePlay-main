# Dockerfile for PaaS Deployment (Render, Railway, Heroku)
# Builds both Frontend and Backend in a single image.

# ----------------------------
# Stage 1: Build Frontend
# ----------------------------
FROM node:20-alpine as frontend-builder
WORKDIR /web-build

# Copy frontend dependency files
COPY web/package*.json ./
RUN npm ci

# Copy frontend source code
COPY web/ ./
RUN npm run build


# ----------------------------
# Stage 2: Build Backend & Serve
# ----------------------------
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and env template (so build never needs real .env)
COPY backend/app/ ./app/
COPY .env.example ./.env.example
# Create template .env at build time if none exists — panel is source of truth, no crash
RUN if [ ! -f .env ]; then cp .env.example .env 2>/dev/null || printf "DATABASE_URL=sqlite:///./data/teleplay.db\nJWT_SECRET=change-me-in-production-please-set-via-panel\nTELEGRAM_API_ID=0\nTELEGRAM_API_HASH=\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_STORAGE_CHANNEL_ID=0\n" > .env; echo "Template .env created at build"; fi

# Copy built frontend assets from Stage 1 to Backend's static folder
# FastAPI is configured to look in 'app/static' to serve the SPA
COPY --from=frontend-builder /web-build/dist ./app/static

# Create session & data directories
RUN mkdir -p /app/session /app/data && chmod 777 /app/session /app/data

# Set environment variable to tell FastAPI we are in production/monolith mode if needed
ENV MULTI_CONTAINER_SETUP=false

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
