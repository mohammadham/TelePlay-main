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

# Copy backend code
COPY backend/app/ ./app/

# Copy built frontend assets from Stage 1 to Backend's static folder
# FastAPI is configured to look in 'app/static' to serve the SPA
COPY --from=frontend-builder /web-build/dist ./app/static

# Create session directory
RUN mkdir -p /app/session && chmod 777 /app/session

# Set environment variable to tell FastAPI we are in production/monolith mode if needed
ENV MULTI_CONTAINER_SETUP=false

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
