# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY . .
ARG VITE_PUBLIC_PARTICIPANT_URL=
ENV VITE_PUBLIC_PARTICIPANT_URL=${VITE_PUBLIC_PARTICIPANT_URL}
RUN pnpm build

FROM nginxinc/nginx-unprivileged:1.28-alpine AS runtime
ENV PORT=8080 \
    BACKEND_URL=http://backend:8000
COPY nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=0755 nginx/15-backend-url.envsh /docker-entrypoint.d/15-backend-url.envsh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1
