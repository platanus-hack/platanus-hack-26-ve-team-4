# Arquitectura propuesta de Agent Zero

Estado: referencia de diseño del MVP. El ciclo P0 y parte de la arena ya están implementados; ver [núcleo implementado](./nucleo.md) para los contratos vigentes, pruebas y brechas.

## 1. Decisiones de alcance

El MVP se plantea como un monolito modular: una API Python con FastAPI, procesos de trabajo asíncronos en el mismo despliegue, SQLite para persistencia y una interfaz React con TypeScript. Los eventos se transmitirían por SSE, suficiente para actualizar una arena que envía acciones mediante HTTP. Son decisiones propuestas, sin dependencias instaladas ni versiones fijadas todavía.

Un adaptador desacopla al proveedor de LLM. La víctima, el mutador y el analizador tienen instrucciones, contextos y presupuestos separados. Pueden usar el mismo proveedor, pero no comparten memoria. Los secretos del proveedor solo existen en el servidor.

La base protegida y el honeypot utilizan archivos SQLite distintos y adaptadores sin referencias cruzadas. La evaluación de parches utiliza una tercera copia desechable de los datos semilla. El término «protegido» siempre se refiere al laboratorio con datos sintéticos.

## 2. Flujo general

```mermaid
flowchart TD
    U[Participantes por QR] --> API[API de la arena]
    P[Prober Agent] --> API
    API --> Q[Cola acotada por sesión]
    Q --> R[Policy Engine / Honeypot Router]
    R -->|Permitir| V[Agente víctima]
    R -->|Desviar| H[Agente señuelo]
    R -->|Bloquear| RESP[Respuesta controlada]
    V --> G[Validadores de herramientas y salida]
    G --> DB[(Datos sintéticos protegidos)]
    H --> HD[(Datos y herramientas señuelo)]
    G --> E[Registro de eventos]
    H --> E
    RESP --> E
    E --> A[Vulnerability Analyzer]
    A --> F[Hallazgo con evidencia]
    F --> PG[Patch Generator]
    PG --> T[Pruebas en copia aislada]
    T -->|Aprobado| PV[Registro de políticas versionadas]
    PV --> R
    PV --> G
    E --> SSE[Eventos SSE]
    SSE --> UI[Panel público y panel de operación]
```

La flecha hacia los datos protegidos siempre pasa por un adaptador. No se entrega al modelo una conexión SQL, un intérprete ni un cliente HTTP genérico. El servidor decide identidad, entorno y permisos para cada ejecución.

## 3. Escenario y límites de confianza

La tienda ficticia contiene clientes, pedidos, reglas de reembolso y documentos de soporte. La identidad autenticada se fija al crear la sesión. El cuerpo del mensaje, los documentos recuperados, la memoria y las salidas del modelo son contenido no confiable.

| Límite | Riesgo | Control previsto |
| --- | --- | --- |
| Navegador → API | Suplantación de sesión o envío masivo. | Token firmado, alias sin identidad real, tamaño y frecuencia acotados. |
| Documento → contexto | Una fuente intenta convertirse en instrucción. | Procedencia explícita, separación de contenido y reglas de ejecución fuera del LLM. |
| Modelo → herramienta | Argumentos fuera de permisos. | Esquema, lista de herramientas y autorización del lado del servidor. |
| Memoria → siguiente turno | Persistencia de una falsa excepción. | Campos permitidos, ámbito por sesión, procedencia y cuarentena. |
| Hallazgo → política | El atacante contamina la defensa. | Esquema declarativo cerrado, pruebas y reglas base inmutables. |
| Panel público → operación | Acceso a controles o trazas internas. | Autorización de servidor; ocultar componentes visuales no basta. |
| Honeypot → entorno protegido | Escape o mezcla de datos. | Adaptadores y archivos separados; decisión de ruta exclusivamente del servidor. |

Los atacantes no pueden modificar objetivos, verificadores, suites reservadas ni permisos del generador. La arena tampoco acepta una URL arbitraria como objetivo del Prober.

## 4. Prober Agent

**Entrada:** perfil del escenario, plantillas, familias habilitadas, historial de resultados y presupuesto restante.

