FROM python:3.12-slim

WORKDIR /app

# Install system deps for bcrypt, curl_cffi, and git (for pip git deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev supervisor git nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the project
RUN pip install --no-cache-dir .

# Copy process manager config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

# Create data directory for SQLite + Garmin tokens
# On Azure App Service, /home is the only persistent volume
RUN mkdir -p /home/data /home/data/garmin-tokens

ENV PACEFORGE_DB_PATH=/home/data/paceforge.db
ENV PACEFORGE_GARMIN_TOKEN_DIR=/home/data/garmin-tokens

EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
