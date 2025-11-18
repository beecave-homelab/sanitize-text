FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY sanitize_text ./sanitize_text

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

ENV FLASK_APP=sanitize_text.webui:create_app

CMD ["gunicorn", "-b", "0.0.0.0:8000", "sanitize_text.webui:create_app()"]
