FROM python:3.12-slim

WORKDIR /app

ARG INSTALL_FOUNDATION=true
ARG TORCH_CUDA=cpu

# TORCH_CUDA: cpu | cu124 | cu126 | cu128 | cu128-nightly
# RTX 50-series (sm_120) requires cu128 or cu128-nightly (cu124/cu126 lack sm_120 kernels).

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && if [ "$INSTALL_FOUNDATION" = "true" ]; then apt-get install -y --no-install-recommends git; fi \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-sentiment.txt requirements-llm.txt requirements-deep-learning.txt requirements-foundation.txt ./

RUN if [ "$TORCH_CUDA" = "cpu" ]; then \
      pip install --no-cache-dir 'torch>=2.1.0,<3.0'; \
    elif [ "$TORCH_CUDA" = "cu128-nightly" ]; then \
      pip install --no-cache-dir --pre torch \
        --index-url https://download.pytorch.org/whl/nightly/cu128; \
    else \
      pip install --no-cache-dir torch \
        --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}"; \
    fi

RUN pip install --no-cache-dir -r requirements.txt -r requirements-sentiment.txt -r requirements-llm.txt \
    -r requirements-deep-learning.txt \
    && if [ "$INSTALL_FOUNDATION" = "true" ]; then pip install --no-cache-dir -r requirements-foundation.txt; fi

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
