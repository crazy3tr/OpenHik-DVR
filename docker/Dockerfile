FROM python:3.11-slim

# Install ffmpeg for lossless MP4 remuxing and tzdata for accurate scheduling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy OpenHik-DVR codebase
COPY python/ /app/python/
COPY tools/ /app/tools/
COPY examples/ /app/examples/

# Environment variables with sensible defaults
ENV DVR_HOST="192.168.1.100"
ENV DVR_PORT="80"
ENV DVR_USER="admin"
ENV DVR_PASS="password123"
ENV WEB_PORT="8080"
ENV BACKUP_CHANNEL="1"
ENV BACKUP_DAYS="1"
ENV OUTPUT_DIR="/recordings"

# Web Dashboard Port
EXPOSE 8080

# Default command: launch the ActiveX-free modern Web Dashboard using ENV parameters
CMD ["sh", "-c", "python tools/web_dashboard.py --host \"$DVR_HOST\" --port \"$DVR_PORT\" --user \"$DVR_USER\" --pass \"$DVR_PASS\" --bind 0.0.0.0 --web-port \"$WEB_PORT\""]
