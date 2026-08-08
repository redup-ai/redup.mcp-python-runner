ARG BASE_IMAGE=python:3.13-slim

FROM ${BASE_IMAGE} AS builder

RUN --mount=type=secret,id=PIP_INDEX_URL,required=false \
    export PIP_INDEX_URL=$(cat /run/secrets/PIP_INDEX_URL 2>/dev/null || true) \
    && python3 -m pip install --no-cache -U uv hatchling

WORKDIR /build
COPY pyproject.toml VERSION README.md LICENSE NOTICE packages.txt ./
COPY src ./src
RUN --mount=type=secret,id=PIP_INDEX_URL,required=false \
    export PIP_INDEX_URL=$(cat /run/secrets/PIP_INDEX_URL 2>/dev/null || true) \
    && if [ -n "${PIP_INDEX_URL}" ]; then export UV_INDEX_URL="${PIP_INDEX_URL}"; fi \
    && uv pip install --no-cache --system --python python --target=/app/libs .

# Preinstall allowlisted scientific packages into a dedicated venv (offline at runtime).
RUN --mount=type=secret,id=PIP_INDEX_URL,required=false \
    export PIP_INDEX_URL=$(cat /run/secrets/PIP_INDEX_URL 2>/dev/null || true) \
    && if [ -n "${PIP_INDEX_URL}" ]; then export UV_INDEX_URL="${PIP_INDEX_URL}"; fi \
    && uv venv /opt/code-tools-env --python python3 \
    && uv pip install --python /opt/code-tools-env/bin/python --no-cache -r /build/packages.txt \
    && cp /build/packages.txt /opt/code-tools-env/packages.txt

FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y --no-install-recommends \
      util-linux \
    && rm -rf /var/lib/apt/lists/*

# uv is not required at runtime; keep only for optional diagnostics if present.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONPATH=/app/libs \
    CODE_TOOLS_PYTHON=/opt/code-tools-env/bin/python \
    # Harden: never let child uv/pip talk to indexes even if mis-invoked.
    UV_NO_CACHE=1 \
    PIP_NO_INDEX=1

COPY --from=builder /app/libs /app/libs
COPY --from=builder /opt/code-tools-env /opt/code-tools-env
COPY VERSION /app/VERSION
COPY config/ /config/
COPY packages.txt /config/packages.txt

WORKDIR /app

RUN find / -xdev \( -perm -4000 -o -perm -2000 \) -type f -exec chmod a-s {} \; || true

EXPOSE 8000 9999

CMD ["python", "-m", "redup_mcp_python_runner.service", "/config/config.yaml"]
