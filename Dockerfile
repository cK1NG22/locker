FROM node:22-slim AS companion-build

WORKDIR /build
COPY companion/package.json companion/package-lock.json ./
RUN npm ci
COPY companion/ .
RUN npm run build

FROM node:22-slim AS dashboard-build

WORKDIR /build
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ .
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .
COPY --from=companion-build /static/companion ./static/companion
COPY --from=dashboard-build /static/dashboard ./static/dashboard

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
