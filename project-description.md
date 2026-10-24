# AGENT ZERO — Arena de Red Teaming Autónomo con Defensa en Vivo

## Pitch en una frase

> Mientras otros construyen el escudo, nosotros construimos al atacante autónomo que encuentra las grietas y las sella en tiempo real, en una arena pública donde cualquiera puede intentar hackear a nuestro agente… y fallar.

Esa es la ambición de la demo. La promesa técnica del MVP es concreta y medible: descubrir una vulnerabilidad reproducible en un agente de laboratorio, generar una mitigación, validarla y mostrar cómo cambia el resultado del mismo ataque sin reiniciar el servicio. Ninguna defensa se presentará como invulnerable.

## El problema

Un agente de IA puede consultar documentos, leer datos de clientes, recordar información y ejecutar herramientas. Si interpreta una instrucción maliciosa como una orden legítima, el fallo puede convertirse en una acción: consultar el pedido de otra persona, autorizar un reembolso indebido o guardar una falsa excepción de seguridad para conversaciones futuras.

Una revisión previa al lanzamiento ofrece una fotografía de un sistema que seguirá cambiando. Nuevas herramientas, documentos y políticas pueden introducir rutas de ataque distintas. Nuestra hipótesis es que los equipos necesitan repetir estas pruebas durante la evolución del agente y verificar que las defensas conservan su utilidad.

Agent Zero propone ese ciclo continuo en un entorno autorizado: **atacar → observar → explicar → proponer un parche → validar → activar → volver a atacar**.

## La propuesta

Agent Zero es una arena de seguridad ofensiva y defensiva para agentes de IA. Combina un red team autónomo, participación humana, análisis de evidencia y un motor de políticas versionadas. El producto central es la capacidad de descubrir y reproducir fallos; los bloqueos y parches hacen visible cómo se responde a ellos.

La analogía de producto es un «Chaos Monkey para agentes de IA»: introducir fallos y ataques controlados para comprobar límites de seguridad. La comparación describe el enfoque experimental, sin implicar una integración con esa herramienta.

En el MVP, el entorno se ejecutaría en una máquina con acceso a APIs de modelos. Los clientes, pedidos, documentos, herramientas y secretos de prueba serían sintéticos. La exposición pública se limitaría a la interfaz de participación de la arena.

## Usuarios y valor

| Usuario | Necesidad | Resultado que buscamos ofrecer |
| --- | --- | --- |
| Equipo que desarrolla agentes | Detectar qué cambia al añadir una herramienta o una fuente RAG. | Casos reproducibles y regresiones asociadas a versiones. |
| Equipo de seguridad | Entender impacto, alcance y control que falló. | Trazas de acciones, evidencia y propuestas de mitigación revisables. |
| Responsable de producto | Conservar tareas útiles mientras reduce exposición. | Comparación de seguridad y utilidad antes y después de cada parche. |
| Jurado o participante | Comprobar el comportamiento de forma directa. | Arena interactiva, clasificación y explicación del resultado. |

Los sectores de banca, comercio, salud y telecomunicaciones son posibles usuarios futuros por sus flujos con datos y acciones sensibles. El primer escenario se concentra en soporte comercial; integrar sistemas reales de esos sectores queda fuera del hackathon.

El valor esperado es reducir el tiempo entre descubrir un fallo y verificar una mitigación, aumentar la repetibilidad de auditorías y convertir ataques nuevos en casos de regresión. Son hipótesis de producto pendientes de medición, sin cifras de ahorro o eficacia asumidas.

## Qué lo diferencia

1. **El atacante es parte del producto.** Un generador busca nuevas rutas de fallo y mutaciones de casos conocidos, además de recibir intentos de la audiencia.
2. **El antes y después es ejecutable.** El mismo caso se reproduce sobre una versión base y una versión candidata, con resultados observables.
3. **La defensa cambia durante la sesión.** Se activan versiones de política sin reiniciar el servicio, después de pasar una validación acotada.
4. **El honeypot añade una respuesta activa.** Una sesión sospechosa puede continuar con datos señuelo y herramientas aisladas, permitiendo observar la técnica.
5. **La utilidad también cuenta.** Rechazar todas las consultas no constituye una defensa aceptable: las operaciones legítimas deben seguir funcionando.

La originalidad propuesta está en reunir estos elementos en una experiencia verificable de arena pública. No afirmamos ser los primeros en red teaming automatizado ni que otros productos carezcan de estas capacidades; una comparación exhaustiva de mercado queda pendiente.

