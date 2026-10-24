# Desarrollo

Guía de trabajo sobre la implementación publicada en `core/complete-autonomous-loop`. Para incorporarse al proyecto, empezar por [continuidad](./continuidad.md), consultar el [mapa de dominios](./dominio/README.md) y elegir pruebas en [la matriz](./pruebas/por-dominio.md). El arranque operativo y los contratos HTTP están en [núcleo](./nucleo.md).

## Requisitos y dependencias fijadas

| Herramienta | Referencia del repositorio | Uso |
| --- | --- | --- |
| Python | 3.12, según [pyproject.toml](../backend/pyproject.toml). | API, workers y pruebas. |
| uv | La imagen usa 0.12.7; dependencias en [uv.lock](../backend/uv.lock). | Instalación y ejecución del backend. |
| Node.js | 24 en build y CI. | Frontend. |
| pnpm | 10.28.2 en [package.json](../frontend/package.json); [lockfile](../frontend/pnpm-lock.yaml). | Instalación, Vitest y build. |
| Docker y Compose v2 | Compatibles con [compose.yaml](../infra/compose.yaml), incluido `env_file.required`. | Verificación de la pila completa. |

Para reproducir dependencias sin resolver versiones nuevas:

```bash
(cd backend && uv sync --frozen)
(cd frontend && pnpm install --frozen-lockfile)
```

`make install` es la entrada cómoda de instalación; una actualización intencional de dependencias debe incluir sus lockfiles y la validación correspondiente. No se necesita clave de IA para la regresión automatizada normal.

## Arrancar para desarrollar

Desde la raíz:

```bash
test -f .env || cp .env.example .env
make arena-server ARENA_MODE=demo
```

En otra terminal:

```bash
make dev-frontend
```

El frontend queda en `http://localhost:5173/`; Vite redirige `/api` a `http://localhost:8000`. `VITE_API_PROXY` permite apuntar a otro backend. La copia condicional conserva un `.env` previo: revisar sus valores antes de reutilizar un ensayo, y personalizar el secreto de operador.

Los targets de servidor cargan el `.env` de la raíz. `Settings()` usado directamente lee `.env` desde el directorio de ejecución; ejecutar desde otro directorio sin exportar configuración puede cambiar modo, datos o secreto. Mantener una terminal distinta para las pruebas, sin variables `AGENT_ZERO_*` del servidor exportadas. La [guía de pruebas](./pruebas/README.md) incluye una ejecución aislada del entorno del proceso.

`demo` propone herramientas reales del escenario mediante un proveedor determinista y muestra evidencia simulada. `offline` requiere un guion inyectado y falla explícitamente si se agota. `live`/`record` consumen la API configurada; `replay` utiliza una cassette. Ver [LLM](./dominio/llm.md).

## Mapa del código vigente

| Área | Rutas y responsabilidad |
| --- | --- |
| Composición | `backend/src/agent_zero/main.py`, `config.py`, `shared/`, `fleet/` y `arena/core.py`. |
| Participación y ronda | `sessions/`, `attempts/`, `routing/`, `events/`, `arena/`. Las rutas de operación viven en `arena/`, no en un módulo backend `operator/`. |
| Escenario y controles | `victim/`, `oracles/`, `policies/`, `patches/`. |
| Autonomía y comparación | `prober/`, `analyzer/`, `evals/`. |
| Plataforma | `registry/`, `identity/`, `agent_gateway/`, `armor/`, `memory_bank/`, `runtime/`, `telemetry/`, `llm/`. |
| Recorrido HTTP original | `backend/src/agent_zero/walkthrough/`; conserva el escenario de flota 1.0.0. |
| Verificación LIVE | `backend/scripts/`; datos temporales, presupuesto explícito y artefactos. |
| Frontend | `frontend/src/app/`, `features/{participant,arena,operator}/`, `shared/api/` y `styles.css`. |
| Entrega | `frontend/nginx/`, Dockerfiles, `infra/` y `.github/workflows/ci.yml`. |

Los servicios usan esquemas cerrados, modelos y repositorios según su necesidad; no todos los dominios tienen router o repositorio propios. Las pruebas suelen seguir la estructura del código, pero los efectos de oráculos, patches y routing están integrados en `tests/arena` y `tests/evals`. El [índice por dominio](./dominio/README.md) enlaza las entradas reales.

