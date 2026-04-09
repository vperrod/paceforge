FROM python:3.12-slim

WORKDIR /app

# Install system deps for bcrypt, curl_cffi, and git (for pip git deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev supervisor git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the project
RUN pip install --no-cache-dir .

# Copy process manager config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create data directory for SQLite + Garmin tokens
RUN mkdir -p /data /data/garmin-tokens

ENV PACEFORGE_DB_PATH=/data/paceforge.db
ENV PACEFORGE_GARMIN_TOKEN_DIR=/data/garmin-tokens

EXPOSE 8000 8501

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
