# AGENT ZERO

**Arena de red teaming autónomo con defensa en vivo.**

<img src="./project-logo.png" alt="Logo del proyecto" width="200" />

Agent Zero encuentra fallos en agentes de IA mediante ataques automatizados y participativos, propone parches de política, los valida y activa la defensa durante la misma sesión. Una arena pública permite observar ataques, bloqueos y desvíos a un honeypot con datos sintéticos.

> Mientras otros construyen el escudo, nosotros construimos al atacante autónomo que encuentra las grietas y ayuda a sellarlas en tiempo real.

**Track:** 🛡️ AI Security · **Evento:** Platanus Hack 26: Caracas ft. Yummy · **Equipo:** team-4.

## Estado

Este repositorio contiene la propuesta, la especificación y el esqueleto del MVP: backend y frontend por dominios, contenedores y CI. El ciclo de ataque, análisis y parcheo y el despliegue están pendientes de implementación. Las capacidades y métricas descritas son objetivos de construcción y validación, salvo indicación expresa de evidencia obtenida.

## Cómo funciona

1. Un agente atacante genera y muta intentos contra un asistente de soporte con clientes, pedidos y herramientas simulados.
2. El analizador comprueba si hubo una violación y relaciona el resultado con su causa probable.
3. El generador propone una política declarativa y la prueba contra ataques y tareas legítimas.
4. El motor activa la nueva versión, bloquea acciones indebidas o desvía sesiones a un entorno señuelo aislado.
5. La arena muestra la evolución y permite repetir el mismo ataque antes y después del parche.

El MVP adapta políticas y controles; no reentrena el modelo. Cada parche necesita evidencia de validación, una versión y una vía de reversión.

## Documentación

| Documento | Contenido |
| --- | --- |
| [Descripción del proyecto](./project-description.md) | Problema, propuesta, usuarios, diferenciación, alcance y evolución. |
| [Arquitectura](./docs/arquitectura.md) | Módulos, límites de confianza, datos, contratos y activación de políticas. |
| [Evaluación](./docs/evaluacion.md) | Amenazas, oráculos, métricas y criterios de aceptación. |
| [Demo en vivo](./docs/demo.md) | Experiencia pública, clasificación, revelación del honeypot y contingencias. |
| [Plan de 36 horas](./docs/plan-36-horas.md) | Prioridades, hitos, distribución de trabajo y entrega. |
| [Desarrollo](./docs/desarrollo.md) | Estructura, convenciones, comandos y CI. |
| [Equipo](./docs/equipo.md) | Frentes, responsables, propiedad del código y flujo de trabajo. |

## Equipo

- Carlos Eduardo Sanoja ([@carsanoja](https://github.com/carsanoja)).
- Fernando Molina Siavato ([@fernandosiavato](https://github.com/fernandosiavato)).
- Francisco Bastardo ([@franbastardo](https://github.com/franbastardo)).

## Entrega y despliegue

Los metadatos de votación están en [platanus-hack-project.jsonc](./platanus-hack-project.jsonc). Falta registrar una URL pública verificada en `deploy-url` cuando exista el despliegue. El logo existente cumple las dimensiones de 1000 × 1000 píxeles y ocupa menos de 500 KB; su identidad visual queda por revisar.

Según la plantilla del evento, las integraciones de despliegue deben conectarse a un repositorio personal y este repositorio se conserva como destino de entrega al jurado. Las imágenes de contenedor no dependen del proveedor; el destino de despliegue está pendiente.

## Desarrollo

```bash
cp .env.example .env
make install
make up && make smoke
```

Requisitos, estructura por dominios, convenciones y CI en [docs/desarrollo.md](./docs/desarrollo.md).
