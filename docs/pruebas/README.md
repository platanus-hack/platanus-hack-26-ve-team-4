# Pruebas: ejecución y resultados

Esta carpeta es la guía de verificación para continuar el proyecto. Los comandos parten de la raíz del repositorio salvo que el bloque cambie de directorio. [Por dominio](./por-dominio.md) indica qué ejecutar según el cambio; [evidencias](./evidencias.md) explica los artefactos guardados y su reproducción. La [verificación documental](./verificacion-documental.md) registra las comprobaciones ejecutadas al preparar este traspaso.

## Resultado de referencia

Implementación verificada el 24 de octubre de 2026, antes de esta actualización exclusivamente documental, sobre el árbol publicado en `1d0e21d2671dc21827ddf7cdb1e81f52a95cd5e2`:

| Verificación ejecutada | Resultado y alcance |
| --- | --- |
| Backend completo | 860 aprobadas, 2 LIVE opcionales omitidas, sin warnings. |
| Backend estático | Ruff, formato y mypy estricto de `src`, `tests` y `scripts` aprobados. |
| Frontend | 47 pruebas de Vitest aprobadas; Biome, TypeScript y build aprobados. |
| Contenedores | Ambas imágenes construidas; API, nginx, SPA, autorización, SSE y ejercicio completo comprobados. |
| Flota original | 22/22 comprobaciones HTTP en modo demo. |
| Comparación DEMO | 270 ejecuciones, 732 llamadas simuladas, 90/90 → 0/90 violaciones, utilidad 45/45 en ambas versiones. |
| Ciclo LIVE | Once comprobaciones aprobadas, 93 llamadas reales y los cinco roles; coste estimado de US$0.0101596 según tokens y tarifas configuradas. |
| Historia de implementación | 25 commits comprobados individualmente en importaciones, nombres, arranque, sesión y consulta de políticas; el mapa conserva procedencia. |

No hubo revisión visual en navegador ni prueba de acceso desde un teléfono externo. El resultado DEMO verifica integración del laboratorio; no mide eficacia de un LLM real. El ensayo LIVE comprueba el ciclo, no la comparación amplia de 270 ejecuciones ni una meta de capacidad.

La actualización documental vuelve a validar enlaces, comandos de colección y trazabilidad. No convierte esos resultados históricos en ejecuciones nuevas ni consume el proveedor para editar documentos.

## Preparar dependencias

Requisitos: Python 3.12 mediante `uv`, Node 24 y pnpm 10.28.2. Usar los lockfiles del repositorio:

```bash
(cd backend && uv sync --frozen)
(cd frontend && pnpm install --frozen-lockfile)
```

Para las pruebas automatizadas no es necesario copiar `.env` ni configurar una clave de IA. Ejecutarlas en una terminal sin variables `AGENT_ZERO_*` exportadas del servidor; esas variables pueden alterar los fixtures. En particular, no habilitar `AGENT_ZERO_LLM_LIVE_SMOKE` para una regresión normal.

Si se utilizó la misma terminal para cargar el `.env` de operación, esta variante limpia sólo el entorno del proceso hijo y mantiene intacto el archivo y la terminal:

```bash
python3 - <<'PY'
import os
import subprocess
environment = {key: value for key, value in os.environ.items() if not key.startswith("AGENT_ZERO_")}
subprocess.run(["make", "check"], env=environment, check=True)
PY
```

## Regresión general

```bash
make check
(cd frontend && pnpm build)
```

`make check` ejecuta lint, formato, tipado y ambas suites. El build de frontend es un comando adicional. En backend:

```bash
cd backend
uv run pytest -q
uv run pytest --collect-only -q
```

La colección de referencia contiene 862 casos: 860 normales y dos de proveedor real. Un cambio futuro puede aumentar el total; no reducir casos para reproducir el número histórico. Pytest trata `SAWarning` y `PytestUnraisableExceptionWarning` como errores mediante [pyproject.toml](../../backend/pyproject.toml).

Una regresión detectada durante la implementación fue una consulta que reutilizaba una sesión SQLAlchemy después de salir de `async with`; se corrigió el alcance en [test_repository.py](../../backend/tests/registry/test_repository.py). Una advertencia de GC puede aparecer en el test siguiente: atribuir el checkout original y corregir el recurso, sin silenciar el warning.

## Integración HTTP en contenedores

Desde una ronda de ensayo, con Docker disponible:

```bash
test -f .env || cp .env.example .env
make up
make smoke
make smoke-exercise
```

`make smoke` sólo lee salud, SPA, estado público y autorización, y abre el SSE. `make smoke-exercise` carga el `.env` en su proceso, crea sesión e intentos, verifica idempotencia, utilidad, violación base, ocho casos de validación, activación, repetición protegida y revelación. Necesita una ronda base abierta y termina dejándola revelada/cerrada.

Para repetir con archivado explícito de una ronda drenada:

```bash
set -a
. ./.env
set +a
./infra/scripts/smoke.sh http://localhost:8080 --exercise --reset-round
```

No usar reset sobre el ensayo de otra persona. Devuelve 409 si queda trabajo activo; detener nuevas generaciones y dejar drenar. El reset invalida tokens de la ronda y conserva el archivo de evidencia. `make down` conserva el volumen; `down --volumes` lo elimina y no forma parte del ensayo normal.

## Suites por nivel

| Nivel | Entrada | Dependencia externa |
| --- | --- | --- |
| Unitarias e integración en pytest | [Matriz por dominio](./por-dominio.md) | SQLite y proveedores de prueba; sin red de IA. |
| Componentes frontend | `cd frontend && pnpm test` | jsdom; no equivale a revisión visual. |
| Flota HTTP | [prueba-flota.md](../prueba-flota.md) | Servidor propio; `demo` no consume IA. |
| Ejercicio de arena | `infra/scripts/smoke.sh --exercise` | Servidor y nginx; escribe en la ronda. |
| Evaluación comparativa | [evals](../dominio/evals.md) y [evidencias](./evidencias.md) | 45 casos por versión y repetición; coste si se elige LIVE. |
| Ensayo LIVE | `cd backend && uv run python scripts/verify_live.py --help` | API real, clave local y presupuesto explícito. |

Los dos tests LIVE de `tests/llm/test_live_provider.py` requieren `AGENT_ZERO_LLM_LIVE_SMOKE=1`. El script `verify_live.py` es otra entrada, con datos temporales y comprobaciones del producto completo; no se habilita al ejecutar `make check`.

## Registrar una nueva ejecución

Anotar commit, si el árbol estaba modificado, comando, fecha, modo/proveedor, resultado, skips y fallos. Mantener juntos JSON y `.sha256`; no sobrescribir los artefactos de referencia. Para datos nuevos usar otro nombre o carpeta, sin tokens de sesión, claves, secreto de operador ni credenciales reales.

Si una ejecución falla, conservar el error y los casos pendientes; no excluirlos para mejorar tasas. La [guía de continuidad](../continuidad.md) define qué validación corresponde a cada tipo de cambio y cómo preparar su revisión.
