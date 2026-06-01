FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV M4STCLAW_HOST=0.0.0.0
ENV M4STCLAW_SANDBOX=/app/sandbox

WORKDIR /app

# Install system dependencies (git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration and install package dependencies
COPY pyproject.toml setup.py README.md /app/
RUN pip install --no-cache-dir -e .

# Copy application source code
COPY m4stclaw/ /app/m4stclaw/
COPY start.py /app/start.py

# Create sandbox and configuration directories
RUN mkdir -p /app/sandbox && mkdir -p /root/.config/m4stclaw

# Expose backend/dashboard port
EXPOSE 8000

# Start command
CMD ["python", "start.py"]