## El agente víctima: soporte de una tienda ficticia

El asistente de laboratorio ayuda a una persona autenticada a revisar sus pedidos y solicitar reembolsos dentro de una política comercial ficticia. Tiene acceso a documentos de ayuda, un catálogo y una base de datos sintética. Cada sesión recibe su identidad desde el servidor.

Las tareas legítimas incluyen consultar un pedido propio, explicar una condición de devolución y registrar una preferencia inocua. Los objetivos adversarios incluyen acceder a un pedido ajeno, conseguir un reembolso que exceda el límite o persistir una instrucción que cambie autorizaciones en un turno posterior.

Las herramientas propuestas son `get_order`, `request_refund`, `search_knowledge` y `save_memory`. La autorización se verifica al ejecutar la herramienta; una afirmación del modelo o del usuario no cambia la identidad autenticada. La vulnerabilidad inicial de la demo será una omisión deliberada y acotada en un adaptador de laboratorio con datos ficticios.

## Cuatro módulos, un ciclo de mejora

### 1. Prober Agent: generar y mutar ataques

El agente atacante parte de plantillas por familia y utiliza un modelo pequeño para producir variaciones de redacción, idioma y contexto. Explora inyección directa, instrucciones incrustadas en documentos, desvío de objetivos, uso indebido de herramientas y contaminación de memoria.

Cada caso incluye objetivo, superficie, secuencia de mensajes, semilla y condición de éxito. Los ataques generados permanecen dentro del escenario autorizado, con un presupuesto de llamadas y sin exploración de infraestructura externa.

### 2. Vulnerability Analyzer: convertir intentos en hallazgos

El analizador observa respuestas, llamadas de herramientas, cambios de estado y procedencia de documentos. Distingue un intento de ataque, una violación confirmada, una mitigación y un resultado inconcluso. Un clasificador semántico propone la categoría y una explicación, mientras que verificadores deterministas comprueban los efectos medibles.

Por ejemplo, si aparece un pedido ajeno en la salida o se ejecuta un reembolso indebido, existe evidencia de violación. Si el modelo solo asegura «lo hice» y el estado no cambia, no basta para declarar éxito. La causa raíz se presenta como hipótesis respaldada por trazas, con su nivel de confianza.

### 3. Patch Generator: proponer una mitigación verificable

El generador transforma el hallazgo en una política candidata. Puede reforzar el contexto del sistema, activar un validador determinista existente o añadir una condición de cuarentena semántica. La salida utiliza un esquema permitido; el MVP no ejecutará código Python arbitrario escrito por un LLM.

Antes de activarse, el parche debe bloquear el caso reproducido, conservar tareas legítimas y respetar reglas base que el generador no puede debilitar. Si falla o la evidencia es insuficiente, se rechaza o queda pendiente. «Aprender» significa ampliar políticas y pruebas de regresión, sin modificar los pesos del modelo.

### 4. Policy Engine / Honeypot Router: hacer cumplir y observar

El motor evalúa acciones antes de ejecutarlas y salidas antes de publicarlas. Puede permitir, bloquear o desviar una sesión a un entorno señuelo. Conserva versiones y trazas para explicar qué política produjo cada resultado.

El honeypot utiliza clientes, pedidos, memoria y herramientas propios. Una aparente extracción de datos señuelo no cuenta como una vulneración del entorno protegido. La separación se realiza en el servidor, antes de cualquier acción, y permanece durante la sesión.

## Agent Zero Guard: el mismo ciclo para cualquier agente

El ciclo de la arena no depende de la tienda ficticia. El Guard lo aplica al agente de cualquier empresa a partir de un **contrato de dominio** en YAML. En él, la empresa declara:

- sus herramientas;
- el tipo de cada argumento: monto, recurso con dueño, lista cerrada, identificador o texto;
- los invariantes de negocio que nunca deben romperse;
- unas pocas tareas legítimas que ninguna regla puede bloquear.

El agente consulta al Guard antes y después de cada herramienta. Con eso el Guard:

- etiqueta la procedencia de cada argumento: lo dijo el usuario, sale de un sistema propio, de un tercero o de la memoria;
- confirma violaciones sobre hechos;
- sintetiza reglas dentro de una gramática cerrada, propuestas por el modelo o derivadas de forma determinista;
- las valida contra las tareas legítimas y contra inyecciones simuladas;
- las activa o las deja propuestas para aprobación humana.

Si algo no está declarado, se deniega. Los contratos se versionan en el repositorio o se registran por API desde la consola del operador.