## Convenciones de implementación

- Definir fronteras con DTO, servicios y enums explícitos. Los acoplamientos existentes se describen en [arquitectura](./arquitectura.md); no asumir una separación de capas que el código todavía no tiene.
- Preferir archivos y componentes compactos, alrededor de 200 y 150 líneas respectivamente. Dividir por responsabilidad, conservando un flujo legible; no crear copias `*_v2` o `*_new` como solución temporal.
- Mantener cliente, entorno, versión y operación fijados por el servidor. Preservar los guards persistentes y la separación de proyecciones públicas/operativas.
- Conservar transacciones, IDs de operaciones, checkpoints y outbox al modificar efectos. Un reintento debe probar estado persistido, además de la respuesta.
- Usar mypy estricto y TypeScript estricto; Ruff y Biome son las referencias de formato. `make format` escribe cambios: revisar su diff antes de incluirlos.
- Mantener desconocidos los costes/tokens no medidos y separar `simulated`, `replayed` y `live`. Una explicación LLM no reemplaza un veredicto ni un resultado de validación.

## Qué ejecutar antes de compartir

```bash
make check
(cd frontend && pnpm build)
```

`make check` incluye lint, formato, tipado de `src/tests/scripts` y ambas suites. El build del frontend es adicional. Las advertencias de SQLAlchemy y las excepciones ignoradas fallan los tests. Los comandos selectivos y las garantías de cada suite están en [pruebas por dominio](./pruebas/por-dominio.md).

Para cambios en imágenes, proxy o contratos HTTP, usar una ronda de ensayo:

```bash
make up
make smoke
make smoke-exercise
```

`make smoke` sólo lee. El ejercicio carga el `.env` en su proceso, escribe intentos y revela/cierra la ronda al terminar. Para repetirlo con reset explícito y archivado, seguir [infraestructura](./dominio/infraestructura.md); no borrar el volumen para ocultar un fallo ni reiniciar el ensayo compartido de otra persona.

Un cambio exclusivamente documental se comprueba mediante enlaces, rutas, bloques de comandos y trazabilidad; no exige gastar el proveedor de nuevo. Los resultados históricos y sus límites están en [pruebas](./pruebas/README.md) y [evidencias](./pruebas/evidencias.md).

## Ramas, commits y revisión

La implementación se publicó en `core/complete-autonomous-loop` de `origin` y `org`. Eso no implica que esté integrada en `main`. Continuar en una rama acordada o partir de esa referencia; revisar el remoto y el diff antes de enviar.

Hacer commits coherentes por cambio: contrato, consumidores necesarios, pruebas y documentación deben permitir un checkout utilizable. No separar un esquema de sus consumidores si deja commits intermedios rotos. Solicitar revisión según [CODEOWNERS](../.github/CODEOWNERS) y [equipo](./equipo.md), con el comportamiento final y la validación concreta en la descripción.

No dar por existentes permisos de administrador, protección de ramas o aprobación obligatoria sólo porque aparezcan en un plan antiguo. El equipo comprueba esas reglas en el repositorio antes de integrar; publicar una rama no autoriza a forzar `main`.

## CI y publicación

[ci.yml](../.github/workflows/ci.yml) define PR y push a `main` como disparadores:

1. Backend: instalación congelada, Ruff, formato, mypy y pytest.
2. Frontend: instalación congelada, Biome, TypeScript, Vitest y build.
3. Contenedores: tras ambas suites, genera un secreto efímero, usa `demo`, construye imágenes y ejecuta smoke de lectura más ejercicio completo.
4. Publicación: sólo en push a `main` después de aprobar contenedores; publica `ghcr.io/<repository_owner>/agent-zero-{backend,frontend}` con SHA largo y `latest`.

El YAML es la configuración, no prueba de que Actions esté habilitado o de que una ejecución remota haya pasado. Comprobar la disponibilidad y los checks del PR en GitHub. Un push de una rama de trabajo no activa por sí solo el trigger de push definido para `main`.

No hay un job de despliegue de aplicación ni una URL pública verificada. Backend usa `$PORT` y `/data` persistente; nginx usa `$PORT` y `$BACKEND_URL`. Elegir hosting, TLS, respaldo/restauración y medición de carga requiere trabajo operativo explícito, descrito en [continuidad](./continuidad.md).
