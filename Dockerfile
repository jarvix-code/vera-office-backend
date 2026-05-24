FROM python:3.11-slim

WORKDIR /app

# System dependencies für PaddleOCR
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Backend kopieren
COPY backend /app/backend

# Frontend kopieren
COPY frontend/dist /app/frontend/dist

# SSL Keys (optional)
COPY keys /app/keys

# Config, Models, Data (werden als Volumes gemountet)
RUN mkdir -p /app/data /app/logs /app/config /app/models /app/paddleocr-models

# Port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Command
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