**Proceso:** elegir un objetivo, generar una variante, deduplicar, ejecutar contra una sesión aislada y priorizar resultados novedosos. El LLM redacta mutaciones; el planificador determina destinos y límites.

**Salida:** un `AttackCase` con `case_id`, `family`, `surface`, `objective_id`, `messages`, `fixture_id`, `seed`, `parent_case_id` y `origin` (`autonomous` o `audience`).

Las superficies iniciales son mensaje directo, documento recuperado, resultado simulado de herramienta y memoria entre turnos. La inyección en herramientas afecta el texto devuelto por un adaptador de prueba, sin instalar servidores o dependencias suministrados por participantes.

Configuración inicial propuesta: hasta cuatro turnos por caso, dos repeticiones por variante, una cola global con cupo para la audiencia y tope de llamadas y tokens por campaña. El valor exacto de concurrencia se fijará tras medir la API del proveedor. Al agotarse el presupuesto, se detiene la generación y se conserva la evidencia existente.

## 5. Vulnerability Analyzer

El analizador combina tres capas:

1. **Verificación determinista:** compara herramientas, salidas y cambios de estado con invariantes y marcadores sintéticos.
2. **Clasificación semántica:** identifica familia, intención y una causa probable usando una salida estructurada.
3. **Consolidación:** agrupa intentos relacionados en un hallazgo reproducible, con referencias a eventos.

El resultado tiene campos independientes para `attack_family`, `violation_status`, `route` y `confidence`. La ruta `honeypot` nunca equivale a una violación confirmada. Los errores de infraestructura producen `inconclusive`, incluso si el clasificador cree que el ataque era peligroso.

Un hallazgo incluye precondiciones, objetivo violado, versión afectada, pasos de reproducción, eventos de evidencia, hipótesis de causa y alcance observado. Su identificador permanece estable para comparar revisiones. Una nueva redacción del mismo fallo aumenta evidencia, sin inflar el número de vulnerabilidades.

El analizador recibe citas delimitadas del ataque y no tiene permiso para cambiar políticas o ejecutar herramientas de negocio. La explicación del LLM no se considera una prueba por sí sola.

## 6. Patch Generator y activación en caliente

El generador selecciona controles de un catálogo implementado previamente: comprobar titularidad, limitar importes, validar destinos, restringir escrituras de memoria, exigir procedencia o activar cuarentena. Un refuerzo del prompt puede complementar esos controles, pero no sustituye la autorización en herramientas.

Ejemplo de contrato de una política candidata:

```json
{
  "policy_id": "policy-0007",
  "parent_version": 6,
  "finding_ids": ["finding-0012"],
  "scope": "get_order",
  "rules": [
    {
      "validator": "order_belongs_to_session_customer",
      "on_failure": "block"
    }
  ],
  "reason": "La consulta de un pedido debe respetar la identidad de la sesión",
  "status": "candidate"
}
```

Los nombres técnicos son identificadores del contrato; las explicaciones para personas se muestran en español. El candidato no puede desactivar la separación de entornos, habilitar herramientas nuevas, ampliar privilegios ni cambiar las condiciones de éxito.

### Estados de una política

`candidate → validating → active → superseded`.

Una validación fallida lleva a `rejected`. Una política activa que cause regresiones pasa a `rolled_back`, restaurando una versión válida y verificada. Se conserva un motivo y un evento para cada transición.

### Secuencia de validación

1. Validar el esquema y la lista de controles permitidos.
2. Comprobar que la versión base sigue siendo la activa; si cambió, regenerar o revalidar.
3. Reproducir el caso original sobre una copia de fixtures y memoria.
4. Ejecutar variantes reservadas y tareas legítimas sin revelarlas al generador.
5. Exigir cero violaciones en los casos críticos y ninguna regresión en la suite mínima de utilidad.
6. Registrar resultados, hash del contenido, versión padre y duración.
7. Activar mediante una actualización atómica del puntero de política.

Solo se valida y activa un candidato a la vez en el MVP. La activación en caliente afecta nuevas ejecuciones. Cada ejecución conserva su versión inicial hasta terminar; antes de activar se drenan las operaciones en curso con un plazo acotado. Si no se vacían, se pospone la activación y se muestra el estado pendiente. Así se evita evaluar una acción bajo dos versiones distintas.

