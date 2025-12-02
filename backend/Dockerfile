FROM python:3.11-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install --no-cache-dir -U pip setuptools wheel \
 && pip install --no-cache-dir "poetry>=2.0,<3.0" \
 && poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi --no-root

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
