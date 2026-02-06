# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + config
COPY src/ ./src/
COPY config/ ./config/

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app

# Use a fixed UID/GID to match the host (and Compose) and avoid bind-mount permission issues
ARG UID=1000
ARG GID=1000

# Create non-root user/group with predictable IDs
RUN addgroup --gid ${GID} appgroup \
 && adduser  --uid ${UID} --gid ${GID} --disabled-password --gecos "" appuser

# Copy app + dependencies from builder
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/config/ ./config/
# Re-install dependencies in the runtime stage to avoid copying potentially large /usr/local/lib/pythonX.Y/site-packages
COPY --from=builder /app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Ensure /app is owned by the runtime user
RUN chown -R ${UID}:${GID} /app

ENV PYTHONPATH=/app

# Drop privileges
USER ${UID}:${GID}

# Default execution
ENTRYPOINT ["python", "-m", "src.cli"]
