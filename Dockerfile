# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Skip gcc for now - aiohttp will use pure Python fallback
# This avoids package hash mismatch issues

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot_container.py .
COPY personalities/ ./personalities/

# Create utils directory (will be populated later)
RUN mkdir -p utils

# Create non-root user for security
RUN useradd -m -u 1000 discordbot && chown -R discordbot:discordbot /app
USER discordbot

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check - checks if bot is connected
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the bot
CMD ["python", "bot_container.py"]