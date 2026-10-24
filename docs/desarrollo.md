# Desarrollo

Guía para trabajar en el repositorio: estructura, convenciones, comandos y entrega continua.

El arranque de la arena, sus contratos HTTP y los límites actuales se documentan en [núcleo implementado](./nucleo.md).

## Requisitos

| Herramienta | Versión | Uso |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | 0.12 o superior | Python 3.12, dependencias y entorno del backend. |
| Node.js | 24 | Frontend; `corepack enable` activa la versión de pnpm fijada en `package.json`. |
| Docker con Compose | 2.24 o superior | Pila completa en contenedores. |

## Arranque

```bash
test -f .env || cp .env.example .env
make install
make arena-server ARENA_MODE=demo
```

En otra terminal, desde la raíz:

```bash
make dev-frontend
```

El frontend queda en `http://localhost:5173` y Vite redirige `/api` al backend en el puerto 8000. Para levantar la pila tal como se desplegará:

```bash
make up
make smoke
make down
```

Con contenedores, la aplicación queda en `http://localhost:8080`; `FRONTEND_PORT` cambia ese puerto. `make smoke` sólo lee estado. Para el recorrido con escrituras, exportar el `.env` (`set -a; . ./.env; set +a`) y ejecutar `make smoke-exercise` en una ronda base abierta. El reset archivado y la comparación amplia se describen en [núcleo implementado](./nucleo.md). El modo `demo` es explícitamente simulado y no necesita clave de IA.

## Estructura

```text
backend/
  src/agent_zero/
    main.py            fábrica de la aplicación y ciclo de vida
    config.py          configuración por variables AGENT_ZERO_*
    shared/            base de datos, dependencias, reloj, identificadores, salud
    sessions/          sesiones de participantes (modelo, esquemas, repositorio, servicio, API)
    events/            eventos de traza, broker en memoria y SSE de la arena
    routing/           decisiones allow/block/divert y rutas protegida/señuelo
    victim/            herramientas del agente de soporte y fixtures sintéticos
    attempts/          estados y resultados de un intento
    prober/            contrato AttackCase y familias de ataque
    analyzer/          evaluación de intentos y hallazgos
    policies/          contrato de políticas candidatas y su ciclo de vida
  tests/               un archivo de prueba por archivo fuente, espejando la estructura
frontend/
  src/
    app/               enrutamiento de la aplicación
    features/          participant, arena y operator, cada una con sus componentes, hooks, API y tipos
    shared/            cliente HTTP compartido
  nginx/               plantilla de nginx: SPA, proxy /api y SSE sin búfer
infra/
  compose.yaml         pila local y de CI
  scripts/smoke.sh     prueba de humo contra una URL
.github/workflows/     CI y publicación de imágenes
```

## Convenciones

- **Dominio primero.** Cada dominio del backend contiene sus propios `models.py` (tipos y ORM), `schemas.py` (contratos Pydantic), `repository.py`, servicios separados por operación (`session_creation_service.py`) y `router.py`. Un dominio importa contratos de otro, nunca su repositorio.
- **Archivos pequeños.** Unas 200 líneas como máximo por archivo y 150 por componente; si crece, se divide por responsabilidad, nunca por versión (`*_v2`, `*_new`).
- **Límites de confianza en el servidor.** Identidad, ruta y permisos los fija el backend. La vista pública recibe proyecciones sin campos de operación.
- **Tipado estricto.** `mypy --strict` en el backend y `strict` más `noUncheckedIndexedAccess` en TypeScript.
- **Formato automático.** Ruff en Python y Biome en TypeScript; `make format` aplica ambos.

## Ramas y revisión

`main` está protegida: no admite force-push ni borrado. El rol admin hace push directo; el resto del equipo entra por pull request. Antes de abrir un PR se ejecuta `make check`; si el cambio toca contenedores, también `make up && make smoke`.

## Integración y entrega continua

El flujo `ci` está desactivado por ahora y la verificación es local con `make check` y `make up && make smoke`. Se reactiva con `gh workflow enable ci`; entonces corre en cada pull request y en cada push a `main`:

1. **backend:** Ruff, formato, mypy y pytest.
2. **frontend:** Biome, TypeScript, Vitest y build.
3. **containers:** construye ambas imágenes, levanta la pila con Compose y ejecuta `infra/scripts/smoke.sh`.
4. **publish:** solo en `main`; publica `ghcr.io/carsanoja/agent-zero-backend` y `ghcr.io/carsanoja/agent-zero-frontend` con etiquetas `sha-<commit>` y `latest`.

Las imágenes no dependen del proveedor. El backend escucha en `$PORT` (8000 por defecto) y guarda SQLite en `/data`, que debe montarse como volumen persistente. El frontend escucha en `$PORT` (8080 por defecto) y redirige `/api` a `$BACKEND_URL`. El proveedor de despliegue está pendiente de los créditos de los aliados; al elegirlo se añadirá un job `deploy` después de `publish`.
