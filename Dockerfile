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

# Make directory for the app as root (last time we use root)
RUN mkdir -p /app && \
    chown $DOCKER_USER:$DOCKER_USER /app

# Switch to the non-root user - NEVER GO BACK TO ROOT
USER $DOCKER_USER

# Set the working directory
WORKDIR /app

# Set UV cache to a location we can write to
ENV UV_CACHE_DIR=/tmp/uv-cache

# Install python
RUN uv python install 3.13

# Install the Python project's dependencies using the lockfile and settings
COPY --chown=$DOCKER_USER:$DOCKER_USER pyproject.toml uv.lock /app/

# Run without cache mount - simpler and avoids permission issues
RUN uv sync --frozen --no-install-project

# Then, add the rest of the project source code and install it
COPY --chown=$DOCKER_USER:$DOCKER_USER . /app

# Add binaries from the project's virtual environment to the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Sync the project's dependencies and install the project
RUN uv sync --frozen

# Install FastAPI dependencies using uv pip (not .venv/bin/pip)
RUN uv pip install \
    fastapi \
    uvicorn \
    pydantic \
    pydantic-settings \
    sqlalchemy \
    httpx

# Pass custom command to entrypoint script provided by the base image
ENTRYPOINT ["/entrypoint.sh"]

# Expose the API port
EXPOSE 8080

# Command to run the application
CMD [".venv/bin/python", "-m", "app.main"]
