# Documentación del equipo

Punto de entrada para continuar Agent Zero. La implementación y las evidencias de referencia corresponden al 24 de octubre de 2026. Los documentos distinguen comportamiento actual, resultados ejecutados y trabajo pendiente.

## Por dónde empezar

| Necesitas… | Leer |
| --- | --- |
| Incorporarte y elegir la siguiente tarea | [Continuidad y traspaso](./continuidad.md). |
| Saber qué cambió, cuándo y por qué | [Bitácora](./bitacora/README.md): una entrada por PR, con verificación y pendientes. |
| Levantar el producto | [README del repositorio](../README.md) y [núcleo implementado](./nucleo.md). |
| Llevar Agent Zero al agente de una empresa | [Guía de integración](./integracion.md) y [dominio guard](./dominio/guard.md). |
| Entender el flujo y sus transacciones | [Arquitectura](./arquitectura.md) y [flujo de decisión](./dominio/flujo-de-decision.md). |
| Cambiar una parte del código | [Índice por dominio](./dominio/README.md): archivos, contratos, invariantes, pruebas y extensiones. |
| Repetir o elegir pruebas | [Pruebas](./pruebas/README.md) y [matriz por dominio](./pruebas/por-dominio.md). |
| Revisar qué se comprobó | [Evidencias y reproducción](./pruebas/evidencias.md). |
| Preparar una presentación | [Demo](./demo.md); separar ensayo local de despliegue público. |
| Cambiar reglas o medir eficacia | [Evaluación](./evaluacion.md) y [oráculos](./dominio/oracles.md). |
| Coordinar revisión y contratos | [Equipo](./equipo.md), [desarrollo](./desarrollo.md) y [CODEOWNERS](../.github/CODEOWNERS). |

## Mapa de lectura

El [índice de dominios](./dominio/README.md) cubre producto, autonomía, plataforma y frontend/infraestructura. Cada documento enlaza código vigente y tests reales. Los ejemplos no sustituyen los DTO cerrados ni los routers como fuente del contrato exacto.

Los informes guardados en `artifacts/core-evaluation/` son evidencia sintética del laboratorio. DEMO, LIVE y reproducción tienen orígenes distintos; una ejecución simulada no acredita una tasa de eficacia de un proveedor real. Los hashes y el mapa de commits permiten seguir la procedencia.

## Referencias complementarias

| Documento | Función |
| --- | --- |
| [Visión](./dominio/vision.md) | Problema, alcance y aplicación del ciclo. |
| [Casos de uso](./dominio/casos-de-uso.md) | UC-01 a UC-16 y rutas de implementación. |
| [Rendimiento](./dominio/rendimiento.md) | Mediciones existentes frente a metas pendientes. |
| [Prueba de flota](./prueba-flota.md) | Recorrido original de 22 comprobaciones por HTTP. |
| [Trazabilidad](./trazabilidad.md) | Requisitos con IDs y tests que los citan. |
| [Plan de 36 horas](./plan-36-horas.md) | Contexto de construcción y estado de la entrega; no reemplaza el backlog de continuidad. |

Al modificar código, actualizar el documento de dominio, sus contratos públicos y la matriz de pruebas relacionada. Si se agrega un comando, comprobar su directorio de trabajo, configuración y efectos sobre datos antes de documentarlo como reproducible.
