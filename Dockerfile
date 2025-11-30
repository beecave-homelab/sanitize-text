FROM python:3.12-slim

LABEL org.opencontainers.image.source=https://github.com/beecave-homelab/sanitize-text

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY sanitize_text ./sanitize_text
COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

EXPOSE 8080

ENV FLASK_APP=sanitize_text.webui:create_app

CMD ["gunicorn", "-b", "0.0.0.0:8080", "sanitize_text.webui:create_app()"]
