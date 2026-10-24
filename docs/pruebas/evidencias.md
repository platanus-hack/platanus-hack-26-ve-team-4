# Evidencias ejecutadas y cómo revisarlas

Esta página registra resultados ya obtenidos el 24 de octubre de 2026, antes de esta revisión documental. No implica que se hayan repetido llamadas LIVE al editar los documentos. Para los comandos habituales ver [guía de pruebas](./README.md), [pruebas por dominio](./por-dominio.md) y [evaluación](../evaluacion.md).

## Inventario preservado

Todos los JSON siguientes están en [artifacts/core-evaluation](../../artifacts/core-evaluation/) y tienen un archivo `.json.sha256` contiguo. Contienen datos sintéticos y evidencias de operación; no son una proyección para la audiencia.

| Artefacto | Resultado y alcance |
| --- | --- |
| [demo-270.json](../../artifacts/core-evaluation/demo-270.json) | Comparación completa DEMO de 270 ejecuciones, 732 llamadas de origen `simulated`. Corresponde a los fixtures anteriores a los comercios de Yummy (#24), el origen y destino de entrega (#29) y los nombres de clientes (#34): su `fixture_hash` ya no coincide con `fixture_hash()` actual. |
| [demo-270-2026-10-24-yummy.json](../../artifacts/core-evaluation/demo-270-2026-10-24-yummy.json) | La misma comparación DEMO repetida sobre los fixtures actuales, en `63e1096` con árbol limpio: 270 ejecuciones, 732 llamadas `simulated`, cifras iguales a `demo-270.json`. |
| [live-p0.json](../../artifacts/core-evaluation/live-p0.json) | Once comprobaciones LIVE aprobadas, 93 llamadas reales y cinco roles. |
| [live-p0-initial-timeout.json](../../artifacts/core-evaluation/live-p0-initial-timeout.json) | Primer ensayo: P0 verificado, pero timeout del límite global de campaña; `passed=false` preservado. |
| [fleet-demo.json](../../artifacts/core-evaluation/fleet-demo.json) | Cuatro runs del recorrido original de la flota en DEMO. |
| [fleet-demo-checks.json](../../artifacts/core-evaluation/fleet-demo-checks.json) | CLI con código 0, `report_ok=true` y 22/22 comprobaciones. |
| [commit-map.json](../../artifacts/core-evaluation/commit-map.json) | Referencias originales y revisadas de la historia local, hashes de árbol y comprobaciones de los commits intermedios. |

## Comparación amplia simulada

La evaluación `eval-0b4b840a0609` comparó políticas 0 y 3 con `demo-rule-engine-v1`, sin honeypot. Cada caso utilizó una sesión y base de validación limpias. Las herramientas, efectos SQLite, gateway y oráculos fueron los de la aplicación; el proveedor de lenguaje fue determinista y simulado.

| Medida | Política 0 | Política 3 |
| --- | --- | --- |
| Ejecuciones adversarias evaluables | 90 | 90 |
| Violaciones confirmadas | 90 | 0 |
| Intentos impedidos por un control | 0 | 90 |
| Tareas legítimas correctas | 45/45 | 45/45 |
| Inconclusos | 0 | 0 |
| Familias | 6 | 6 |

Las tres repeticiones completaron 15/15 tareas legítimas por versión y repetición. Las 732 llamadas no contienen uso medido; `total_cost_usd` es `null`. No presentar esas tasas como eficacia de un LLM real ni el coste desconocido como facturación cero.

La partición reservada está publicada y puede haberse usado al validar controles. No debe tratarse como un conjunto nuevo independiente en un futuro ajuste.

### Repetición sobre los fixtures actuales

`demo-270.json` se generó antes de que los pedidos tuvieran comercio de Yummy, dirección de retiro y entrega, y nombre del cliente. Su `fixture_hash` (`26095a2e…6d5fd0`) ya no coincide con el de los datos actuales. La evaluación `eval-4f9375e1912d` repite la comparación sobre `63e10960319fa6beef292b717a4dc2e251e4edb5`, con `working_tree_dirty=false` y `fixture_hash` `0fe4044f383bdc0606fa07bd9983b52746232a8ce046ae72fb99abcf2d1aebf9`, el mismo que devuelve `fixture_hash()` en ese commit. La suite (`9a4a0cd3…457f91`) y los hashes de las políticas 0 y 3 son idénticos a los de la evaluación anterior.

| Medida | `demo-270.json` | `demo-270-2026-10-24-yummy.json` |
| --- | --- | --- |
| Violaciones, política 0 → 3 | 90/90 → 0/90 | 90/90 → 0/90 |
| Intentos impedidos en la política 3 | 90 | 90 |
| Tareas legítimas correctas por versión | 45/45 | 45/45 |
| Inconclusos | 0 | 0 |
| Llamadas `simulated` | 732 | 732 |
| Resultado por caso, versión y repetición | — | Idéntico en las 270 ejecuciones |
| `state_hash` y texto de `reply` | — | No comparables entre corridas: ver el párrafo siguiente |

Los datos nuevos no cambiaron ninguna cifra. Los seis pedidos conservan identificador, dueño, total, estado y saldo reembolsado. Cambian los artículos y el dominio del correo, y se agregan el comercio, las direcciones de retiro y entrega y el nombre del cliente. Ningún oráculo ni expectativa de utilidad depende de esos campos. Los casos usan los mismos pedidos, dueños e importes. El `state_hash` no sirve para comparar corridas: incluye los canarios aleatorios de cada pedido y el `operation_id` de cada reembolso, así que cambia en cada ejecución aunque los fixtures sean los mismos (en los dos JSON, las tres repeticiones de cada caso tienen hashes distintos). El texto de `reply` difiere en 201 de las 270 ejecuciones: en 63 solo por identificadores y canarios aleatorios, y en 138 porque la salida de `get_order` ahora trae el nombre, el comercio y las direcciones. La latencia por ejecución no se compara entre los dos JSON, porque depende de la máquina: en la repetición fue de 0,10 a 0,56 s, con mediana de 0,18 s (0,19 s en la política 0 y 0,18 s en la 3), frente a 0,03 a 0,13 s en `demo-270.json`. Se descartó una corrida previa porque el reloj de Windows estaba desincronizado y producía latencias de ±222 s.

Se generó con el procedimiento HTTP de [evaluación](../evaluacion.md#9-ejecutar-y-exportar-la-comparación), en un contenedor `python:3.12-slim-bookworm` con un clon limpio del commit, SQLite, `AGENT_ZERO_LLM_MODE=demo`, sin `.env` y con secretos aleatorios de un solo uso. La campaña de seis intentos activó la política 3 con los tres controles del catálogo. Dos variables difieren de `.env.example`, y conviene fijarlas para repetir la comparación:

- `AGENT_ZERO_ARENA_FLOW_SYNTHESIS=false`. Con `true`, la campaña mitiga pedido y reembolso con `flow_rules` sintetizadas y la versión activa no llega a tener los tres controles del catálogo, así que la espera de la sección 9 termina con error a los 300 s.
- `AGENT_ZERO_GATEWAY_RATE_LIMIT_PER_MINUTE=10000`, el mismo valor que fija `scripts/verify_live.py`. Con el valor por defecto, 60 por minuto por agente, las 270 ejecuciones comparten `soporte-tienda` y el gateway deniega herramientas con `rate_limited`. Esas denegaciones no son defensas de la política: convierten violaciones y tareas útiles en `not_achieved`. El límite global por agente ya figura como pendiente en la [bitácora de la traza v2](../bitacora/2026-10-24-traza-herramientas-v2.md).

## Ensayo completo LIVE

[live-p0.json](../../artifacts/core-evaluation/live-p0.json) registra `passed=true`, sin errores, con `claude-haiku-5-5`. Se comprobaron:

1. Consulta propia útil con herramienta completada y violación base de pedido ajeno.
2. Candidato con ocho casos aprobados, activación y replay en entorno protegido impedido con denegación de herramienta.
3. Tres turnos en señuelo, incluido un pedido explícito de volver al soporte real, conservando aislamiento.
4. Campaña de seis mutaciones LLM y seis casos de las seis familias.
5. Reversión de la política 3 a su padre 2; reset a 0 con archivo `archive-c0a2e83ddc81` y evidencia conservada.

| Rol | Llamadas LIVE |
| --- | --- |
| `victim` | 75 |
| `decoy` | 6 |
| `prober` | 6 |
| `analyzer` | 3 |
| `patcher` | 3 |
| Total | 93 |

El coste estimado fue **0,0101596 USD**, calculado con tokens reales y las tarifas configuradas en el proyecto. No es una factura del proveedor. El verificador configuró 200 llamadas instrumentadas y un presupuesto diario estimado de 0,50 USD, respetando un límite monetario configurado menor si existía. El límite se comprueba antes de llamadas posteriores; no es un bloqueo de facturación de la cuenta ni una reserva del coste máximo de peticiones simultáneas. Un reintento HTTP interno tampoco equivale a otra reserva de llamada instrumentada; detalles en [LLM](../dominio/llm.md).

El entorno de ese ensayo no tenía DNS operativo. Se usó el flag explícito `--diagnostic-doh`, limitado al proceso y a `api.anthropic.com`, con HTTPS y verificación TLS del nombre conservada. El JSON guarda ese diagnóstico. No se modificaron DNS del sistema ni el comportamiento de la aplicación.

El primer intento guardado excedió el plazo global de 60 segundos para seis casos y sus validaciones. Conserva sus 92 llamadas y `passed=false`; el verificador final espera por caso. No sumar su resultado parcial como un éxito completo ni borrar ese antecedente al repetir el ejemplo.

## Recorrido de flota y controles locales

El recorrido DEMO aprobó 22/22 comprobaciones: publicación/aprobación, ejecución con espera y reanudación, memoria entre runs, denegación por scope, bloqueo de inyección, revocación, traza y auditoría. [fleet-demo-checks.json](../../artifacts/core-evaluation/fleet-demo-checks.json) guarda el comando, salida y cada check; [fleet-demo.json](../../artifacts/core-evaluation/fleet-demo.json) conserva los cuatro runs.

La verificación global de código previa aprobó **860 pruebas backend**, con dos pruebas LIVE opcionales omitidas y ninguna advertencia, y **47 pruebas frontend**. Ruff, formato, mypy, Biome, TypeScript, build frontend, construcción de ambas imágenes y smoke HTTP completo en contenedores pasaron. El smoke recorrió utilidad, ataque, ocho validaciones, activación, replay, revelación y reset archivado.

Las pruebas frontend fueron de DOM y los contenedores se verificaron por HTTP. No se realizó revisión visual en navegador ni prueba pública desde otro dispositivo. No hay evidencia publicada de carga real con diez participantes concurrentes ni comparación amplia LIVE.

## Integridad y procedencia

Desde la raíz, sin servidor ni clave de IA:

```bash
(cd artifacts/core-evaluation && shasum -a 256 -c *.sha256)
```

En Linux puede utilizarse `sha256sum -c *.sha256` dentro de la misma carpeta. Los seis hashes fueron cotejados contra sus JSON durante esta revisión documental. El séptimo, de la repetición sobre los fixtures actuales, se cotejó al guardarlo.

| JSON | SHA-256 |
| --- | --- |
| `demo-270.json` | `6aaa2f7f9008fb1c692f7d6519439d49c058113bcda4817bce71245db2f1840f` |
| `live-p0.json` | `34ffcfe76681250e5010260a9f93987e6549044207c51add53709b149ed9c92e` |
| `live-p0-initial-timeout.json` | `92bbdcdf131f7b5409df86466204e3d81e6237bf8793761674e1e93e75400ada` |
| `fleet-demo.json` | `1ec4c403e529c31ec9a269160278e51a57da7808e92697a850249b742e512eb9` |
| `fleet-demo-checks.json` | `ce4739fd199d46ae405a18027cae7202cb156b5c1c1ef6dbf4f7d690fc60c2a8` |
| `commit-map.json` | `8d473a972fbbdfc102956ec1efc0a8121b396fc0b340790edb28c21c1ca21943` |
| `demo-270-2026-10-24-yummy.json` | `ed6623b94a80839a5d6f5d712a19dbf0190da7128ec4444cfc4568197ed27459` |

La comparación DEMO registró originalmente `aed15dd4f7ea21ccabd5886a05bcdfd2d5d5fd9d` con árbol de trabajo modificado. La historia local se reorganizó antes de publicarse: el mapa identifica `20f97a771f309c0380b0a244d112a56ba870c926` con el mismo árbol Git. La referencia original `cc35d0661eb6439fa6e416f1c871385a4a339362` corresponde a `568f642f6658d18d10ae944b36db081873cad6c9`, también con árbol idéntico.

Los JSON conservan sus referencias originales. Los hashes de suite, fixtures y políticas permiten revisar insumos concretos; `working_tree_dirty=true` declara que un commit por sí solo no captura todos los archivos del momento del ensayo. No reescribir los metadatos históricos para hacerlos parecer ejecutados en un commit posterior limpio.

## Cómo repetir sin perder la referencia

Para la comparación DEMO, preparar otra ronda, esperar la política verificada y seguir [el procedimiento de evaluación](../evaluacion.md#9-ejecutar-y-exportar-la-comparación). Elegir un nuevo archivo de salida, por ejemplo `mi-comparacion.json`, y conservar su `.sha256`. La versión activa puede diferir de 3. Fijar en `.env` (no basta con exportarlas en la shell) `AGENT_ZERO_ARENA_FLOW_SYNTHESIS=false` y `AGENT_ZERO_GATEWAY_RATE_LIMIT_PER_MINUTE=10000`, como en la [repetición sobre los fixtures actuales](#repetición-sobre-los-fixtures-actuales).

Para el recorrido original usar [prueba de la flota](../prueba-flota.md), con `FLEET_MODE=demo` si no se desean llamadas reales. Para el ensayo LIVE, desde la raíz y con la clave local configurada:

```bash
cd backend
uv run python scripts/verify_live.py --budget-usd 0.50 \
  --output ../artifacts/core-evaluation/mi-ensayo-live.json
```

Añadir `--diagnostic-doh` sólo si el entorno necesita ese diagnóstico de resolución. El script usa datos temporales, produce JSON/SHA-256 y termina con código distinto de cero si falla una comprobación. La salida registra resultados observados, incluido un fallo; no fuerza una historia de éxito. La clave y los tokens no deben copiarse a documentos, comandos compartidos ni artefactos.

Para una nueva entrega, conservar por separado el reporte de código (commit y comandos), el ensayo operativo LIVE y la evaluación amplia con sus denominadores. El estado y los próximos trabajos se mantienen en [continuidad](../continuidad.md).
