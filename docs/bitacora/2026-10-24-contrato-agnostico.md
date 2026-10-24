---
fecha: 2026-10-24
autor: "@CarSanoja"
rama: feat/contrato-agnostico
pr: directo a main (issue 30)
estado: integrado
dominios: [contract, guard, victim]
requisitos: []
---

# Contrato de dominio declarativo y Guard para agentes de cualquier negocio

## Qué cambió

- `backend/src/agent_zero/contract/`: esquema del contrato en YAML (herramientas, tipos de argumento, invariantes, tareas legítimas), cinco condiciones, procedencia léxica compartida y variantes de ataque por invariante.
- `backend/src/agent_zero/guard/`: API `/api/guard` con `check` antes de cada herramienta y `effects` después; hallazgos, síntesis o derivación de reglas, compuerta contra las tareas legítimas, activación, aprobación y reversión.
- `backend/contracts/`: tres contratos (Yummy, banca y clínica) que usan el mismo código.
- `examples/guard/`: cliente de referencia en Python 3.9+ sin dependencias y un agente bancario de ejemplo.
- README reescrito con la explicación de producto; guía en `docs/integracion.md` y dominio en `docs/dominio/guard.md`.

## Por qué

La arena demuestra el bucle sobre un único escenario cuyos oráculos están en código. Para que una empresa lo use, la parte de negocio tiene que declararse y el motor tiene que ser genérico.

## Archivos compartidos tocados

`config.py` (dos ajustes: `guard_api_key`, `contracts_dir`), `main.py` (router y construcción del Guard), `victim/provenance.py` (usa la procedencia de `contract/`, mismo comportamiento), `backend/Dockerfile` (copia `contracts/` a la imagen), `.env.example`.

## Cómo se verificó

- Backend tras rebase sobre `03c0369`: 1112 pruebas aprobadas, dos LIVE omitidas; Ruff, formato y mypy estricto aprobados. Frontend: 68 pruebas, Biome y tipos aprobados.
- `tests/guard/test_router.py` recorre por HTTP cada invariante de los tres contratos.
- `examples/guard/banco_demo.py` contra un servidor real en modo demo (puerto 8013): el ataque de 900 USD inyectado por correo se bloquea por invariante, se aprende la versión 1, una inyección de 40 USD que no rompe ningún invariante queda bloqueada por la regla de procedencia y las transferencias legítimas siguen ejecutándose.
- `[SUPUESTO]` La imagen Docker con `contracts/` no se construyó: Docker no estaba disponible.

## Riesgos y efectos en otros frentes

- Fuera de local, sin `AGENT_ZERO_GUARD_API_KEY` de 32 caracteres o más, los endpoints del Guard responden 503; la arena no se ve afectada.
- La síntesis con LLM solo corre en `live` y no se probó con el proveedor real.

## Pendiente

Vista en la consola del operador, adaptadores MCP y de frameworks, condiciones con ventana temporal, alta de contratos por API y multi-inquilino.
