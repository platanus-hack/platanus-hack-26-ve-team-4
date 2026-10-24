# Prueba HTTP de la flota

Este recorrido ejecuta la aplicación y sus siete componentes de plataforma: Registry, Runtime, Memory Bank, Identity, Gateway, Armor y Observability. Es distinto del ciclo de parches de la arena: utiliza `support_conversation` y el manifiesto `soporte-tienda` **1.0.0**, cuyos permisos niegan reembolsos. La arena usa manifiestos **2.2.0** y otro handler.

El punto de entrada es [walkthrough/__main__.py](../backend/src/agent_zero/walkthrough/__main__.py). [test_walkthrough.py](../backend/tests/walkthrough/test_walkthrough.py) ejecuta el mismo recorrido con modelo guionado; [evidencias](./pruebas/evidencias.md) conserva el ensayo DEMO aprobado de **22/22 comprobaciones**. Esta guía no requiere llamadas reales por defecto.

## Preparación

Desde la raíz, instalar dependencias y conservar cualquier configuración existente:

```bash
test -f .env || cp .env.example .env
make install
```

El modo DEMO funciona sin clave de IA. El servidor y el cliente deben usar el mismo `AGENT_ZERO_OPERATOR_SECRET` de `.env`; los targets Make lo cargan. `fleet-server` fuerza `AGENT_ZERO_OTEL_EXPORTER=memory`, necesario para consultar trazas por HTTP.

Usar **un directorio de datos nuevo por ensayo**. El recorrido publica IDs/versiones conocidos, usa el cliente `cust-ana`, acumula memoria y crea y revoca un agente temporal. Que algunas publicaciones acepten 409 no equivale a empezar de cero. El reset de arena conserva registro, revocaciones, memoria de plataforma y runs ajenos a la ronda; no limpia este recorrido.

## Ensayo DEMO en dos terminales

En la primera terminal, desde la raíz:

```bash
export FLEET_DATA="$(mktemp -d "${TMPDIR:-/tmp}/agent-zero-fleet-demo.XXXXXX")"
printf 'Copiar en la segunda terminal: export FLEET_DATA=%q\n' "$FLEET_DATA"
make fleet-server FLEET_MODE=demo FLEET_PORT=8000 FLEET_DATA="$FLEET_DATA"
```

La ruta impresa es absoluta y el directorio ya existe. En la segunda terminal, también desde la raíz, copiar primero la línea `export FLEET_DATA=...` que imprimió el servidor y ejecutar:

```bash
make fleet-walkthrough FLEET_PORT=8000 FLEET_DATA="$FLEET_DATA"
```

El CLI espera hasta completar los cuatro runs, imprime los 22 checks y guarda `$FLEET_DATA/recorrido.json`. Código de salida 0 significa que `Report.ok` es verdadero; 1 indica un check fallido. Un fallo de conexión o timeout también termina el proceso con error.

No lanzar el recorrido mientras otro servicio ocupe el puerto. Para cambiarlo, pasar el mismo `FLEET_PORT` a ambos targets. Al terminar, detener el servidor con Ctrl-C y conservar el directorio como evidencia. Para repetir, crear otro directorio; no borrar ni reutilizar el del ensayo anterior como supuesto reset.

| Variable Make | Valor por defecto | Precaución |
| --- | --- | --- |
| `FLEET_MODE` | `live` | Especificar `demo` para el ensayo sin proveedor. |
| `FLEET_PORT` | `8000` | Debe coincidir entre servidor y CLI. |
| `FLEET_DATA` | `./data/fleet` | Make cambia a `backend/`: las rutas relativas se interpretan desde allí. |

Para ajustar espera y archivo, el CLI acepta `--follow-up-seconds`, `--timeout`, `--base-url` y `--save`. Si se usa directamente, cargar `.env` desde la raíz antes de cambiar de carpeta. `--save` no crea la carpeta padre: debe existir; la receta con `mktemp -d` cumple ese requisito.

```bash
set -a
. ./.env
set +a
cd backend
uv run python -m agent_zero.walkthrough --base-url http://localhost:8000 \
  --follow-up-seconds 1 --timeout 90 --save "$FLEET_DATA/recorrido.json"
```

## Qué verifica

| Área | Evidencia esperada |
| --- | --- |
| Plataforma | `/health` responde y `/api/fleet/status` enumera handler y herramientas. |
| Registry | Publicar/aprobar `soporte-tienda@1.0.0`, descubrir por capacidad y verificar el hash del manifiesto. |
| Armor de publicación | Un manifiesto con herramienta envenenada recibe 422. |
| Runtime | Un run responde, pasa por `waiting` y reanuda hasta `succeeded`, conservando checkpoint. |
| Modelo | La respuesta del primer contacto no está vacía; en DEMO es simulada. |
| PII | El pedido visto por el agente contiene `[EMAIL]` en lugar del correo sintético. |
| Memoria | El segundo contacto recuerda al menos una interacción anterior del cliente. |
| Gateway | La solicitud de reembolso queda denegada; no pertenece a los permisos de este manifiesto. |
| Armor de entrada | La inyección termina bloqueada con `input_blocked`. |
| Identity | El agente temporal revocado no ejecuta pasos y su run termina `failed`. |
| Observability | Run, pasos, gateway y modelo comparten traza; atributos sin el correo sintético. |
| Auditoría y límite | La cadena verifica, contiene denegaciones y el gasto registrado no supera el tope configurado. |

