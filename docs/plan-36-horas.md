# Plan de construcción en 36 horas

Estado del 24 de octubre de 2026: se conserva el plan de referencia y se registra su avance real en la sección 8. El núcleo, la arena local y la comparación amplia simulada y la LIVE con `claude-haiku-5-5` están implementados; el despliegue público sigue pendiente. La distribución personal conserva su carácter de propuesta.

## 1. Resultado mínimo

La prioridad es una secuencia completa y repetible: una consulta útil, un ataque confirmado, un hallazgo, una política candidata, su validación, activación en caliente y repetición del caso. El honeypot y la participación pública completan la experiencia cuando ese circuito funciona.

El primer corte usa un único escenario de soporte, un proveedor de LLM, una herramienta vulnerable y un validador. Las familias adicionales se incorporan sin cambiar los contratos. No se inicia una integración empresarial o infraestructura distribuida para obtener ese resultado.

## 2. Frentes de trabajo sugeridos

| Frente | Responsabilidad | Entregable para los demás |
| --- | --- | --- |
| Agente y controles | Fixtures, herramientas, identidad, políticas y honeypot. | Ejecución trazable con ruta y versión estables. |
| Red team y evaluación | Plantillas, mutaciones, verificadores, hallazgos y candidatos. | Caso reproducible y decisión de validación. |
| Arena y entrega | API de participación, eventos, interfaz, QR y despliegue. | Flujo público usable y panel de operación protegido. |

La propuesta de responsables, propiedad del código y forma de trabajo está en [equipo](./equipo.md); el equipo la confirma al inicio. Los contratos de eventos, intentos y políticas se definen juntos antes de separar trabajo.

## 3. Hitos por horario

| Ventana | Construcción | Condición de salida |
| --- | --- | --- |
| Horas 0–3 | Acordar escenario, contratos, repositorio personal de despliegue, proveedor y presupuesto. | Fixtures definidos, responsabilidades acordadas y primer despliegue mínimo accesible. |
| Horas 3–8 | Víctima con una herramienta, identidad de servidor, traza y política base de laboratorio. Interfaz con eventos simulados etiquetados. | Una tarea útil y un ataque preparado producen estados verificables. |
| Horas 8–13 | Plantillas, mutaciones, oráculos, analizador y persistencia de hallazgos. Sustituir eventos simulados. | Un caso autónomo abre un hallazgo con evidencia real. |
| Horas 13–18 | Catálogo de controles, candidato estructurado, validación breve y activación atómica. | El mismo ataque falla con el parche y una consulta útil sigue pasando. |
| Horas 18–23 | Honeypot aislado, ruta persistente, marcador señuelo y clasificación. | Tres turnos desviados sin acciones protegidas; revelación coherente. |
| Horas 23–28 | QR público, cola, límites, autorización de operación y SSE reanudable. | Participación desde otro dispositivo con datos públicos sanitizados. |
| Horas 28–32 | Suite amplia, variantes reservadas, utilidad, coste y prueba de carga acotada. | Informe de ejecución, defectos críticos resueltos y capacidad medida. |
| Horas 32–35 | Ensayo completo, regresión final, grabación de respaldo y metadatos. | Demo repetible con resultados propios y URL verificada. |
| Hora 35–36 | Congelar funcionalidades, revisar entrega y disponibilidad. | Commit identificado, documentación coherente y envío listo. |

Las ventanas describen hitos integrados: los tres frentes pueden avanzar simultáneamente, pero el resultado de cada etapa se comprueba en conjunto. Si un hito falla, se reduce alcance antes de añadir nuevas funciones.

## 4. Prioridades

**P0, necesarias para afirmar el ciclo completo:** escenario sintético, un fallo reproducible, oráculo determinista, parche declarativo validado, conservación de una tarea legítima, política versionada, activación y reversión sin reinicio, trazas y separación de operación.

**P1, necesarias para la demo de arena propuesta:** participación por enlace, eventos en vivo, origen humano/autónomo, clasificación provisional y final, honeypot aislado, límites de uso y revelación basada en evidencia.

**P2, ampliaciones si queda tiempo:** más familias, explicación visual de causas, exportación de informe y comparación de varios candidatos. Soporte de más proveedores, integraciones externas y despliegue empresarial quedan para después del evento.

P0 y las funciones locales de P1 ya están integrados. El acceso público de P1 requiere todavía un despliegue y una URL comprobados. La cobertura de seis familias y la exportación de P2 también existen. El alcance comunicado debe distinguir esos resultados de las mediciones pendientes de carga y despliegue, y las tasas simuladas de las medidas con proveedor real.

## 5. Cómo recortar sin perder el concepto

- Reducir familias antes que eliminar verificación de efectos o tareas legítimas.
- Usar documentos de texto con búsqueda simple antes que montar una base vectorial.
- Mantener un catálogo pequeño de validadores antes que generar código ejecutable.
- Usar una sola instancia y SSE antes que introducir colas distribuidas.
- Reducir concurrencia y mostrar espera antes que perder trazabilidad.
- Conservar el ensayo reproducible antes de pulir animaciones o exportaciones.

## 6. Riesgos de construcción