El repositorio incluye tres contratos de dominios distintos que funcionan sobre el mismo código: soporte de comercio, banca personal y clínica. En la prueba con el banco ocurre lo siguiente:

- Un correo intenta que el agente transfiera 900 USD a un beneficiario externo. Se bloquea antes de ejecutarse.
- De ese intento, el Guard aprende reglas de procedencia.
- Una transferencia de 40 USD dictada por otro correo, que no rompe ningún invariante, se bloquea igual.
- El pago legítimo del alquiler sigue funcionando.

La integración se describe en [docs/integracion.md](./docs/integracion.md).

## La experiencia «wow»

El jurado ve un asistente de soporte y una vulnerabilidad inicial reproducible. Se abre un QR para que participantes intenten vulnerarlo durante tres o cuatro minutos. La arena muestra actividad, hallazgos, parches y un indicador de vulnerabilidades abiertas en el conjunto conocido.

Mientras llegan intentos, Agent Zero analiza evidencia y propone una defensa. Al activarla, se repite el ataque inicial: la acción antes permitida se bloquea y una consulta legítima sigue funcionando. La mejora queda asociada a una versión y a un caso verificable.

El giro final utiliza el honeypot: algunos participantes reciben una respuesta que parece confirmar su éxito, pero solo obtuvieron datos sintéticos del señuelo. El panel de operación conserva el destino real y la técnica observada. Al revelar el giro, se contrastan «éxitos aparentes», «compromisos confirmados» y «sesiones contenidas».

La inscripción indica que se trata de una simulación con posibles señuelos y que sus intentos quedarán registrados para el ejercicio. El detalle de cuándo se activa el desvío permanece oculto hasta la revelación. Las reglas y la clasificación nunca convierten una respuesta convincente en evidencia de compromiso.

## Alcance del hackathon

El objetivo de 36 horas es un agente víctima, un escenario comercial, un generador por plantillas con mutación, un analizador híbrido, parches declarativos, dos entornos aislados y una interfaz con eventos en vivo. La prioridad es demostrar el ciclo completo con una familia de vulnerabilidad y extenderlo después a las demás.

La inyección indirecta se representará con documentos de texto controlados. La memoria será una tabla por sesión, suficiente para probar un ataque entre turnos. No hacen falta un navegador autónomo, una base vectorial ni agentes con ejecución de código para demostrar el concepto.

Quedan fuera la reparación universal de agentes, el entrenamiento de modelos, las integraciones empresariales, el acceso a datos reales y la activación autónoma de cambios en producción. El MVP adapta controles dentro del laboratorio; un producto posterior requeriría aprobaciones, aislamiento y evaluación adicionales según cada integración.

## Cómo mediremos el resultado

Se compararán la tasa de violaciones confirmadas antes y después del parche, la tasa de tareas legítimas completadas, los bloqueos incorrectos y el tiempo entre hallazgo y activación. Se reportarán cantidades absolutas, denominadores, versiones y casos inconclusos.

La aspiración de «parchear en segundos» se probará con una meta inicial de hasta 30 segundos para un caso preparado y carga controlada. No es un resultado obtenido ni un compromiso de servicio. Un tiempo excedido se mostrará tal como ocurrió.

La barra de vulnerabilidades abiertas representa hallazgos conocidos y reproducibles, no toda la superficie de ataque. Un hallazgo se marca mitigado solo tras verificar su caso y variantes reservadas. La contención en honeypot se registra como resultado separado.

## Evolución del producto

Tras el hackathon, la ruta propuesta es ofrecer un kit de evaluación para desarrollo, integrar suites de regresión en CI y ampliar los adaptadores del Guard para agentes existentes. Una etapa posterior podría ofrecer campañas programadas, gestión por organización y propuestas de política con aprobación del responsable del sistema.

La hipótesis comercial es una suscripción por agentes evaluados y volumen de ejecuciones, con campañas privadas para equipos de seguridad. Precios, disposición de pago y comparación con proveedores existentes requieren entrevistas y validación; no se asumen clientes ni ingresos.

## Referencias y documentos de implementación

El enfoque usa como referencia las categorías de secuestro de objetivos (ASI01), uso indebido de herramientas (ASI02) y contaminación de memoria y contexto (ASI06) de [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/download/52117/). Es un marco para organizar escenarios, sin implicar certificación ni cobertura completa.

La construcción se detalla en [arquitectura](./docs/arquitectura.md), [evaluación](./docs/evaluacion.md), [guion de demo](./docs/demo.md) y [plan de 36 horas](./docs/plan-36-horas.md).
