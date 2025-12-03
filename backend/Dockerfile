FROM python:3.11-slim-bookworm
WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir -U pip setuptools wheel \
 && pip install --no-cache-dir "poetry>=2.0,<3.0" \
 && poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root --without dev,embed-heavy

COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
