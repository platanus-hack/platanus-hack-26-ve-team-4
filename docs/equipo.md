# Equipo y forma de trabajo

Propuesta de organización para las 36 horas. La asignación parte de la experiencia visible de cada persona y se puede intercambiar si el equipo lo decide; al cambiarla se actualizan esta tabla, `.github/CODEOWNERS` y las etiquetas de los issues.

## Frentes

| Frente | Responsable | Alcance | Entrega a los demás |
| --- | --- | --- | --- |
| Agente y controles | Carlos ([@CarSanoja](https://github.com/CarSanoja)) | Fixtures, agente víctima, adaptador LLM, motor de políticas, activación y reversión, honeypot, infraestructura y despliegue. | Ejecución trazable con ruta y versión de política estables. |
| Red team y evaluación | Fernando ([@FernandoSiavato](https://github.com/FernandoSiavato)) | Prober, mutaciones, oráculos, analizador, generador de parches y suites de evaluación. | Casos reproducibles, hallazgos con evidencia y políticas candidatas. |
| Arena y entrega | Francisco ([@franbastardo](https://github.com/franbastardo)) | Sesiones, intentos, eventos, clasificación, vistas de participante, arena y operación. | Flujo público usable y panel de operación protegido. |

Carlos coordina la integración: custodia los contratos compartidos y decide cuándo un hito está integrado.

## Propiedad del código

| Ruta | Responsable |
| --- | --- |
| `backend/src/agent_zero/shared/`, `config.py`, `main.py` | Carlos |
| `backend/src/agent_zero/victim/`, `routing/`, `policies/` | Carlos |
| `backend/src/agent_zero/prober/`, `analyzer/`, `patches/`, `evals/` | Fernando |
| `backend/src/agent_zero/sessions/`, `attempts/`, `events/`, `arena/`, `operator/` | Francisco |
| `frontend/` | Francisco |
| `infra/`, `.github/` | Carlos |
| `docs/` | Todo el equipo |

El responsable revisa los cambios en su ruta, pero cualquiera puede proponerlos. `.github/CODEOWNERS` pide su revisión automáticamente.

## Contratos compartidos

Los esquemas de `schemas.py` y los enums de `models.py` son la frontera entre frentes: `AttackCase`, `AttemptAssessment`, `Finding`, `PolicyCandidate`, `TraceEvent` y los tipos de evento. Un cambio de contrato:

1. Se avisa en el canal del equipo antes de empezar.
2. Va en su propio commit o PR, separado de la implementación que lo usa.
3. Actualiza el tipo espejo del frontend (`frontend/src/features/*/types.ts`) en el mismo cambio.

## Flujo de trabajo

- **Ramas.** `<frente>/<tema>`, por ejemplo `redteam/oraculo-reembolso` o `arena/vista-participante`. Ramas cortas, integradas varias veces al día.
- **Integración.** Carlos hace push directo a `main` como admin; el resto entra por pull request sin aprobación obligatoria. Un PR que cruza un límite de confianza (identidad, herramientas, honeypot, operación) espera la revisión de su responsable.
- **Listo para integrar.** `make check` pasa, el código nuevo tiene pruebas y, si toca contenedores, `make up && make smoke` pasa.
- **Seguimiento.** Cada tarea es un issue con etiqueta de frente y prioridad, asignado a una persona y dentro del milestone de su hito.

## Puntos de sincronización

Al cierre de cada ventana del [plan de 36 horas](./plan-36-horas.md) el equipo integra en `main`, ejecuta la pila completa y comprueba la condición de salida del hito. Si no se cumple, se recorta alcance antes de abrir trabajo nuevo.

| Hito | Condición de salida |
| --- | --- |
| H0–3 | Fixtures y contratos acordados; responsables confirmados. |
| H3–8 | Una tarea útil y un ataque preparado producen estados verificables. |
| H8–13 | Un caso autónomo abre un hallazgo con evidencia real. |
| H13–18 | El mismo ataque falla con el parche y una consulta útil sigue pasando. |
| H18–23 | Tres turnos desviados al señuelo sin acciones protegidas. |
| H23–28 | Participación desde otro dispositivo con datos públicos sanitizados. |
| H28–32 | Informe de evaluación y capacidad medida. |
| H32–36 | Demo ensayada, grabación de respaldo y entrega lista. |

## Etiquetas

| Etiqueta | Uso |
| --- | --- |
| `frente:agente`, `frente:redteam`, `frente:arena` | Frente responsable. |
| `P0`, `P1`, `P2` | Prioridad según el plan: ciclo completo, demo de arena y ampliaciones. |
| `contrato` | Cambia un esquema compartido entre frentes. |
| `bloqueado` | Espera una dependencia externa o de otro frente. |
