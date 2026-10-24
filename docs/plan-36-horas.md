# Plan de construcción en 36 horas

Estado: planificación propuesta para tres integrantes. No supone que las tareas estén realizadas ni asigna responsables personales sin acuerdo del equipo.

## 1. Resultado mínimo

La prioridad es una secuencia completa y repetible: una consulta útil, un ataque confirmado, un hallazgo, una política candidata, su validación, activación en caliente y repetición del caso. El honeypot y la participación pública completan la experiencia cuando ese circuito funciona.

El primer corte usa un único escenario de soporte, un proveedor de LLM, una herramienta vulnerable y un validador. Las familias adicionales se incorporan sin cambiar los contratos. No se inicia una integración empresarial o infraestructura distribuida para obtener ese resultado.

## 2. Frentes de trabajo sugeridos

| Frente | Responsabilidad | Entregable para los demás |
| --- | --- | --- |
| Agente y controles | Fixtures, herramientas, identidad, políticas y honeypot. | Ejecución trazable con ruta y versión estables. |
| Red team y evaluación | Plantillas, mutaciones, verificadores, hallazgos y candidatos. | Caso reproducible y decisión de validación. |
| Arena y entrega | API de participación, eventos, interfaz, QR y despliegue. | Flujo público usable y panel de operación protegido. |

El equipo acuerda al inicio qué persona toma cada frente y quién revisa los cambios que cruzan límites de confianza. Los contratos de eventos, intentos y políticas se definen juntos antes de separar trabajo.

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

Si solo se completa P0, el proyecto se presenta como demostrador del ciclo y se declara pendiente la arena pública o el honeypot. El alcance comunicado debe corresponder a lo construido.

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

- El README identifica el estado real y explica instalación y ejecución una vez que existan.
- Los comandos documentados se prueban desde un entorno limpio o sus requisitos se declaran.
- El repositorio incluye dependencias fijadas, variables de ejemplo sin secretos y fixtures sintéticos.
- La evidencia satisface los [criterios de evaluación](./evaluacion.md) o declara explícitamente las brechas.
- El QR funciona desde un teléfono externo y el panel de operación exige autorización.
- La demo identifica actividad preparada, autónoma, humana y reproducida.
- La clasificación final concuerda con efectos protegidos y separa señuelos e inconclusos.
- El logo es un PNG de 1000 × 1000 y menos de 500 KB, y su identidad se revisó.
- `deploy-url` contiene una URL pública comprobada, sin usar una dirección de ejemplo.
- Este repositorio contiene los cambios usados en la presentación; el espejo personal permite desplegarlos.

## 8. Estado de esta entrega documental

Ya están redactados el README, la descripción extensa, los metadatos descriptivos, la arquitectura, el protocolo de evaluación, el guion y este plan. El logo existente cumple tamaño y dimensiones. Siguen pendientes la implementación, las pruebas, la evidencia, la revisión visual del logo y el despliegue; por ello `deploy-url` permanece vacío.

La documentación no atribuye resultados a un sistema que todavía no existe. Al construir, debe actualizarse el estado y reemplazar objetivos por mediciones respaldadas por la campaña correspondiente.
