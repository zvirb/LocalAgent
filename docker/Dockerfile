# LocalAgent - Multi-Provider LLM CLI Container
# Production-ready Docker image with security and optimization
FROM python:3.11-slim-bookworm

# Metadata
LABEL maintainer="LocalAgent Development Team"
LABEL version="1.0.0"
LABEL description="Multi-provider LLM orchestration CLI with UnifiedWorkflow integration"

# Security and environment setup
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:/app/UnifiedWorkflow"
ENV LOCALAGENT_CONFIG_DIR="/app/config"
ENV LOCALAGENT_CACHE_DIR="/app/.cache"

# Install system dependencies with minimal attack surface
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create dedicated user for security
RUN groupadd --system --gid 1000 localagent \
    && useradd --system --uid 1000 --gid 1000 --home /app --shell /bin/bash localagent

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY requirements.txt ./
COPY UnifiedWorkflow/requirements-core.txt ./requirements-core.txt
COPY UnifiedWorkflow/requirements-web.txt ./requirements-web.txt

# Install Python dependencies with pinned versions
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        # Core LocalAgent dependencies
        click>=8.1.0 \
        rich>=13.0.0 \
        pyyaml>=6.0 \
        aiohttp>=3.9.0 \
        # Provider SDKs
        openai>=1.0.0 \
        google-generativeai>=0.3.0 \
        anthropic>=0.3.0 \
        # Security
        cryptography>=41.0.0 \
        keyring>=24.0.0 \
        # AsyncIO and networking
        asyncio \
        httpx>=0.27.0 \
        # Configuration and environment
        python-dotenv>=1.0.0 \
        pydantic>=2.0.0 \
        # Development tools
        pytest>=7.0.0 \
        pytest-asyncio>=0.21.0 \
    && pip install --no-cache-dir -r requirements-core.txt \
    && pip install --no-cache-dir -r requirements-web.txt

# Copy application code
COPY --chown=localagent:localagent . .

# Create necessary directories
RUN mkdir -p /app/config /app/.cache /app/logs \
    && chown -R localagent:localagent /app

# Make CLI executable
RUN chmod +x /app/scripts/localagent

# Switch to non-root user
USER localagent

# Create symbolic link for global access
RUN ln -sf /app/scripts/localagent /app/localagent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/scripts/localagent providers --provider ollama || exit 1

# Default command - interactive mode
ENTRYPOINT ["/app/scripts/localagent"]
CMD []

# Expose ports for potential web interface
EXPOSE 8000 8080