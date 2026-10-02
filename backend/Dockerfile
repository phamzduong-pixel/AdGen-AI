FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN addgroup --system adgen && adduser --system --ingroup adgen adgen

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p /app/uploads && chown -R adgen:adgen /app

USER adgen

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
