# AGENT ZERO

**El sistema inmune de tu agente de IA: lo ataca, comprueba el daño real y lo bloquea con una regla verificada, sin tocar su código.**

<img src="./project-logo.png" alt="Logo del proyecto" width="200" />

**Track:** AI Security · **Evento:** Platanus Hack 26: Caracas ft. Yummy · **Equipo:** team-4.

## El problema

Las empresas ya ponen en producción agentes con herramientas reales: consultan pedidos, mueven dinero, leen historias clínicas, guardan memoria. Cada herramienta es una puerta. Un mensaje bien escrito, un correo o un documento envenenado bastan para que el agente reembolse, transfiera o lea datos de otra persona.

Hoy eso se descubre tarde. Un humano investiga, alguien escribe un parche y se despliega días después. Mientras tanto el agente sigue expuesto, y los clasificadores de "¿esto suena peligroso?" no dicen si hubo daño.

## Qué hace Agent Zero

Es un *purple team* autónomo: ataque y defensa en el mismo bucle.

1. **Ataca sin parar.** El Prober prueba inyecciones, abuso de herramientas y memoria envenenada, y se adapta a lo que funciona. Personas reales también pueden atacar.
2. **Confirma el daño, no el texto.** Un oráculo determinista mira el efecto: si la transferencia se registró o si se leyó un dato ajeno. Sin efecto no hay hallazgo.
3. **Escribe la defensa desde el incidente.** Rastrea de dónde salió cada argumento (el cliente, el sistema, un documento externo, la memoria) y propone reglas en una gramática cerrada, por ejemplo `DENEGAR transferir SI monto viene de una fuente no confiable`.
4. **La prueba antes de activarla.** La regla tiene que bloquear el ataque sin romper ninguna tarea legítima declarada. Si rompe algo, se rechaza.
5. **La activa en segundos y se revierte con un clic.** Vive en el gateway por el que pasan las llamadas del agente: no hay redeploy ni PR.
6. **Recuerda.** Cada versión hereda las reglas de su padre, con hash, motivo y la evidencia que la justificó.

El modelo propone; el código decide. Oráculos, compuerta, activación y reversión son deterministas, y ninguna regla se activa porque un LLM lo diga.

## Qué obtiene un equipo que lo usa

| Hoy | Con Agent Zero |
| --- | --- |
| Pentest anual con informe en PDF | Ataques continuos contra el agente |
| Un clasificador que avisa si algo "suena raro" | Evidencia de daño real sobre las herramientas |
| Parche manual en días, a veces rompiendo cosas | Regla validada y activa en segundos |
| Revertir exige redeploy | Reversión con un clic a la versión verificada |
| "¿Estamos más seguros?" se responde con una opinión | Tasa de éxito del ataque por versión de política, con n e intervalo |

## Cómo lo usa cualquier empresa

Agent Zero separa lo que solo la empresa sabe de lo que se puede automatizar:

- **La empresa declara qué nunca debe pasar**, una vez, en un contrato.
- **Agent Zero produce, prueba y aplica el cómo**, ante cada ataque.

El motor no conoce ningún negocio. Yummy, un banco y una clínica son tres archivos YAML en [`backend/contracts/`](./backend/contracts/) que usan el mismo código.

### Lo que le pedimos a la empresa

| Pedimos | Para qué | Cómo se entrega |
| --- | --- | --- |
| **1. Un contrato del agente** | Herramientas, qué significa cada argumento, invariantes y tareas legítimas | Un YAML revisado por PR, como cualquier configuración. Una a dos horas para un agente típico |
| **2. Dos llamadas por herramienta** | `check` antes de ejecutar y `effects` después | Un envoltorio de 80 líneas ([cliente de ejemplo](./examples/guard/agent_zero_guard.py)) o un proxy en su gateway |
| **3. El dueño de cada recurso** | Saber si la cuenta, el pedido o el paciente es del usuario de la sesión | Una función `owner_of` que ya tienen en su backend |
| **4. El origen de su contexto** | Saber si un dato lo dijo el usuario o vino de un correo, un documento o la memoria | Etiquetar cada fragmento del prompt como `user`, `store`, `untrusted` o `memory` |