Una política nueva no revierte efectos pasados. Después de una contaminación de memoria se debe poner en cuarentena el estado afectado y repetir la prueba con fixtures limpios. El tiempo de drenaje y validación forma parte del tiempo total de parcheo.

## 7. Policy Engine y Honeypot Router

El motor ofrece tres decisiones: `allow`, `block` y `divert`. Su orden de evaluación propuesto es comprobar sesión y entorno, aplicar controles obligatorios, evaluar señales semánticas y validar cada llamada de herramienta y la salida final.

La clasificación semántica puede enviar a cuarentena o al señuelo; nunca autoriza una acción que un control determinista rechaza. La primera versión puede usar señales conocidas para el desvío y marcar con baja confianza los casos ambiguos.

El desvío crea una sesión señuelo con memoria y datos propios. Se copia únicamente el contenido permitido para reproducir la interacción, sin credenciales ni datos protegidos. La ruta queda fijada para el resto de la sesión; no se retorna al entorno protegido arrastrando memoria del honeypot.

Los marcadores del señuelo permiten probar que una respuesta aparente vino de ese entorno. La etiqueta interna se conserva aunque se oculte temporalmente en la vista pública. La API pública recibe una proyección sin campos de operación, en lugar de enviar secretos y ocultarlos con CSS.

## 8. Herramientas del agente víctima

| Herramienta | Entrada del modelo | Datos fijados por el servidor | Regla verificable |
| --- | --- | --- | --- |
| `get_order` | `order_id` | `session_customer_id`, entorno. | El pedido pertenece al cliente autenticado. |
| `request_refund` | `order_id`, `amount`, motivo. | Identidad, límite comercial, entorno. | Pedido propio, importe positivo y dentro del límite; escritura idempotente. |
| `search_knowledge` | Consulta de texto. | Colección del escenario y ámbito. | Devuelve fragmentos con procedencia, nunca permisos nuevos. |
| `save_memory` | Clave y valor. | Sesión, turno, entorno y procedencia. | Solo preferencias permitidas; objetivos y autorizaciones son inmutables. |

La base vulnerable usa un adaptador de laboratorio con una omisión identificada. La versión reforzada habilita el control correspondiente. Esa excepción no afecta el aislamiento global, los presupuestos ni los secretos de API.

## 9. Modelo de datos y eventos

| Entidad | Campos principales | Propósito |
| --- | --- | --- |
| `Session` | ID, alias, identidad sintética, ruta, fechas. | Separar participantes y entornos. |
| `Attempt` | ID, origen, caso, sesión, versión, estado. | Contabilizar cada ejecución. |
| `TraceEvent` | ID monotónico, intento, tipo, fecha, datos. | Reconstruir decisiones y acciones. |
| `Finding` | ID, objetivo, evidencia, causa probable, estado. | Agrupar una vulnerabilidad conocida. |
| `PolicyVersion` | ID, padre, reglas, hash, validación, estado. | Explicar y revertir defensas. |
| `EvaluationRun` | Fixtures, casos, versiones, resultados, coste. | Comparar antes y después. |
| `MemoryEntry` | Sesión, clave, valor, procedencia, cuarentena. | Probar persistencia y su contención. |

Eventos mínimos: `attempt_queued`, `attempt_started`, `tool_proposed`, `tool_denied`, `tool_completed`, `route_changed`, `attempt_evaluated`, `finding_opened`, `patch_proposed`, `patch_validated`, `policy_activated` y `policy_rolled_back`.

Cada evento lleva `attempt_id`, `session_id`, `policy_version`, `timestamp` y `visibility`. Las trazas registran acciones observables y motivos breves de decisión; no requieren almacenar razonamiento interno del modelo. Los marcadores protegidos se redactan al publicar la vista pública.

SSE utiliza identificadores para reanudar después de una desconexión. El navegador deduplica eventos y el marcador se calcula en el servidor a partir de resultados persistidos; reconectarse no multiplica puntos.

## 10. API propuesta

