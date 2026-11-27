FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl bzip2 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY configs ./configs
COPY scripts/download_model.sh ./scripts/download_model.sh
COPY src/firered_poc ./src/firered_poc

ARG MODELS=aed
ARG SKIP_MODELS=0
RUN chmod +x scripts/download_model.sh \
    && if [ "$SKIP_MODELS" = "1" ]; then \
         echo "skip model download (mount models at /app/models)"; \
       elif [ "$MODELS" = "all" ]; then \
         ./scripts/download_model.sh; \
       else \
         ./scripts/download_model.sh --aed-only; \
       fi

RUN useradd --create-home --uid 10001 app \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "-m", "firered_poc.server", "--config", "configs/app.yaml", "--host", "0.0.0.0", "--port", "8000"]