No pedimos acceso a su código, a su modelo ni a sus datos de producción. Agent Zero solo ve los nombres de las herramientas, sus argumentos y las etiquetas de origen.

### El contrato

```yaml
contract_id: banco-transferencias
subject: Titular autenticado de la banca en línea.
enforce_invariants: true
tools:
  transferir:
    side_effect: true
    arguments:
      cuenta:  {kind: resource}
      destino: {kind: identifier}
      monto:   {kind: amount}
invariants:
  - id: tope-por-transferencia
    tools: [transferir]
    never: {kind: exceeds, argument: monto, limit: 500}
  - id: beneficiarios-registrados
    tools: [transferir]
    never: {kind: not_in, argument: destino, allowed: [BEN-ALQUILER, BEN-AHORRO]}
legitimate:
  - name: pagar-alquiler
    tool: transferir
    arguments: {cuenta: CTA-1, destino: BEN-ALQUILER, monto: 450}
    provenance: {cuenta: user, destino: user, monto: user}
    owners: {cuenta: subject}
```

Cinco tipos de argumento (`amount`, `resource`, `enum`, `identifier`, `text`) y seis condiciones (`exceeds`, `window_exceeds`, `not_owner`, `untrusted_origin`, `not_in`, `contains_any`) cubren dinero por llamada y acumulado en una ventana de tiempo, recursos con dueño, listas permitidas, contenido prohibido y procedencia en cualquier dominio. El contrato se valida al cargar: una tarea legítima que rompa un invariante, una condición que no encaje con el tipo del argumento o una herramienta desconocida lo rechazan.

### En el código del agente

```python
guard = AgentZeroGuard(url, "banco-transferencias", api_key)
transferir = guard.wrap("transferir", transferir, owner_of=dueno_de_cuenta)

transferir(subject="ana", context=[
    {"origin": "user", "text": mensaje_del_cliente},
    {"origin": "untrusted", "text": correo_resumido},
], cuenta="CTA-1", destino="BEN-EXTERNO", monto=900, concepto="factura")
```

Si el Guard deniega, la herramienta no se ejecuta y el agente recibe el motivo. Si el Guard no responde, el cliente falla cerrado.

Hay adaptadores listos para [Python](./examples/guard/agent_zero_guard.py), [Node](./examples/guard/node/agent-zero-guard.mjs), [MCP](./examples/guard/mcp_proxy.py) (un proxy por stdio que se pone delante de cualquier servidor MCP sin tocar su código) y [Strands](./examples/guard/strands_guard.py), descritos en [examples/guard](./examples/guard/README.md).

### Alta del contrato

Un contrato entra de dos formas: como archivo en `backend/contracts/` revisado por PR, o en caliente con `POST /api/guard/contracts` desde la API o desde la consola del operador, que también muestra las versiones de política, el informe de la compuerta, los hallazgos y los botones de activar y revertir.

### Dos modos por contrato

- **`enforce_invariants: true`**: los invariantes también bloquean antes de ejecutar. Un ataque nunca llega a producir efecto, y aun así Agent Zero aprende reglas de procedencia que bloquean variantes que **no** rompen ningún invariante. Recomendado para dinero y datos sensibles.
- **Detección por efecto (por defecto)**: el hallazgo nace de lo que pasó, informado en `effects`. Sirve cuando el daño solo se ve después, por ejemplo el dueño del pedido devuelto.

Con `auto_activate: false`, cada política queda como propuesta hasta que un operador la aprueba.

### Pruébalo en dos minutos

```bash
make arena-server ARENA_MODE=demo
python3 examples/guard/banco_demo.py --url http://127.0.0.1:8000
python3 examples/guard/mcp_banco_demo.py --url http://127.0.0.1:8000 --subject diego
node examples/guard/node/banco-demo.mjs http://127.0.0.1:8000 elena
```

En local, la clave por defecto es `change-me-guard` salvo que `.env` defina `AGENT_ZERO_GUARD_API_KEY`. Fuera de local, una clave de menos de 32 caracteres deja el Guard apagado (503) sin afectar a la arena.

Salida real del agente bancario de ejemplo:

```text
2. Un correo inyecta una transferencia de 900 USD: el invariante la frena
  BLOQUEADA  900 a BEN-EXTERNO  <- invariant:tope-por-transferencia
   regla v1: DENEGAR transferir SI monto > 500
   regla v1: DENEGAR transferir SI destino viene de una fuente no confiable
   regla v1: DENEGAR transferir SI monto viene de una fuente no confiable
4. Una inyección pequeña que no rompe ningún invariante
  BLOQUEADA  40 a BEN-AHORRO desde el correo  <- r_transferir_destino_untrusted
5. Lo legítimo sigue funcionando
  EJECUTADA  alquiler 450 a BEN-ALQUILER
7. Un tercer pago de 450 en el día: el tope diario de 1000 lo frena
  BLOQUEADA  alquiler 450 a BEN-ALQUILER  <- r_transferir_tope_diario
```

El paso 4 es la diferencia con una lista de reglas: 40 USD a un beneficiario registrado cumple todos los invariantes, pero el monto lo dictó un correo.

La [guía de integración](./docs/integracion.md) detalla el contrato, la API, los adaptadores, el modelo de seguridad y los límites.

### Lo que todavía no hace

- **No escribe código ni abre PRs.** Es a propósito: la defensa es una regla que el código impone, no un parche que un modelo inventa.
- **No entrena modelos.** Aprende en el sentido de un sistema inmune: acumula reglas verificadas.
- **La procedencia es léxica**: compara valores con los fragmentos etiquetados. Un atacante que logre que el usuario repita el valor lo vuelve `user`. Para dinero conviene `enforce_invariants`.
- **LangChain y OpenAI Agents no tienen adaptador propio.** Siguen el mismo patrón de dos llamadas que los cuatro adaptadores incluidos.
- **La síntesis con LLM solo corre en modo `live`**; en `demo` y `offline` las reglas se derivan de forma determinista del invariante roto y de la procedencia. En `live`, si la política del modelo bloquea menos inyecciones simuladas que la derivada, se le suman las reglas derivadas: el modelo puede añadir defensa, nunca quitarla.

## La arena: el laboratorio en vivo

La arena es Agent Zero aplicado a un asistente de soporte sintético de Yummy, con audiencia. Los participantes atacan desde el teléfono, el Prober ataca en paralelo, y la pantalla muestra cada hallazgo convertido en política, la repetición en pantalla partida, el señuelo y la curva de éxito del ataque por versión.

Empezar por [continuidad y traspaso](./docs/continuidad.md). El [índice documental](./docs/README.md) reúne la ruta de lectura; los [documentos por dominio](./docs/dominio/README.md) enlazan código, contratos, persistencia, invariantes, pruebas y próximos pasos.

## Estado comprobado

| Área | Resultado |
| --- | --- |
| Backend | 1176 pruebas aprobadas en SQLite; las del Guard también contra Postgres 17; Ruff, formato y mypy estricto aprobados (24 oct). |
| Frontend | 92 pruebas aprobadas; Biome, TypeScript y build aprobados (24 oct). Panel del Guard revisado en el navegador sobre la pila Docker. |
| Guard agnóstico | Tres contratos (comida, banca, clínica): cada invariante produce una política activa, el ataque repetido queda bloqueado y todas las tareas legítimas siguen pasando. Las demos de Python, MCP y Node corren contra la pila Docker completa (Postgres) y un contrato dado de alta por API aprende y bloquea igual. Síntesis LIVE con Haiku: 3 llamadas, US$0.0013, políticas aceptadas por la compuerta en banca y clínica. |
| Comparación DEMO | 270 ejecuciones y 732 llamadas simuladas; 90/90 → 0/90 violaciones, utilidad 45/45 en ambas versiones. |
| Ciclo LIVE | Once comprobaciones, 93 llamadas de cinco roles; parche, repetición protegida, señuelo, Prober, reversión y archivo. Coste estimado US$0.0101596 desde tokens y tarifas configuradas. |

La [guía de pruebas](./docs/pruebas/README.md) distingue resultados históricos, comandos y comprobaciones documentales. Los [artefactos y hashes](./docs/pruebas/evidencias.md) conservan procedencia. La comparación amplia con un LLM real, la revisión visual, la prueba de carga y el despliegue público siguen pendientes. Las tasas DEMO no son métricas de eficacia de un LLM real.

