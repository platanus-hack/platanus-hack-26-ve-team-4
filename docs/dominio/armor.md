# Armor: inspección de contenido y PII

Estado: implementado con reglas deterministas. Examina texto en fronteras concretas; la autorización de recursos pertenece al [gateway](./agent-gateway.md) y a [policies](./policies.md).

## Código y contrato

| Archivo | Responsabilidad |
| --- | --- |
| [model_armor.py](../../backend/src/agent_zero/armor/model_armor.py) | `screen(text, surface)` y `redact_pii(text)`. |
| [models.py](../../backend/src/agent_zero/armor/models.py), [schemas.py](../../backend/src/agent_zero/armor/schemas.py) | Superficies, tipos de amenaza, hallazgos y veredictos. |
| [pattern_scanner.py](../../backend/src/agent_zero/armor/pattern_scanner.py), [threat_pattern.py](../../backend/src/agent_zero/armor/threat_pattern.py) | Combina detectores sobre candidatos normalizados. |
| [normalization.py](../../backend/src/agent_zero/armor/normalization.py), [decoding.py](../../backend/src/agent_zero/armor/decoding.py) | Normalización y decodificación acotada. |
| [injection_patterns.py](../../backend/src/agent_zero/armor/injection_patterns.py), [poisoning_patterns.py](../../backend/src/agent_zero/armor/poisoning_patterns.py) | Patrones de inyección y contaminación por superficie. |
| [pii_patterns.py](../../backend/src/agent_zero/armor/pii_patterns.py), [pii_redactor.py](../../backend/src/agent_zero/armor/pii_redactor.py) | Detección y redacción de correo, teléfono, tarjeta, RUT y cédula. |

Las superficies son `user_input`, `tool_description`, `tool_output`, `memory_write`, `model_output` y `system_prompt`. El veredicto devuelve `action`, hallazgos y, cuando procede, texto saneado.

| Resultado | Comportamiento |
| --- | --- |
| `allow` | No hay amenazas ni PII reconocida; devuelve el texto. |
| `redact` | Detecta PII y devuelve etiquetas como `[EMAIL]` o `[CARD]`. |
| `block` | Detecta una amenaza; el consumidor decide cómo informar la negación. |

Si hay amenaza y PII a la vez, el bloqueo tiene prioridad. Una negación verbal del modelo y un veredicto de Armor no prueban por sí solos que no hubo efectos: esa evaluación corresponde a los oráculos.

## Integración

La publicación de manifiestos examina descripciones, capacidades, herramientas y prompt. El gateway examina argumentos y salidas; Memory Bank examina escrituras antes del cifrado; la víctima examina la respuesta final. El servicio de enrutamiento usa señales conocidas de contenido para desviar sesiones. Las proyecciones públicas aplican además redacción y listas de campos permitidos.

La normalización pliega Unicode y trata texto oculto. Las decodificaciones incluyen base64, rot13, hexadecimal y porcentaje con profundidad y número de candidatos acotados; los límites están en el código y sus pruebas. No quitar esas cotas para detectar un ejemplo aislado: aumentaría el trabajo por entrada de audiencia.

## Pruebas

```bash
cd backend
uv run pytest tests/armor -q
uv run pytest tests/agent_gateway/test_argument_screening.py tests/registry/test_manifest_screening.py tests/memory_bank/test_memory_write_service.py -q
```

| Archivo | Qué verificar al cambiar reglas |
| --- | --- |
| [test_injection_patterns.py](../../backend/tests/armor/test_injection_patterns.py) | Instrucciones adversarias conocidas. |
| [test_poisoning_patterns.py](../../backend/tests/armor/test_poisoning_patterns.py) | Diferencias entre texto normal y contenido de herramienta/memoria. |
| [test_normalization.py](../../backend/tests/armor/test_normalization.py), [test_decoding.py](../../backend/tests/armor/test_decoding.py) | Ofuscación, normalización y límites de exploración. |
| [test_hidden_text.py](../../backend/tests/armor/test_hidden_text.py) | Invisibles y etiquetas Unicode. |
| [test_pii_validators.py](../../backend/tests/armor/test_pii_validators.py), [test_pii_redactor.py](../../backend/tests/armor/test_pii_redactor.py) | Validadores, etiquetas y datos codificados. |
| [legitimate.py](../../backend/tests/armor/legitimate.py), [test_model_armor.py](../../backend/tests/armor/test_model_armor.py) | Falsos positivos y precedencia de acciones. |

La colección actual incluye 372 casos de Armor, muchos parametrizados. Ese número describe cobertura del corpus del repositorio; no es una tasa de detección de ataques desconocidos. Resultados generales en [pruebas](../pruebas/README.md).

## Límites y continuidad

El detector es heurístico, principalmente para patrones en español e inglés. Paráfrasis nuevas pueden pasar; teléfonos de otras regiones y secuencias numéricas ambiguas no tienen cobertura universal. Algunos identificadores largos pueden redactarse como PII.

Para incorporar una regla, añadir un ataque y una tarea legítima cercana que debe seguir pasando, documentar la superficie y ejecutar las suites integradas. No usar una nueva regex como sustituto de comprobar titularidad, saldo o permisos. En caso de regresión, conservar la muestra sintética y revisar la normalización antes de ampliar excepciones globales.