| Método y ruta | Acceso | Función |
| --- | --- | --- |
| `POST /api/sessions` | Público con cupo. | Crear sesión y alias de participante. |
| `POST /api/attempts` | Sesión. | Encolar un intento con clave de idempotencia. |
| `GET /api/attempts/{id}` | Propietario u operación. | Consultar el resultado permitido para esa vista. |
| `GET /api/arena/events` | Público. | Recibir eventos sanitizados por SSE. |
| `GET /api/leaderboard` | Público. | Clasificación provisional o final según fase. |
| `GET /api/operator/findings` | Operación. | Consultar evidencia y estado de hallazgos. |
| `POST /api/operator/campaigns` | Operación. | Iniciar el Prober con presupuesto. |
| `POST /api/operator/policies/{id}/rollback` | Operación. | Revertir una política a su padre validado. |
| `POST /api/operator/reveal` | Operación. | Publicar el resultado real de los señuelos. |
| `POST /api/operator/reset` | Operación. | Cerrar sesiones y restaurar fixtures para otro ensayo. |
| `GET /health` | Público, respuesta mínima. | Comprobar que el servicio responde. |

El modo automático de laboratorio puede activar candidatos aprobados sin intervención. Los controles de operación requieren un secreto de servidor independiente de los tokens de audiencia. No se habilita una ruta pública para redactar o activar políticas.

## 11. Operación, fallos y configuración

Configuración prevista: proveedor y modelo, secreto de API, secreto de operación, rutas de las tres bases, presupuesto de tokens, concurrencia máxima y duración de campaña. Los valores reales irían en un archivo local excluido de Git; un futuro `.env.example` contendría únicamente nombres y ejemplos ficticios.

Ante una caída del LLM, el intento queda inconcluso y la cola devuelve un estado claro. Ante un candidato inválido, continúa la política anterior. Ante un fallo de autorización o de aislamiento, la acción se deniega. Si la cola se llena, la API aplica contrapresión y muestra espera, sin aceptar trabajo ilimitado.

Se propone iniciar con un mensaje cada tres segundos por sesión y entradas de hasta 4000 caracteres, ajustables tras la prueba de carga. Una campaña conserva cupos para la audiencia y para verificar parches. El operador puede pausar nuevas entradas sin perder los eventos ya registrados.

El panel mostrará llamadas, tokens, errores y latencias. El coste estimado será la suma de tokens de entrada y salida por el precio configurado del proveedor; se registrarán modelo y fecha de referencia, sin fijar tarifas de memoria.

### Capa de IA

El dominio `llm` concentra el acceso al modelo. Usa Strands Agents con su proveedor de Anthropic y el modelo `claude-haiku-5-5` para los cinco roles: víctima, señuelo, Prober, analizador y generador de parches. Cada rol tiene su propio esfuerzo (`low` en los roles de volumen, `medium` en análisis y parches), su tope de tokens de salida y una sustitución de modelo opcional por configuración. No se envían `temperature`, `top_p` ni `top_k`, porque la API los rechaza.

Cada llamada atraviesa una cadena fija:

| Capa | Responsabilidad |
| --- | --- |
| `InstrumentedModel` | Topes diarios, por sesión y por campaña; circuit breaker por rol; ledger JSONL con uso, costo, latencia, alcance y versión de prompt; detección de `stop_reason: "refusal"`. |
| `RetryingModel` | Reintentos con backoff exponencial y jitter, solo ante errores transitorios. El SDK va con `max_retries=0` para que no se reintente dos veces. |
| `RecordingModel` | En modo `record`, guarda cada llamada en una cassette para reproducirla después. |
| Proveedor | `AnthropicModel` en `live` y `record`, `CassetteModel` en `replay` y `PlaybackModel` guionado en `offline`. |

`offline` es el modo por defecto y no hace llamadas de red. `replay` reproduce una cassette grabada, de modo que la demo y las pruebas de evaluación se pueden repetir sin coste. `live` y `record` exigen clave y fallan al arrancar si falta.

Un rechazo del modelo (`ModelRefusedError`) es un resultado de primera clase: el intento se registra como `refused` y no cuenta como fallo del proveedor. Haiku 5.5 no tiene fallback de servidor, así que la decisión de qué hacer ante un rechazo queda en el dominio que llamó. Los errores transitorios agotados se convierten en `ModelLimitReachedError` con motivo `provider_unavailable`, y el intento queda inconcluso.

