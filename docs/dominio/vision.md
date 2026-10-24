# Visión

## De qué va

Las empresas ya ponen agentes de IA a operar con herramientas reales: consultan pedidos, emiten reembolsos, recuerdan preferencias. Cada herramienta es una superficie de ataque nueva. Un mensaje bien escrito, un documento recuperado o una memoria contaminada pueden llevar al agente a leer datos ajenos o a ejecutar acciones fuera de su mandato.

El proyecto automatiza el recorrido entre descubrir un fallo y probar su defensa: encuentra una violación con evidencia determinista, deriva un control declarativo, verifica seguridad y utilidad y lo activa sin reiniciar el servicio. Permite revertir si se observa una regresión. La duración depende del proveedor, la cola y la validación; las mediciones y metas se distinguen en [rendimiento](./rendimiento.md).

## Red team, blue team y purple team

| Enfoque | Qué hace | Qué entrega |
| --- | --- | --- |
| Red team | Ataca y documenta lo que encontró. | Un informe. |
| Blue team | Defiende y responde a incidentes. | Reglas y monitoreo. |
| **Purple team** | Ataca y defiende en el mismo bucle, con la defensa alimentada por el ataque. | Defensas verificadas. |

Agent Zero es un **purple team autónomo**. La mitad roja (el Prober y la audiencia) produce ataques; la mitad azul (oráculos, analizador, generador de parches, validador) los convierte en controles verificados. Llamarlo red team se queda corto: lo distintivo es el cierre del ciclo, no el ataque.

## Qué demuestra el MVP

La afirmación evaluable, tomada de [evaluación](../evaluacion.md):

> En un escenario sintético y autorizado, Agent Zero identifica una violación reproducible, propone un control, verifica seguridad y utilidad, lo activa y permite repetir el caso para observar el cambio.

En la demo se ve en vivo:

1. Un asistente de soporte útil responde una consulta legítima.
2. Un ataque preparado logra una acción indebida y abre un hallazgo con evidencia.
3. La audiencia y el Prober atacan durante tres minutos y medio.
4. Mientras la ronda sigue, aparece un parche, se valida y se activa.
5. El mismo ataque se repite y queda detenido; la consulta legítima sigue funcionando.
6. Se revela que algunas victorias aparentes ocurrieron dentro de un señuelo.

## Qué lo diferencia

- **Evidencia determinista.** Una violación se confirma con la traza de herramientas y el estado de los datos, no con un clasificador. Un rechazo verbal no cuenta como defensa si la herramienta igual se ejecutó.
- **Parches declarativos.** El generador elige controles de un catálogo cerrado; no escribe código ni prompts que reemplacen la autorización.
- **Validación con utilidad.** Cada parche se prueba contra variantes reservadas y tareas legítimas antes de activarse.
- **Engaño medible.** El señuelo contiene sesiones sospechosas con datos marcados, y la clasificación final distingue compromisos reales de aparentes.
- **Plataforma modular debajo.** Registro, identidad, gateway, memoria cifrada, runtime durable y auditoría firmada están construidos y probados. La adopción con datos reales requiere completar los límites de [continuidad](../continuidad.md).

## Qué no es

- No ataca sistemas ajenos: todos los destinos y datos son del laboratorio.
- No reemplaza la autorización con un mejor prompt.
- No promete cobertura completa del estándar OWASP para aplicaciones agénticas; usa ASI01, ASI02 y ASI06 para organizar las pruebas.
- No mezcla ataques de la audiencia con la suite controlada al reportar mejoras.

## Aplicación después del evento

El mismo bucle sirve a un equipo que opera agentes en producción: un Prober con sus propios playbooks contra un entorno de staging, oráculos sobre sus invariantes de negocio y un catálogo de controles propio. La flota ya modela departamentos, regiones de datos y clasificación, que es lo que una empresa necesita para adoptarlo.
