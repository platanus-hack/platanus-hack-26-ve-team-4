# Flujo de decisión

## Coreografía por eventos, sin supervisor

No hay un agente orquestador que decida qué agente llama a cuál. El núcleo es una **máquina de estados dirigida por eventos**: cada evento persistido dispara un trabajador, que produce el siguiente evento.

| Ventaja | Por qué |
| --- | --- |
| Rápido | Cero llamadas al modelo para coordinar. |
| Auditable | Cada transición es un evento con `attempt_id`, `session_id` y `policy_version`, y queda en la auditoría firmada. |
| No inyectable | No existe un supervisor al que un atacante pueda convencer de saltarse un paso. |
| Recuperable | Los trabajadores son runs del runtime con checkpoints y reintentos; un fallo no pierde el ciclo. |

## El ciclo

```text
attempt_queued
  → router ────────────────── ms ──→ allow | block | divert (fija la ruta de la sesión)
  → run de víctima o señuelo ─ s ───→ tool_proposed → tool_denied | tool_completed
attempt_completed
  → oráculos ──────────────── ms ──→ attempt_evaluated: confirmed_violation | prevented | not_achieved
                                                       | contained_honeypot | inconclusive
  → hallazgo ──────────────── ms ──→ finding_opened o evidencia sumada a uno abierto
       └─ analizador (LLM) ─── s ───→ familia y causa probable, en segundo plano
  → candidato ─────────────── ms ──→ patch_proposed desde la tabla objetivo → control
       └─ generador (LLM) ──── s ───→ motivo en español, en segundo plano
  → validación nivel 1 ────── ms ──→ re-evaluar la traza grabada con la política nueva
  → validación nivel 2 ────── s ───→ 8 runs en paralelo en copias limpias
  → patch_validated
  → activación ────────────── ms ──→ policy_activated: cambio atómico del puntero de versión
```

Las ramas de segundo plano enriquecen el panel pero nunca bloquean el ciclo: un parche se puede activar antes de que el analizador termine de redactar la causa.

## Quién decide cada cosa

| Decisión | Quién | Insumo | Regla |
| --- | --- | --- | --- |
| Si un intento se acepta | `attempts` | Token de sesión, tamaño, frecuencia, fase de la ronda | Cupo por sesión y global; entradas cerradas devuelven 409. |
| A qué entorno va | Router (`routing`) | Ruta de la sesión, violaciones previas, señales de Armor | El desvío al señuelo es definitivo para la sesión. |
| Si una herramienta se ejecuta | Motor de políticas en el gateway | Versión de política del intento, contexto de la sesión, argumentos | Niega por defecto si un validador falla. |
| Si hubo violación | Oráculos | Traza de herramientas, estado antes y después, canarios | La opinión del modelo nunca confirma una violación. |
| Si es un hallazgo nuevo | `analyzer` | Clave `(objetivo, herramienta, control ausente)` | Misma clave abierta: se suma evidencia. |
| Qué control aplicar | `patches` | Tabla cerrada objetivo → control | El LLM solo elige si la tabla tiene más de una opción válida. |
| Si se activa | Validador | Resultados de los niveles 1 y 2 | Cero violaciones críticas y cero regresiones legítimas. |
| Si se revierte | Operador | Regresión observada | Restaura el padre validado. |
| Qué atacar después | Planificador del Prober | Éxitos, novedad y presupuesto por familia | Prioriza familias con hallazgos abiertos o sin explorar. |

## Validación en dos niveles

**Nivel 1, contrafactual.** Las políticas actúan sobre llamadas a herramientas. La traza del intento original ya contiene cada `tool_proposed` con sus argumentos y el contexto de la sesión. Basta pasar esas llamadas grabadas por el motor de políticas con la versión candidata: si alguna violación vuelve a pasar, el candidato se rechaza en milisegundos sin gastar una llamada al modelo.

**Nivel 2, en vivo.** El nivel 1 no ve si el modelo encuentra otro camino con la política nueva. Por eso se ejecutan en paralelo, cada uno sobre una copia limpia de datos y memoria:

- El caso original.
- Dos variantes reservadas de la misma familia, que el generador nunca vio.
- Cinco tareas legítimas críticas: consulta propia, reembolso válido, pregunta documental, preferencia inocua y una frase que menciona seguridad sin ser ataque.

Se activa solo con cero violaciones en los casos adversarios y las cinco tareas legítimas completadas.

## Activación y versiones

1. El intento fija su versión de política al encolarse y la conserva hasta terminar.
2. Antes de activar, se drenan los intentos en curso con un plazo; si no se vacían, la activación queda pendiente y se muestra.
3. El puntero de versión activa cambia en una sola transacción.
4. Los intentos nuevos usan la versión nueva; los efectos pasados no se revierten, y la memoria contaminada se pone en cuarentena.

Las transiciones permitidas ya están en `policies/lifecycle.py`: `candidate → validating → active → superseded`, con `rejected` y `rolled_back` como estados finales.

## Fallos y degradación

| Situación | Comportamiento |
| --- | --- |
| Error del proveedor o de infraestructura en un intento | `inconclusive`; no suma victoria ni derrota. |
| Presupuesto diario agotado | Los runs fallan con `daily_budget`; el Prober se detiene y se conserva la evidencia. |
| Analizador o generador fallan | El ciclo sigue con la tabla del catálogo y un motivo genérico. |
| Candidato rechazado | El hallazgo sigue abierto y se registra el motivo; el siguiente candidato espera evidencia nueva. |
| Variante reabre un hallazgo mitigado | El hallazgo pasa a `reopened` y vuelve a entrar al ciclo. |
