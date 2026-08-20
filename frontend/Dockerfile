# Built from the repo root (see docker/docker-compose.yml's `context: ..`):
# the lockfile and workspace manifest live there (frontend/ is a pnpm
# workspace member, not a standalone package -- see pnpm-workspace.yaml).
#
# VITE_API_BASE_URL is baked in at build time (Vite env vars are inlined
# into the JS bundle, not read at container runtime) -- it must be the URL
# the *browser* can reach, not a Docker-network hostname like
# http://backend:8000: the frontend container only ever serves static
# files, every API call happens client-side from the visitor's browser.

FROM node:22-alpine AS builder

WORKDIR /app
RUN corepack enable

COPY pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend/package.json frontend/package.json
RUN pnpm install --frozen-lockfile

COPY frontend/ frontend/

ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app/frontend
RUN pnpm build

FROM nginx:1.27-alpine AS runtime

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://localhost:80 || exit 1
