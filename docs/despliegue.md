# Despliegue a producción

Ruta de cero a URL pública en unos 30 minutos, en cualquier VM Ubuntu con Docker (Hetzner, DigitalOcean, Fly Machines con VM, etc.). Nada depende del proveedor: la pila usa las imágenes que publica la CI en GHCR y Caddy como única entrada, con HTTPS automático.

## Qué se despliega

| Servicio | Origen | Expuesto |
| --- | --- | --- |
| `caddy` | `caddy:2-alpine`, `infra/caddy/Caddyfile` | puertos 80 y 443 |
| `frontend` | `ghcr.io/platanus-hack/agent-zero-frontend` | solo red interna |
| `backend` | `ghcr.io/platanus-hack/agent-zero-backend` | solo red interna |
| `postgres` | `pgvector/pgvector:pg17`, volumen | solo red interna |

Los archivos viven en `infra/`: `compose.prod.yaml`, `production.env.example`, `caddy/Caddyfile` y `scripts/`. Caddy desactiva el almacenamiento de la respuesta (`flush_interval -1`), así que el SSE de `/api/arena/events` llega al instante.

## Requisitos

- VM Ubuntu 22.04 o 24.04 con 4 GB de RAM (el backend descarga un modelo de embeddings de unos 220 MB al primer arranque) y acceso SSH con sudo.
- Un dominio o subdominio con registro DNS **A** hacia la IP de la VM, propagado antes del primer despliegue. Caddy no puede emitir el certificado sin él.
- Puertos 80 y 443 abiertos en el firewall del proveedor (el script de bootstrap abre también `ufw`).
- Acceso de lectura a las imágenes de GHCR (ver más abajo).

## Pasos

1. **Crear la VM** y apuntar el registro A del dominio a su IP.
2. **Preparar la VM**, desde tu máquina:

   ```bash
   scp infra/scripts/bootstrap-vm.sh usuario@IP:/tmp/
   ssh usuario@IP 'sudo bash /tmp/bootstrap-vm.sh'
   ```

   Instala Docker y el plugin compose, abre 80 y 443 con `ufw`, crea `/opt/agent-zero` y añade al usuario al grupo `docker`. Cierra la sesión SSH y vuelve a entrar para que el grupo surta efecto.
3. **Copiar `infra/`** a la VM:

   ```bash
   scp -r infra/. usuario@IP:/opt/agent-zero/
   ```

4. **Generar el `.env`** en la VM. Crea secretos aleatorios y deja el archivo con permisos 600 sin imprimirlos:

   ```bash
   cd /opt/agent-zero
   ./scripts/generate-secrets.sh
   nano .env
   ```

   Edita al menos `AGENT_ZERO_DOMAIN`, `ACME_EMAIL` y los límites. Para modo `live`, define `AGENT_ZERO_LLM_MODE=live` y `AGENT_ZERO_LLM_API_KEY`. Guarda el valor de `AGENT_ZERO_OPERATOR_SECRET` en tu gestor de contraseñas: es la entrada al panel de operador.
5. **Desplegar**:

   ```bash
   ./scripts/deploy.sh
   ```

   Valida que los secretos tengan la longitud mínima (32 caracteres, 44 para la clave de memoria) y que no queden valores de la plantilla; hace `pull`, `up -d --wait` y ejecuta `scripts/smoke.sh` contra `https://$AGENT_ZERO_DOMAIN`. El primer arranque del backend puede tardar varios minutos.
6. **Verificar desde un teléfono**: con los datos móviles (no el wifi de la VM), abre `https://tu-dominio/` y comprueba el candado, la arena y el código de unión. `https://tu-dominio/healthz` debe responder `ok`.

## Variables

`infra/production.env.example` lista todas. Las que el despliegue exige:

| Variable | Notas |
| --- | --- |
| `AGENT_ZERO_ENVIRONMENT` | `production`; activa los controles de arranque. |
| `AGENT_ZERO_DOMAIN`, `ACME_EMAIL` | Dominio público y correo para Let's Encrypt. |
| `AGENT_ZERO_OPERATOR_SECRET`, `AGENT_ZERO_GUARD_API_KEY`, `AGENT_ZERO_IDENTITY_SIGNING_KEY` | 32 caracteres o más cada uno, y el de identidad distinto del de operador. |
| `AGENT_ZERO_MEMORY_ENCRYPTION_KEY` | Clave Fernet (44 caracteres, base64 url-safe). Si cambia, la memoria cifrada ya guardada no se puede leer. |
| `POSTGRES_PASSWORD` | Solo se fija al crear el volumen; cambiarla después exige `ALTER USER` dentro de Postgres. |
| `AGENT_ZERO_LLM_MODE` | `live` o `demo`. |
| `AGENT_ZERO_LLM_API_KEY`, `AGENT_ZERO_LLM_DAILY_USD_LIMIT` | Solo en `live`; el tope diario corta el gasto. |
| `AGENT_ZERO_ARENA_*`, `AGENT_ZERO_RUNTIME_WORKER_CONCURRENCY` | Límites de la arena y concurrencia del runtime. La plantilla trae los valores medidos con 100 participantes: 8 workers y cola de 120 ([prueba de estrés](pruebas/estres-2026-10-24.md)). |
| `AGENT_ZERO_DATABASE_POOL_SIZE`, `AGENT_ZERO_DATABASE_MAX_OVERFLOW` | Pool de conexiones de la base principal en Postgres (10 + 20 por defecto). |
| `AGENT_ZERO_IMAGE_TAG` | Tag de imagen; `latest` o un sha largo. |

