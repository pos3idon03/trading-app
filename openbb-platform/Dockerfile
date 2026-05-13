FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENBB_USER_SETTINGS_DIR=/root/.openbb_platform

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r requirements.txt \
 && openbb-build

COPY seed_credentials.py entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

EXPOSE 6900

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:6900/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--host", "0.0.0.0", "--port", "6900"]
