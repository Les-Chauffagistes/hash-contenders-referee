FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=secret,id=pipindex \
    PIP_EXTRA_INDEX_URL="$(cat /run/secrets/pipindex 2>/dev/null || true)" \
    pip install --no-cache-dir --require-hashes --only-binary :all: --trusted-host 10.10.0.3 -r requirements.txt

COPY prisma ./prisma
RUN prisma generate


FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/prisma-python /root/.cache/prisma-python
COPY --from=builder /app/prisma ./prisma

COPY . .

EXPOSE ${SERVER_PORT:-8095}

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${SERVER_PORT:-8095}/health || exit 1

CMD ["sh", "-c", "\
  export DB_PASSWORD=$(cat /run/secrets/db_password) && \
  export DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST:-}:5432/${DB_NAME} && \
  export API_TOKEN=$(cat /run/secrets/api_token) && \
  export JWT_SECRET=$(cat /run/secrets/jwt_secret) && \
  until prisma migrate deploy; do echo 'DB pas prête, retry...'; sleep 2; done && \
  exec python main.py"]