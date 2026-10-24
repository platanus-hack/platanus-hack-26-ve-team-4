# Continuidad y traspaso al equipo

El núcleo está implementado y publicado en la rama `core/complete-autonomous-loop` de los remotos personal y de organización. La referencia funcional antes de esta actualización documental es `1d0e21d2671dc21827ddf7cdb1e81f52a95cd5e2`. Esta guía orienta el trabajo siguiente; no supone integración en `main`, publicación de una URL ni pruebas nuevas del proveedor.

## Primera sesión de trabajo

1. Revisar el estado y cambios locales antes de cambiar de rama; conservar archivos ajenos a la tarea.
2. Leer [arquitectura](./arquitectura.md), [flujo](./dominio/flujo-de-decision.md) y el documento del [dominio](./dominio/README.md) que se vaya a cambiar.
3. Instalar con lockfiles: `(cd backend && uv sync --frozen)` y `(cd frontend && pnpm install --frozen-lockfile)`.
4. Ejecutar [la regresión](./pruebas/README.md) en una terminal que no exporte la configuración del servidor.
5. Ensayar en `demo` con datos propios; usar otro directorio o volumen para conservar la ronda de otra persona.

Desde la raíz, el arranque más corto es:

```bash
test -f .env || cp .env.example .env
make up
make smoke
```

Leer los valores si `.env` ya existía: el comando lo conserva. El ejemplo selecciona `demo`; un archivo anterior podría seleccionar `live`. Abrir `http://localhost:8080/`, `/arena` y `/operator`. Para desarrollar sin Docker: `make arena-server ARENA_MODE=demo`, y `make dev-frontend` en otra terminal.

La [guía del núcleo](./nucleo.md) explica campañas, repetición, reset y evaluación. El ejercicio `make smoke-exercise` escribe y revela una ronda; no es una sonda de salud inocua. El recorrido original de la flota necesita su propio directorio y exportador `memory`, según [prueba-flota](./prueba-flota.md).

## Qué puede dar por comprobado el equipo

| Área | Resultado de referencia | Límite de interpretación |
| --- | --- | --- |
| Regresión | 860 tests backend aprobados, dos LIVE omitidos; 47 tests frontend, lint/tipado/build correctos. | Corpus del repositorio; no cobertura universal. |
| Ciclo del producto | Sesión → herramienta → oráculo → hallazgo → validación → activación → repetición/reversión. | Escenario sintético y catálogo finito. |
| Estado durable | Idempotencia, leases/fencing, outbox, journal de auditoría y reset recuperable. | Garantías específicas probadas; cuotas LLM y algunos locks siguen locales. |
| Evaluación DEMO | 270 ejecuciones, 90/90 → 0/90 violaciones y 45/45 tareas correctas por versión. | Proveedor determinista `simulated`, sin coste/tokens comerciales medidos. |
| Ensayo LIVE | 93 llamadas, cinco roles y once controles del ciclo aprobados. | No es la comparación amplia de 270 ejecuciones ni una prueba de carga. |
| Contenedores y flota | Build de ambas imágenes, smoke completo y recorrido de flota 22/22. | Verificación HTTP/DOM; falta revisión visual y acceso móvil externo. |

Artefactos, costes estimados, hashes, primer timeout conservado y procedencia en [evidencias](./pruebas/evidencias.md). La historia se reorganizó antes del primer push; el mapa conserva los commits originales de los informes y equivalentes con el mismo árbol. No editar esos JSON para actualizar un número de versión.

## Dónde entrar al código

| Cambio | Primeros archivos y documentos |
| --- | --- |
| Arranque/composición | `main.py`, `fleet/fleet_builder.py`, `arena/core.py`; [fleet](./dominio/fleet.md), [shared](./dominio/shared.md). |
| Contratos de audiencia | `sessions/router.py`, `attempts/schemas.py`, `attempts/router.py`; [sessions](./dominio/sessions.md), [attempts](./dominio/attempts.md), [frontend](./dominio/frontend.md). |
| Herramienta o regla de negocio | `victim/tool_schemas.py`, `scenario_tools.py`, `policies/validator_catalog.py`, `policy_engine.py`; [gateway](./dominio/agent-gateway.md), [oracles](./dominio/oracles.md). |
| Política/validación | `policies/policy_service.py`, `patches/validation_runner.py`, `defense_scheduler.py`; [policies](./dominio/policies.md), [patches](./dominio/patches.md). |
| Ataques/evaluación | `prober/playbooks.py`, `mutation.py`, `evals/suite.py`, `runner.py`; [prober](./dominio/prober.md), [evals](./dominio/evals.md). |
| Persistencia/concurrencia | `runtime/run_lease.py`, `events/event_store.py`, `arena/round_service.py`; [runtime](./dominio/runtime.md), [events](./dominio/events.md), [telemetry](./dominio/telemetry.md). |
| Modelo/proveedor | `llm/factory.py`, `catalog.py`, `instrumented_model.py`; [LLM](./dominio/llm.md). |

