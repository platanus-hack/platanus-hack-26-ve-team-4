---
fecha: 2026-10-24
autor: "@usuario"
rama: worktree-agent-a039333f4df15144b
pr: pendiente
estado: en revisión
dominios: [infra]
requisitos: []
---

# Kit de despliegue a producción independiente del proveedor

## Qué cambió

- `infra/compose.prod.yaml`: pila con imágenes de GHCR (`AGENT_ZERO_IMAGE_TAG`, por defecto `latest`), Postgres con volumen, Caddy como única entrada (80 y 443, configurables con `HTTP_PORT` y `HTTPS_PORT`), `restart: unless-stopped` y healthchecks equivalentes a `compose.yaml`. Backend y Postgres no publican puertos.
- `infra/caddy/Caddyfile`: HTTPS automático para `AGENT_ZERO_DOMAIN`, proxy al frontend con `flush_interval -1` para el SSE.
- `infra/production.env.example`: plantilla con todas las variables, incluida `AGENT_ZERO_RUNTIME_WORKER_CONCURRENCY` (se expone, no se recomienda valor).
- `infra/scripts/bootstrap-vm.sh`, `deploy.sh` y `generate-secrets.sh`.
- `.github/workflows/deploy.yml`: despliegue por SSH tras `ci` verde en main o manual; termina en verde sin hacer nada si falta la variable `DEPLOY_HOST` o los secrets.
- `docs/despliegue.md`, enlazada desde `docs/README.md`.

## Por qué

Cierra lo técnico del issue #16. Publicar la arena queda en: crear la VM, apuntar el DNS, copiar un `.env` y ejecutar un script. Aún falta elegir proveedor y por tanto la URL real.

## Archivos

`infra/compose.prod.yaml`, `infra/caddy/Caddyfile`, `infra/production.env.example`, `infra/scripts/{bootstrap-vm,deploy,generate-secrets}.sh`, `.github/workflows/deploy.yml`, `docs/despliegue.md`, `docs/README.md`.

## Cómo se verificó

- Pila levantada con `-p az-prod-local`, `AGENT_ZERO_DOMAIN=localhost`, puertos 8480 y 8443, modo `demo`, embedder `fake` y un `.env` generado con `generate-secrets.sh` en un directorio temporal. Los cuatro servicios quedaron `healthy` con `up -d --wait`.
- `curl -k https://localhost:8443/healthz` devolvió `ok`; la SPA respondió 200 `text/html`; `/readyz` devolvió `{"status":"ok"}`; el puerto 80 redirige con 308 a HTTPS.
- `/api/arena/events` respondió HTTP/2 200 `text/event-stream` y el primer `: ping` llegó a los 5 ms, sin almacenamiento intermedio.
- `smoke.py` contra `https://localhost:8443` con `SSL_CERT_FILE` apuntando a la CA interna de Caddy: OK (modo demo). Con el Python del sistema de macOS (LibreSSL) la verificación del certificado falla aunque curl y openssl lo aceptan; con Python 3.12 de Homebrew pasa.
- `docker compose pull` desde GHCR: `unauthorized` sin sesión y `403 Forbidden` con el token de `gh`, así que se construyeron las imágenes en local y se etiquetaron con el nombre de GHCR (tag `localtest`). El camino de pull real no se pudo comprobar.
- `deploy.sh` rechaza un `.env` con valores de plantilla; con un `.env` válido pasa la validación y llega al `pull`.
- `actionlint` sin avisos; `shellcheck` solo informa SC1091 (`/etc/os-release` no existe en macOS).
- El arranque en `production` exigió `AGENT_ZERO_MEMORY_ENCRYPTION_KEY` (clave Fernet), que `compose.yaml` no necesita; se añadió a la plantilla, al generador y a la validación.

## Riesgos y efectos en otros frentes

- `VITE_PUBLIC_PARTICIPANT_URL` se hornea al construir la imagen; la imagen de GHCR no la lleva y el frontend cae a `window.location.origin`, correcto cuando la arena vive en su propio dominio.
- Si los paquetes de GHCR son privados, la VM necesita `docker login ghcr.io` con un token de solo lectura. La visibilidad no se cambió.

## Pendiente

- Elegir proveedor, crear la VM y el DNS, y ejecutar el primer despliegue real.
- Comprobar `bootstrap-vm.sh` en una VM Ubuntu real y el `pull` desde GHCR con credenciales válidas.
- Comprobar `deploy.yml` con `DEPLOY_HOST` configurado.
