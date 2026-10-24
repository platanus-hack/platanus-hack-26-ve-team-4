# AGENT ZERO

**Arena de red teaming autónomo con defensa en vivo.**

<img src="./project-logo.png" alt="Logo del proyecto" width="200" />

Agent Zero ejecuta ataques contra un asistente de soporte sintético, verifica efectos con oráculos, deriva controles declarativos, valida seguridad y utilidad y activa una política nueva durante la misma ronda. La audiencia y el Prober participan con orígenes separados; un señuelo aislado permite estudiar éxitos aparentes.

**Track:** AI Security · **Evento:** Platanus Hack 26: Caracas ft. Yummy · **Equipo:** team-4.

## Para continuar el proyecto

Empezar por [continuidad y traspaso](./docs/continuidad.md). El [índice documental](./docs/README.md) reúne la ruta de lectura; los [documentos por dominio](./docs/dominio/README.md) enlazan código, contratos, persistencia, invariantes, pruebas y próximos pasos.

La implementación está publicada en `core/complete-autonomous-loop` en el repositorio de organización y el espejo personal. Consultar el estado de la rama y la revisión antes de asumir que está integrada en `main`.

## Estado comprobado

Verificación funcional de referencia del 24 de octubre de 2026:

| Área | Resultado |
| --- | --- |
| Backend | 860 pruebas aprobadas, dos LIVE opcionales omitidas y cero warnings; Ruff, formato y mypy estricto aprobados. |
| Frontend | 47 pruebas aprobadas; Biome, TypeScript y build aprobados. |
| Contenedores/flota | Ambas imágenes construidas, smoke HTTP completo y recorrido original de flota 22/22. |
| Comparación DEMO | 270 ejecuciones y 732 llamadas simuladas; 90/90 → 0/90 violaciones, utilidad 45/45 en ambas versiones. |
| Ciclo LIVE | Once comprobaciones, 93 llamadas de cinco roles; parche, repetición protegida, señuelo, Prober, reversión y archivo. Coste estimado US$0.0101596 desde tokens y tarifas configuradas. |

La [guía de pruebas](./docs/pruebas/README.md) distingue resultados históricos, comandos y comprobaciones documentales. Los [artefactos y hashes](./docs/pruebas/evidencias.md) conservan procedencia y el primer ensayo LIVE que agotó el timeout del verificador. La comparación amplia con un LLM real, la revisión visual, la prueba de carga y el despliegue público siguen pendientes. Las tasas DEMO no son métricas de eficacia de un LLM real.

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
