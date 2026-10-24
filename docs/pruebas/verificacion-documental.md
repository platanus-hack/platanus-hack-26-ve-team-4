# Verificación de esta actualización documental

Fecha: 24 de octubre de 2026. Documento de traspaso principal: `cd60e7e`, sobre la implementación de referencia `1d0e21d2671dc21827ddf7cdb1e81f52a95cd5e2`. Los cambios de esta tarea afectan README y `docs/`; la aplicación, configuración ejecutable, lockfiles y JSON de evidencia permanecen intactos.

## Comprobaciones realizadas

| Comprobación | Resultado sobre el commit documental principal |
| --- | --- |
| Inventario Markdown | 45 archivos, incluido el README raíz. |
| Enlaces locales y fragmentos de encabezado | 926 referencias válidas a documentos, código, tests y artefactos. |
| Bloques Bash/sh | 82 bloques comprobados con `bash -n`. |
| Rutas de pytest en comandos | 53 rutas únicas existentes bajo `backend/tests`. |
| Contratos HTTP citados | 55 menciones de método/ruta comprobadas contra OpenAPI, incluidos paths dinámicos. |
| Colección de pytest | 862 casos; la matriz registra su distribución por carpeta. |
| Trazabilidad | `uv run pytest tests/test_traceability.py -q`: 3 aprobadas. |
| Interfaces CLI | `--help` de walkthrough, evals, verify_live y smoke aceptados. |
| Integridad de evidencia | Seis JSON cotejados con sus archivos SHA-256. |
| Diff | `git diff --check` sin errores. |

La revisión cruzó afirmaciones con servicios, routers, DTO, modelos y tests. Corrigió diferencias importantes: rutas reales frente a enums de diseño; cuotas LLM de proceso frente a planes durables; asesoría PATCHER esperada dentro de validación; memoria por sesión; archivos de ronda descargables por API; e idempotencia distinta entre runtime e intentos.

La comprobación de enlaces revisó destinos y anchors locales. La de Bash comprobó sintaxis, y la de OpenAPI comprobó que las rutas documentadas existen; por sí solas no ejecutan cada ejemplo ni sus efectos.

## Comandos que puede repetir el equipo

Desde la raíz:

```bash
git diff --check
(cd backend && uv run pytest tests/test_traceability.py -q)
(cd backend && uv run pytest --collect-only -q)
(cd artifacts/core-evaluation && shasum -a 256 -c *.sha256)
```

Las interfaces de los ejemplos pueden comprobarse sin servidor ni consumo del proveedor:

```bash
cd backend
uv run python -m agent_zero.walkthrough --help
uv run python -m agent_zero.evals --help
uv run python scripts/verify_live.py --help
python3 ../infra/scripts/smoke.py --help
```

Para cambios futuros, comprobar también cada enlace local y su encabezado, las rutas de código/tests citadas y la sintaxis de los bloques shell. Los routers y los DTO siguen siendo la fuente exacta del contrato; el OpenAPI de la app está en `/docs` cuando se arranca el servidor.

## Relación con las pruebas funcionales

Los 860 tests backend, 47 frontend, build de contenedores, comparación DEMO de 270 ejecuciones y ensayo LIVE de 93 llamadas son resultados de la implementación previa, descritos en [evidencias](./evidencias.md). Esta tarea documental ejecutó la colección, trazabilidad y comprobaciones anteriores, sin repetir el proveedor LIVE ni reiniciar rondas del equipo.

Al cambiar comportamiento, usar [la matriz por dominio](./por-dominio.md) y la [regresión general](./README.md), y registrar una ejecución nueva. Conservar los artefactos históricos y sus hashes; la actualización de un documento no debe convertir un resultado previo en una medición de otro commit.
