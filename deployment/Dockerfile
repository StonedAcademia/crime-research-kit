FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TRCR_CASES_ROOT=/app/data/cases \
    TRCR_MODEL=ollama:llama3.1 \
    TRCR_SEARXNG_URL=http://searxng:8080 \
    TRCR_QDRANT_URL=http://qdrant:6333 \
    TRCR_QDRANT_HOST=qdrant \
    TRCR_QDRANT_PORT=6333 \
    OLLAMA_HOST=http://ollama:11434 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      fonts-noto \
      ghostscript \
      git \
      libgl1 \
      libglib2.0-0 \
      pngquant \
      qpdf \
      tesseract-ocr \
      tesseract-ocr-eng \
      unpaper \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY .agents ./.agents
COPY docs ./docs
COPY data/examples ./data/examples
COPY deployment ./deployment

RUN python -m pip install --upgrade pip \
    && python -m pip install -e '.[agentic,llm,mcp,web-local,documents,retrieval,memory-local]'

RUN mkdir -p /app/data/cases /app/data/exports /app/.cache/huggingface \
    && useradd --create-home --shell /bin/bash trcr \
    && chown -R trcr:trcr /app

USER trcr

CMD ["tail", "-f", "/dev/null"]
