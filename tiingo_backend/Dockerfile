FROM python:3.12-slim

WORKDIR /app

ARG INSTALL_FOUNDATION=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && if [ "$INSTALL_FOUNDATION" = "true" ]; then apt-get install -y --no-install-recommends git; fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-sentiment.txt requirements-llm.txt requirements-foundation.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-sentiment.txt -r requirements-llm.txt \
    && if [ "$INSTALL_FOUNDATION" = "true" ]; then pip install --no-cache-dir -r requirements-foundation.txt; fi

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
