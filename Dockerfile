FROM python:3.10-slim

# Set work directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Create a non-root user and switch to it
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Copy source code
COPY . .

# Change ownership of the app directory
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose the port Cloud Run expects
EXPOSE 8080
# Set a valid cache directory for uv
ENV XDG_CACHE_HOME=/tmp/uv_cache

# Start the FastAPI app
CMD uv run uvicorn app.main:app --host 0.0.0.0 --port 8080