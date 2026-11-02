FROM node:24-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

COPY frontend ./
RUN npm run build


FROM nginxinc/nginx-unprivileged:1.31-alpine AS runtime

COPY deploy/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=builder /app/dist /usr/share/nginx/html

ENV AERONA_BACKEND_ORIGIN=http://backend:8000 \
    NGINX_ENVSUBST_FILTER=^AERONA_

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1:8080/healthz"]