| Riesgo | Señal temprana | Ajuste |
| --- | --- | --- |
| Demasiados módulos sin integrar. | A la hora 13 no existe un hallazgo completo. | Concentrar al equipo en un caso de extremo a extremo. |
| Dependencia del juicio del LLM. | Se declara éxito sin cambios observables. | Implementar primero oráculos de acceso y reembolso. |
| Sobreajuste al ataque inicial. | Pasa el caso conocido, fallan variantes. | Mantener el candidato pendiente y ampliar el control. |
| Costo o latencia altos. | La cola crece y las pruebas no terminan. | Limitar mutaciones, turnos y concurrencia; reservar cupos de validación. |
| Honeypot poco aislado. | Comparte memoria o adaptadores protegidos. | Separar almacenamiento y permisos antes de habilitar el desvío. |
| Defensa inutiliza al asistente. | Fallan consultas propias o reembolsos válidos. | Rechazar el candidato o revertir la política. |
| Despliegue tardío. | El QR solo abre en la máquina del equipo. | Probar acceso público desde las primeras horas. |

## 7. Definición de entrega lista

La revisión final debe confirmar:

- El README identifica el estado real y ofrece arranque Docker/demo, smoke y desarrollo reproducibles.
- Los comandos documentados se prueban desde un entorno limpio o sus requisitos se declaran.
- El repositorio incluye dependencias fijadas, variables de ejemplo sin secretos y fixtures sintéticos.
- La evidencia satisface los [criterios de evaluación](./evaluacion.md) o declara explícitamente las brechas.
- El QR funciona desde un teléfono externo y el panel de operación exige autorización.
- La demo identifica actividad preparada, autónoma, humana y reproducida.
- La clasificación final concuerda con efectos protegidos y separa señuelos e inconclusos.
- El logo es un PNG de 1000 × 1000 y menos de 500 KB, y su identidad se revisó.
- `deploy-url` contiene una URL pública comprobada, sin usar una dirección de ejemplo.
- Este repositorio contiene los cambios usados en la presentación; el espejo personal permite desplegarlos.

## 8. Estado de la implementación y entrega

| Área | Estado comprobado |
| --- | --- |
| Ciclo P0 | Integrado con oráculos, controles acumulativos, ocho casos de validación, activación, repetición protegida y reversión. |
| Arena local | Chat e historial recuperables, QR configurable, tiempo transcurrido, clasificación provisional/final y operación autorizada. |
| Autonomía | Campañas durables de seis familias, mutación estructurada y explicaciones de asesoría con roles separados. |
| Recuperación | Outbox, leases, escrituras de negocio idempotentes, auditoría con journal y reset archivado recuperable. |
| Capacidad de identidad | 100 plazas por defecto y hasta 500 configurables, sin compartir cliente entre participantes; no equivale a una prueba de carga real. |
| Evaluación amplia | [Artefacto](../artifacts/core-evaluation/demo-270.json): 270 ejecuciones y 732 llamadas simuladas, 90/90 → 0/90 violaciones, 45/45 tareas útiles por versión, cero inconclusos. |
| Proveedor real | [Once comprobaciones del ciclo completo](../artifacts/core-evaluation/live-p0.json), 93 llamadas LIVE, cinco roles y coste estimado de 0,0101596 USD a partir de tokens medidos. |
| Evaluación amplia LIVE | [Artefacto](../artifacts/core-evaluation/live-270-2026-10-24-yummy.json): 270 ejecuciones con `claude-haiku-5-5`, 683 llamadas de evaluación con coste medido, 59/90 → 0/90 violaciones, 45/45 tareas útiles por versión, cero inconclusos; coste total de 0,075079 USD. |
| Contenedores | Ambas imágenes construidas; proxy, ejercicio completo y reset archivado comprobados en modo demo. |
| Backend | 860 pruebas aprobadas y dos LIVE opcionales omitidas, con advertencias tratadas como errores; Ruff, formato y mypy aprobados. |
| Frontend | 47 pruebas, tipado, lint y build aprobados. La revisión visual en navegador sigue pendiente. |
| Entrega pública | URL pública, prueba desde un teléfono externo, medición de carga y grabación de respaldo pendientes. |

La evidencia simulada identifica el modelo efectivo, hashes y commit de referencia, y declara que el árbol tenía cambios concurrentes. Sus tasas no se atribuyen a un LLM real. El protocolo, comandos de generación/evaluación y procedencia completa están en [evaluación](./evaluacion.md).

Para repetir el ensayo local, usar [núcleo implementado](./nucleo.md): `make up`, `make smoke` y `make smoke-exercise`, con el secreto exportado desde el `.env` propio. El ejercicio cierra la ronda tras revelar; el siguiente ensayo empieza con reset archivado explícito. La evaluación se inicia con la versión activa comprobada, no con un número supuesto.

La revisión final pendiente se concentra en ejecutar la comparación real con presupuesto, medir capacidad y latencia bajo carga, revisar visualmente la interfaz y publicar una URL comprobada. El logo existente cumple tamaño y dimensiones; su revisión de identidad sigue separada. `deploy-url` debe permanecer sin una URL inventada mientras no exista ese despliegue.
