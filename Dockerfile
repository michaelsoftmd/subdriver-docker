FROM ghcr.io/stephanlensky/swayvnc-chrome:latest

ARG ENABLE_XWAYLAND
ARG SWAY_UNSUPPORTED_GPU

# Install xwayland if needed
RUN if [ "$ENABLE_XWAYLAND" = "true" ]; then \
    apt-get update && \
    apt-get -y install xwayland && \
    echo "Xwayland installed."; \
    fi

# Configure xwayland
RUN if [ "$ENABLE_XWAYLAND" = "true" ]; then \
    sed -i '/^export XDG_RUNTIME_DIR/i export DISPLAY=${DISPLAY:-:0}' /entrypoint_user.sh && \
    sed -i 's/xwayland disable/xwayland enable/' /home/$DOCKER_USER/.config/sway/config; \
    fi

# Add unsupported GPU flag if needed
RUN if [ "$SWAY_UNSUPPORTED_GPU" = "true" ]; then \
    sed -i 's/sway &/sway --unsupported-gpu \&/' /entrypoint_user.sh; \
    fi

ENV PYTHONUNBUFFERED=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Setup app directory
RUN mkdir /app && chown $DOCKER_USER:$DOCKER_USER /app

USER $DOCKER_USER
WORKDIR /app

# Install Python 3.13
RUN uv python install 3.13

# Copy and install dependencies
COPY --chown=$DOCKER_USER:$DOCKER_USER pyproject.toml uv.lock* ./

# Install dependencies only (not the project)
RUN uv sync --no-install-project || \
    uv venv && \
    uv pip install \
        zendriver \
        fastapi \
        uvicorn[standard] \
        pydantic \
        pydantic-settings \
        sqlalchemy \
        httpx \
        redis \
        prometheus-client \
        python-json-logger

# Copy application code
COPY --chown=$DOCKER_USER:$DOCKER_USER app /app/app

# Create data and profiles directories
RUN mkdir -p /app/data /app/profiles

# Set PATH
ENV PATH="/app/.venv/bin:$PATH"

USER root

ENTRYPOINT ["/entrypoint.sh"]
CMD [".venv/bin/python", "-m", "app.main"]