### URL de participación

`VITE_PUBLIC_PARTICIPANT_URL` se hornea en el frontend **al construir la imagen** (ver `frontend/Dockerfile`), por lo que ponerla en el `.env` de la VM no tiene efecto. La imagen de GHCR se construye sin ella y `JoinCode.tsx` usa `window.location.origin`, que en producción ya es el dominio público. No hay nada que hacer salvo que la URL de participación deba diferir del dominio de la arena; en ese caso habría que pasarla como `build-arg` en el job `publish` de la CI o resolverla en runtime desde el nginx.

## Visibilidad de las imágenes en GHCR

Los paquetes `agent-zero-backend` y `agent-zero-frontend` se publican con la visibilidad que tengan en la organización. Si son **privados**, la VM necesita iniciar sesión antes del primer `deploy.sh`, con un token clásico de solo lectura (`read:packages`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u USUARIO --password-stdin
```

Si `docker compose pull` responde `unauthorized` o `403`, falta este paso o el token no tiene el alcance. Cambiar la visibilidad es una decisión del equipo y se hace en la página del paquete en GitHub.

## Operación

### Rotar la clave de Anthropic

1. Crea la clave nueva en la consola de Anthropic.
2. Reemplaza `AGENT_ZERO_LLM_API_KEY` en `/opt/agent-zero/.env`.
3. `cd /opt/agent-zero && docker compose -p agent-zero --env-file .env -f compose.prod.yaml up -d backend`.
4. Revoca la clave anterior.

### Rotar el secreto de operador

1. Genera otro: `openssl rand -hex 32`.
2. Reemplaza `AGENT_ZERO_OPERATOR_SECRET` y recrea el backend como arriba.
3. Entra al panel de operador con el secreto nuevo y actualiza el `AGENT_ZERO_OPERATOR_SECRET` que uses en `smoke.sh --exercise`.

### Cambiar entre live y demo

Edita `AGENT_ZERO_LLM_MODE` en el `.env` (`live` exige `AGENT_ZERO_LLM_API_KEY`) y recrea el backend con el mismo comando. Los datos se conservan.

### Si cae el proveedor de LLM

Cambia a `demo` y reinicia solo el backend:

```bash
cd /opt/agent-zero
sed -i 's/^AGENT_ZERO_LLM_MODE=.*/AGENT_ZERO_LLM_MODE=demo/' .env
docker compose -p agent-zero --env-file .env -f compose.prod.yaml up -d backend
```

La arena sigue funcionando con las respuestas simuladas. Cuando el proveedor se recupere, vuelve a `live` del mismo modo. Avisa a los participantes de que el modo es demo.

### Volver atrás

Cada push verde a main publica un tag con el sha largo del commit. Para volver a una versión anterior:

```bash
cd /opt/agent-zero
AGENT_ZERO_IMAGE_TAG=<sha-largo-anterior> ./scripts/deploy.sh
```

Si `deploy.sh` falla en el smoke, imprime la imagen que corría antes. Para dejar el tag fijo, escríbelo en `AGENT_ZERO_IMAGE_TAG` del `.env`.

### Logs y estado

```bash
docker compose -p agent-zero --env-file .env -f compose.prod.yaml ps
docker compose -p agent-zero --env-file .env -f compose.prod.yaml logs -f backend
```

## Despliegue automático opcional

`.github/workflows/deploy.yml` despliega solo después de una CI verde en main, y también a mano (`workflow_dispatch`). Si no está configurado termina en verde sin hacer nada. Para activarlo:

- Variable de repositorio `DEPLOY_HOST`: IP o nombre de la VM.
- Secrets `DEPLOY_USER` y `DEPLOY_SSH_KEY` (clave privada de un usuario con acceso a Docker en la VM).
- El `.env` ya debe existir en `/opt/agent-zero`; el workflow copia `infra/` sin tocarlo y ejecuta `deploy.sh` con `AGENT_ZERO_IMAGE_TAG` igual al sha.

## Prueba local de la pila

Con `AGENT_ZERO_DOMAIN=localhost`, `HTTP_PORT=8480`, `HTTPS_PORT=8443` y `AGENT_ZERO_LLM_MODE=demo` en el `.env`, Caddy emite un certificado de su CA interna. Para el smoke con ese certificado, exporta el CA que Caddy generó:

```bash
docker cp <proyecto>-caddy-1:/data/caddy/pki/authorities/local/root.crt ca.crt
SSL_CERT_FILE=$PWD/ca.crt infra/scripts/smoke.sh https://localhost:8443
```