Los frentes y revisores están en [equipo](./equipo.md) y CODEOWNERS. Confirmar con el equipo quién toma cada mejora; esta guía no asigna trabajo nuevo a una persona.

## Siguiente trabajo recomendado

| Prioridad | Mejora pendiente | Comprobación de salida |
| --- | --- | --- |
| Antes de exponer público | Configuración no local con claves separadas, dominio/HTTPS, acceso móvil y protección administrativa. | Arranque sin secretos de ejemplo, URL comprobada desde otro dispositivo y ausencia de datos privados en respuestas públicas. |
| Antes de datos reales | Política de retención/borrado de mensajes y evidencias, claves/backup y anclaje externo. | Los mensajes de `Attempt` están en JSON de app, no cifrados por Memory Bank; demostrar el alcance de cada borrado y recuperación. |
| Disponibilidad | Cleanup de errores de inicialización anteriores al `yield` en `main.py`. | Fallo inyectado en arranque devuelve todos los recursos, además del cierre normal ya cubierto. |
| Escala | Cuotas LLM y limiter persistentes/compartidos; coordinación del ledger. | Reiniciar o añadir un worker no reinicia ni multiplica cupos autorizados. |
| Datos | Migraciones y procedimiento de backup/restauración. | Actualizar una base anterior y recuperar una copia compatible sin eliminar evidencia. `create_all` no migra columnas. |
| Operación | UI de archivos de ronda y sus descargas; suscripción explícita a `round_started`. | Misma autorización que API, enlaces al archivo correcto y cambio de ronda sin depender sólo del polling. |
| Evaluación | Nuevas variantes reservadas y comparación amplia LIVE con presupuesto. | Reportar denominadores, inconclusos, estado limpio, modelos, hashes y coste estimado, sin reutilizar como inéditos los casos publicados. |
| Experiencia/capacidad | Revisión visual y prueba de carga acotada. | Verificar móvil/accesibilidad, cola y p95 con tamaño de muestra; no confundir plazas con llamadas simultáneas. |

La selección adaptativa por novedad, un servidor de autorización de operadores y restauración arbitraria de un snapshot no están implementados. No anunciar esas capacidades a partir de nombres de DTO o enums del diseño inicial.

## Invariantes que una mejora debe conservar

- Cliente, ruta, versión e identidad de operación se fijan fuera del mensaje del modelo.
- Una acción completada sigue siendo evidencia aunque la salida se filtre después.
- La comprobación de saldo y su efecto comparten la reserva de escritura del entorno.
- Un intento usa una sola política; la activación espera drenaje y conserva un padre verificable.
- El LLM no modifica el veredicto determinista ni añade controles fuera del catálogo.
- Protegido, señuelo y validaciones tienen memoria y efectos separados; una sesión desviada no vuelve al protegido.
- Un inconcluso y un caso pendiente no cuentan como defensa exitosa.
- La proyección pública se construye en el servidor; ocultar una columna en React no concede privacidad.

## Preparar el siguiente cambio

Crear una rama pequeña, describir el comportamiento que cambia y revisar el DTO fuente y su tipo espejo. Añadir una prueba de efecto o recuperación que aporte evidencia; ejecutar el dominio afectado y luego la regresión general. Si se tocan contenedores/proxy, añadir el smoke en una ronda de ensayo nueva.

Actualizar el documento de dominio, la [matriz de pruebas](./pruebas/por-dominio.md) y la trazabilidad si cambió un requisito. Guardar nueva evidencia con otro nombre, sin credenciales. Hacer commits que incluyan sus dependencias y dejar un resultado revisable antes de abrir revisión o enviar cambios al remoto.