La salida estructurada usa el formato JSON nativo de la API. Si una validación de Pydantic falla, se repite la llamada con el error como turno de reparación, con un presupuesto acotado (uno por defecto). El caché de prompts se activa en el system prompt, las herramientas y el último turno.

El costo se calcula con la tabla de `pricing.py`: entrada, salida, lecturas y escrituras de caché, con la tarifa larga cuando el prompt supera 100.000 tokens. Las tarifas tienen fecha de referencia del 24 de octubre de 2026.

## 12. Estructura de implementación

El backend se organiza por dominios en `backend/src/agent_zero/`: `sessions`, `events`, `routing`, `victim`, `attempts`, `prober`, `analyzer`, `policies` y `llm`, con un núcleo `shared`. El frontend agrupa `participant`, `arena` y `operator` en `frontend/src/features/`. La estructura detallada, las convenciones y los comandos están en [desarrollo](./desarrollo.md).

Ya existen la creación de sesiones, el broker de eventos con SSE, la capa de IA, los contratos de `AttackCase`, hallazgos y políticas, y el ciclo de vida de políticas. Fixtures completos, el agente víctima, el Prober, el analizador y el honeypot siguen pendientes. Los criterios para aceptar el sistema se encuentran en [evaluación](./evaluacion.md).

## 13. Flota de agentes

La flota agrupa siete dominios independientes que `fleet.fleet_builder.build_fleet` conecta sobre una misma base y un mismo reloj. Los requisitos y sus pruebas están en [trazabilidad](./trazabilidad.md).

| Dominio | Papel en la flota |
| --- | --- |
| `registry` | Repositorio de agentes versionados con ciclo `draft → approved → deprecated`, descubrimiento por capacidad, departamento o etiqueta, hash sha256 del manifiesto y revisión de Model Armor al publicar. |
| `runtime` | Ejecución asíncrona con checkpoints, esperas de días (`resume_at`), reintentos, cancelación e idempotencia. El worker consulta la admisión antes de cada paso. |
| `memory_bank` | Memoria por agente y sujeto, cifrada en reposo, con TTL, procedencia y borrado por sujeto. Toda escritura pasa por Model Armor. |
| `identity` | Credenciales firmadas de corta duración con scopes, clearance y regiones; verificación en cada llamada y revocación por credencial o por agente. |
| `agent_gateway` | Punto único hacia herramientas y datos. Las herramientas se registran con clasificación, región y scope; los handlers del runtime solo reciben un `ToolAccess` ligado al gateway. |
| `armor` | Model Armor: bloquea inyección y envenenamiento, incluso ofuscados, y redacta PII. |
| `telemetry` | Spans OpenTelemetry con atributos saneados y registro de auditoría append-only encadenado por hash. |

La admisión (`RegistryAdmission`) une registro e identidad: solo emite una credencial para una versión aprobada y no revocada, y la guarda en una bóveda en memoria con la misma caducidad. Cada paso de un run la solicita de nuevo, de modo que tras semanas de espera el agente se vuelve a validar contra el registro. Los pasos reanudados continúan el `trace_id` del primer paso.

Una llamada a herramienta recorre siempre el mismo orden, y cada etapa es un span hijo del span `gateway.call_tool`:

1. Identidad: firma, caducidad, revocación y scope `tool:<nombre>`.
2. Política: versión aprobada, herramienta presente en el manifiesto, clasificación frente al nivel del agente, región frente al agente y a las regiones permitidas, y límite de tasa.
3. Model Armor sobre los argumentos: se bloquea la inyección y se redacta la PII.
4. Ejecución de la herramienta.
5. Model Armor sobre la salida: se bloquea el envenenamiento y se redacta la PII.
6. Auditoría: una entrada con actor, decisión (`allow`, `deny` o `redact` en los atributos), motivo y `trace_id`.

Las decisiones de denegación lanzan `GatewayDeniedError` con un motivo del enum `GatewayReason`; una herramienta que falla se audita como error y su excepción se propaga al runtime sin copiar su mensaje a los spans.