## Arranque con Docker

Desde la raíz, con Docker y Compose disponibles:

```bash
test -f .env || cp .env.example .env
make up
make smoke
```

El ejemplo selecciona `demo` y no requiere una clave de IA. Si ya existe `.env`, revisar sus valores: se conserva y podría seleccionar otro modo. Personalizar `AGENT_ZERO_OPERATOR_SECRET` antes de compartir acceso.

Abrir `http://localhost:8080/` para participar, `/arena` para proyectar y `/operator` para operar. El operador utiliza el secreto de su `.env`. `make smoke` sólo comprueba salud, rutas, autorización y proxy SSE.

Para recorrer utilidad → violación → validación → activación → repetición impedida → revelación sobre una ronda base abierta:

```bash
make smoke-exercise
```

Este comando crea datos y cierra la ronda al revelar. Otro ensayo requiere reset archivado explícito y drenaje, descritos en [pruebas de integración](./docs/pruebas/README.md#integración-http-en-contenedores). `make down` conserva el volumen. El QR se genera localmente; una dirección `localhost` no permite entrar desde otro teléfono.

## Desarrollo y regresión

Requisitos: Python 3.12 con uv, Node 24 y pnpm 10.28.2. Instalar con los lockfiles:

```bash
(cd backend && uv sync --frozen)
(cd frontend && pnpm install --frozen-lockfile)
test -f .env || cp .env.example .env
make arena-server ARENA_MODE=demo
```

En otra terminal, desde la raíz: `make dev-frontend`. Vite abre en `http://localhost:5173/` y redirige `/api` al backend del puerto 8000. Para proveedor real, configurar su clave local y ejecutar `make arena-server ARENA_MODE=live`.

Ejecutar las pruebas en una terminal sin la configuración del servidor exportada:

```bash
make check
(cd frontend && pnpm build)
```

La [matriz por dominio](./docs/pruebas/por-dominio.md) indica la regresión específica de cada cambio. Para ensayar flota, campañas, evaluación de dos políticas o proveedor real, seguir [prueba de flota](./docs/prueba-flota.md), [evals](./docs/dominio/evals.md) y [evidencias](./docs/pruebas/evidencias.md). Estos comandos tienen efectos y presupuestos distintos de `make check`.

## Documentos del equipo

| Documento | Contenido |
| --- | --- |
| [Continuidad](./docs/continuidad.md) | Primera sesión de trabajo, mapa de entrada, límites y backlog concreto. |
| [Arquitectura](./docs/arquitectura.md) | Composición, bases, transacciones y fronteras de confianza reales. |
| [Dominios](./docs/dominio/README.md) | Guía por módulo de producto, autonomía, plataforma, frontend e infraestructura. |
| [Pruebas](./docs/pruebas/README.md) | Preparación, regresión, integración, resultados y registro de evidencia nueva. |
| [Núcleo y API](./docs/nucleo.md) | Arranque operativo, rutas HTTP, ejemplos y límites. |
| [Evaluación](./docs/evaluacion.md) | Modelo de amenaza, métricas, aceptación y comparación reproducible. |
| [Desarrollo](./docs/desarrollo.md) y [equipo](./docs/equipo.md) | Convenciones, CI, revisión, CODEOWNERS y contratos compartidos. |
| [Trazabilidad](./docs/trazabilidad.md) | Requisitos y tests que los demuestran. |

La propuesta del producto está en [project-description.md](./project-description.md), el guion en [demo](./docs/demo.md) y el contexto de construcción en [plan de 36 horas](./docs/plan-36-horas.md).

## Equipo y entrega

- Carlos Eduardo Sanoja ([@CarSanoja](https://github.com/CarSanoja)).
- Fernando Molina Siavato ([@FernandoSiavato](https://github.com/FernandoSiavato)).
- Francisco Bastardo ([@franbastardo](https://github.com/franbastardo)).

[CODEOWNERS](./.github/CODEOWNERS) es la referencia de revisión por ruta. Los metadatos del evento están en [platanus-hack-project.jsonc](./platanus-hack-project.jsonc). `deploy-url` debe contener una URL pública verificada cuando exista; no se incluye una dirección de ejemplo como despliegue realizado.