El resultado anterior se conserva en [fleet-demo-checks.json](../artifacts/core-evaluation/fleet-demo-checks.json), con `cli_exit_code=0`, `report_ok=true` y 22 checks; [fleet-demo.json](../artifacts/core-evaluation/fleet-demo.json) contiene los cuatro runs. Sus hashes están junto a los archivos. La evidencia DEMO prueba integración de plataforma, no eficacia de un LLM real.

## Variantes LIVE, record y replay

Para LIVE, configurar `AGENT_ZERO_LLM_API_KEY`, modelo y presupuestos en el `.env` propio. Repetir la preparación con otro directorio y `FLEET_MODE=live`. Primer y segundo contacto normalmente realizan dos llamadas de respuesta, pero errores/reintentos o actividad concurrente pueden incrementar el consumo. Consultar el ledger; no asumir un coste fijo por recorrido.

`record` llama al proveedor real y escribe una cassette, por defecto en `$FLEET_DATA/llm/cassette.jsonl`. Iniciar el servidor como en la receta anterior cambiando sólo `FLEET_MODE=record`; ejecutar el CLI una vez y detenerlo. Si `.env` define `AGENT_ZERO_LLM_CASSETTE_PATH`, revisar esa ruta antes de usar la receta por defecto siguiente.

Para reproducir, en la primera terminal del ensayo grabado, conservar la cassette y preparar **otra base de plataforma**:

```bash
export RECORDED_CASSETTE="$FLEET_DATA/llm/cassette.jsonl"
export FLEET_DATA="$(mktemp -d "${TMPDIR:-/tmp}/agent-zero-fleet-replay.XXXXXX")"
mkdir -p "$FLEET_DATA/llm"
cp "$RECORDED_CASSETTE" "$FLEET_DATA/llm/cassette.jsonl"
printf 'Copiar en la segunda terminal: export FLEET_DATA=%q\n' "$FLEET_DATA"
make fleet-server FLEET_MODE=replay FLEET_PORT=8000 FLEET_DATA="$FLEET_DATA"
```

Copiar la nueva línea de `FLEET_DATA` en la segunda terminal y ejecutar `make fleet-walkthrough` con ese directorio. El proveedor no recibe llamadas nuevas y el origen es `replayed`. La cassette consume entradas por rol/tipo/DTO en orden; no verifica que el prompt sea idéntico. No reutilizarla para atribuir resultados a entradas distintas. Reiniciar recarga sus colas, pero para otro ensayo limpio también se necesita nueva base.

El coste LIVE estimado se reconstruye desde el ledger de esa carpeta. Cada directorio tiene su propio ledger; cambiarlo no conserva un presupuesto monetario global. Los contadores generales de llamadas/tokens son de proceso. Detalles en [LLM](./dominio/llm.md).

## Inspección HTTP

Con el servidor activo y `.env` cargado en una terminal desde la raíz:

```bash
set -a
. ./.env
set +a
export FLEET_API=http://localhost:8000
curl --fail --silent --show-error -H "X-Operator-Secret: $AGENT_ZERO_OPERATOR_SECRET" \
  "$FLEET_API/api/fleet/status"
curl --fail --silent --show-error -H "X-Operator-Secret: $AGENT_ZERO_OPERATOR_SECRET" \
  "$FLEET_API/api/fleet/audit?limit=20"
```

Para consultar un run, tomar su `run_id` de `recorrido.json` y usar `GET /api/runtime/runs/{id}` y `GET /api/fleet/runs/{id}/trace`, con el mismo encabezado. El JSON incluye `statuses_seen`; no almacena las credenciales del cliente.

## Pruebas automatizadas y diagnóstico

Desde la raíz, en una terminal de pruebas que no exporte configuración LIVE:

```bash
cd backend
uv run pytest tests/walkthrough tests/fleet -q
```

La suite prueba el cliente HTTP, el cálculo de `Report.ok`, el recorrido completo guionado, registro de componentes, admisión, identidad, memoria y trazas. Para el detalle por dominio y la suite global previa de 860 pruebas, ver [pruebas](./pruebas/README.md) y [matriz](./pruebas/por-dominio.md).

| Síntoma | Comprobación |
| --- | --- |
| 401 | Servidor y CLI deben cargar el mismo secreto; un token de audiencia no autoriza flota. |
| 409 al pedir traza | Usar exportador `memory`; con `otlp` consultar el colector. |
| 404 de traza tras reiniciar | Los spans `memory` son del proceso; ejecutar y exportar antes de detenerlo. |
| `FileNotFoundError` al guardar | Crear el padre de `--save`; revisar la ruta relativa a `backend/`. |
| Check de memoria o manifiesto inesperado | Confirmar directorio nuevo y que el CLI apunta a ese servidor, no a otra arena. |
| Run `failed` por límite/proveedor | Inspeccionar `failure_reason`, status y ledger; no contarlo como éxito de seguridad. |
| Cassette agotada | Usar una grabación completa compatible; sus colas se consumen durante el proceso. |
| `offline` sin respuesta | No instala DEMO automáticamente; requiere un guion inyectado. Usar `demo` para este recorrido. |

Para continuar la implementación, ver [continuidad](./continuidad.md); para el ciclo de ataque/parche usar [núcleo](./nucleo.md), no confundir sus manifiestos ni su reset con este recorrido de plataforma.
