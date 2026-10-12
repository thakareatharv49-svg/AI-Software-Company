FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir pytest \
    && groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin sandbox

WORKDIR /workspace
USER 10001:10001
