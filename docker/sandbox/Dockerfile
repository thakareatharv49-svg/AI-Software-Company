FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates tar \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir pytest

WORKDIR /workspace
