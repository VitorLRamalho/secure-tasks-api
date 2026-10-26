# syntax=docker/dockerfile:1

# ---- Estágio 1: instala dependências (compiladores ficam fora da imagem final) ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Estágio 2: imagem final mínima ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DATABASE_URL=sqlite:////data/app.db

# Usuário sem privilégios: um RCE na app não vira root no container
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data && chown app:app /data

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
