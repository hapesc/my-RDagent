# syntax=docker/dockerfile:1

# ==========================================
# Build Stage
# ==========================================
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt* ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install all dependencies
RUN uv pip install --no-cache -e ".[all]"

# ==========================================
# Production Stage
# ==========================================
FROM python:3.11-slim as production

# Install Docker CLI for sandboxed execution
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/rd_agent_artifacts \
    /tmp/rd_agent_workspace \
    /tmp/rd_agent_trace \
    /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AGENTRD_ENV=production
ENV AGENTRD_ARTIFACT_ROOT=/tmp/rd_agent_artifacts
ENV AGENTRD_WORKSPACE_ROOT=/tmp/rd_agent_workspace
ENV AGENTRD_TRACE_STORAGE_PATH=/tmp/rd_agent_trace/events.jsonl
ENV AGENTRD_SQLITE_PATH=/tmp/rd_agent.sqlite3
ENV AGENTRD_ALLOW_LOCAL_EXECUTION=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.startup; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "app.startup"]

# ==========================================
# Development Stage
# ==========================================
FROM python:3.11-slim as development

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    vim \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml ./
COPY requirements.txt* ./

# Create virtual environment
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies in editable mode with all extras
RUN uv pip install --no-cache -e ".[all]"

# Copy application code (will be overwritten by volume mount in compose)
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/rd_agent_artifacts \
    /tmp/rd_agent_workspace \
    /tmp/rd_agent_trace \
    /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AGENTRD_ENV=development
ENV AGENTRD_ARTIFACT_ROOT=/tmp/rd_agent_artifacts
ENV AGENTRD_WORKSPACE_ROOT=/tmp/rd_agent_workspace
ENV AGENTRD_TRACE_STORAGE_PATH=/tmp/rd_agent_trace/events.jsonl
ENV AGENTRD_SQLITE_PATH=/tmp/rd_agent.sqlite3
ENV AGENTRD_ALLOW_LOCAL_EXECUTION=true

# Default command for development
CMD ["bash"]

# ==========================================
# API Server Stage
# ==========================================
FROM production as api

EXPOSE 8000

CMD ["uvicorn", "app.api_main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ==========================================
# UI Stage
# ==========================================
FROM production as ui

EXPOSE 8501

CMD ["streamlit", "run", "ui/trace_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
