# =====================================================
# Prompt-to-Animate Dockerfile
# Multi-purpose image for Azure Container Apps
# Supports both API (uvicorn) and Worker (rq) modes
# =====================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies for Manim
# Note: texlive-full is large (~4GB). For lighter builds, use texlive-base + specific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for video encoding
    ffmpeg \
    # Cairo for vector graphics
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    # GObject Introspection for Pango text rendering
    libgirepository1.0-dev \
    gir1.2-pango-1.0 \
    gobject-introspection \
    # Python bindings for Cairo and GObject (system packages - avoids build issues)
    python3-gi \
    python3-gi-cairo \
    python3-cairo \
    # LaTeX for mathematical text (lighter alternative to texlive-full)
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    texlive-extra-utils \
    dvipng \
    dvisvgm \
    # Build tools
    build-essential \
    git \
    meson \
    ninja-build \
    # Network utilities (for healthcheck)
    curl \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p generated_animations backend/temp

# Expose port for API
EXPOSE 8000

# Default command (API mode)
# Override with: python -m backend.worker (for Worker mode)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =====================================================
# Usage Examples:
# 
# Build:
#   docker build -t prompt-to-animate .
#
# Run API:
#   docker run -p 8000:8000 --env-file .env prompt-to-animate
#
# Run Worker:
#   docker run --env-file .env prompt-to-animate python -m backend.worker
#
# For Azure Container Apps:
#   Deploy two container instances from the same image:
#   1. API: command = uvicorn backend.main:app --host 0.0.0.0 --port 8000
#   2. Worker: command = python -m backend.worker
# =====================================================
