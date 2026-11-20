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

# Install after copying the package source so the build can find its modules.
COPY pyproject.toml setup.py README.md /app/
COPY m4stclaw/ /app/m4stclaw/
COPY start.py /app/start.py
RUN pip install --no-cache-dir .

# Create sandbox and configuration directories
RUN mkdir -p /app/sandbox && mkdir -p /root/.config/m4stclaw

# Expose backend/dashboard port
EXPOSE 8000

# Start command
CMD ["python", "start.py"]
