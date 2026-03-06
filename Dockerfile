FROM node:22-slim AS companion-build

WORKDIR /build
COPY companion/package.json companion/package-lock.json ./
RUN NODE_OPTIONS=--max-old-space-size=512 npm ci
COPY companion/ .
RUN NODE_OPTIONS=--max-old-space-size=512 npm run build

FROM node:22-slim AS dashboard-build

WORKDIR /build
COPY dashboard/package.json dashboard/package-lock.json ./
RUN NODE_OPTIONS=--max-old-space-size=512 npm ci
COPY dashboard/ .
RUN NODE_OPTIONS=--max-old-space-size=512 npm run build

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

ARG CACHE_BUST=phase3
COPY . .
COPY --from=companion-build /static/companion ./static/companion
COPY --from=dashboard-build /static/dashboard ./static/dashboard

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
