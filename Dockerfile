FROM ghcr.io/stephanlensky/swayvnc-chrome:latest

ARG ENABLE_XWAYLAND

# install xwayland
RUN if [ "$ENABLE_XWAYLAND" = "true" ]; then \
    apt-get update && \
    apt-get -y install xwayland && \
    Xwayland -version && \
    echo "Xwayland installed."; \
    else \
    echo "Xwayland installation skipped."; \
    fi

# set DISPLAY for xwayland
RUN if [ "$ENABLE_XWAYLAND" = "true" ]; then \
    sed -i '/^export XDG_RUNTIME_DIR/i \
    export DISPLAY=${DISPLAY:-:0}' \
    /entrypoint_user.sh; \
    fi

# add `xwayland enable` to sway config
RUN if [ "$ENABLE_XWAYLAND" = "true" ]; then \
    sed -i 's/xwayland disable/xwayland enable/' \
    /home/$DOCKER_USER/.config/sway/config; \
    fi

ARG SWAY_UNSUPPORTED_GPU

# add `--unsupported-gpu` flag to sway command
RUN if [ "$SWAY_UNSUPPORTED_GPU" = "true" ]; then \
    sed -i 's/sway &/sway --unsupported-gpu \&/' /entrypoint_user.sh; \
    fi

ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Make directory for the app
RUN mkdir /app
RUN chown $DOCKER_USER:$DOCKER_USER /app

# Switch to the non-root user
USER $DOCKER_USER

# Set the working directory
WORKDIR /app

# Install python
RUN uv python install 3.13

# Copy dependency files
COPY --chown=$DOCKER_USER:$DOCKER_USER pyproject.toml /app/
COPY --chown=$DOCKER_USER:$DOCKER_USER uv.lock* /app/

# Install dependencies only (not the project itself)
RUN uv sync --no-install-project || \
    (uv venv && \
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
        python-json-logger)

# Copy the application code
COPY --chown=$DOCKER_USER:$DOCKER_USER app /app/app

# Create data directory
RUN mkdir -p /app/data

# Add binaries from the project's virtual environment to the PATH
ENV PATH="/app/.venv/bin:$PATH"

USER root

# Pass custom command to entrypoint script provided by the base image
ENTRYPOINT ["/entrypoint.sh"]
CMD [".venv/bin/python", "-m", "app.main"]
