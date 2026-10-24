---
fecha: 2026-10-24
autor: "@equipo"
rama: worktree-agent-a8e74895b82f28cc6
pr: pendiente
estado: en revisión
dominios: [guard, frontend]
requisitos: []
---

# Panel del Guard en la consola del operador

## Qué cambió
- Nueva feature `frontend/src/features/guard/` y sección "Guard · contratos y políticas" en `OperatorPage`, que reutiliza el secreto de operador ya en memoria.
- El operador elige un contrato y ve sus versiones de política (versión, padre, estado, fecha, reglas en texto legible e informe de la compuerta con llamadas violatorias bloqueadas, tareas legítimas conservadas e inyecciones simuladas bloqueadas). "Activar" aparece en las propuestas y "Revertir" en la activa.
- Lista de hallazgos con invariantes rotos, versión y resuelto por.
- Formulario para pegar YAML, "Validar" y "Registrar" un contrato nuevo.
- Un 401 o 403 cierra el acceso igual que el resto de la consola. Los resultados se anuncian con `aria-live`.

## Por qué
El Guard ya expone contratos, políticas y hallazgos por API; faltaba una vista para que el operador activara, revirtiera y registrara contratos sin usar curl.

## Archivos
- `frontend/src/features/guard/`: `api.ts`, `GuardPanel.tsx`, `GuardPolicies.tsx`, `GuardPolicyCard.tsx`, `GuardGate.tsx`, `GuardFindings.tsx`, `ContractRegister.tsx`, `guard.css`, `guardFixtures.ts` y un `.test.tsx` por componente.
- `frontend/src/features/operator/OperatorPage.tsx` y su test (mock de `/api/guard/contracts`).

## Cómo se verificó
- `pnpm lint`, `pnpm typecheck` y `pnpm test` en verde.
- Backend en modo demo en el puerto 8031 con directorio de datos temporal. Se generaron datos con `examples/guard/banco_demo.py`. Los tipos y los fixtures salen de las respuestas reales de `GET /api/guard/banco-transferencias/policies` y `/findings`, y de `GET /api/guard/contracts`.
- Contra el backend real: `activate` sobre una política activa respondió 409 con `{detail}`; `rollback` de la versión 2 la dejó `rolled_back` y reactivó la 1; `validate` devolvió `valid: false` con `error` para un YAML incompleto y `valid: true` para el contrato de la clínica; sin cabecera, 401.

## Riesgos y efectos en otros frentes
- `POST /api/guard/contracts` (registro) y el campo `source` de `summary` los implementa otro frente. El panel los usa según el contrato acordado (201 `{contract}`, 409 y 422 con `{detail}`), pero no se probaron contra el backend real. `source` es opcional en los tipos.
- El panel consulta contratos, políticas y hallazgos cada 4 s mientras la consola está abierta.

## Pendiente
- Probar el registro contra el backend integrado.
- Ninguna propuesta real apareció en la demo (el modo demo activa automáticamente), así que "Activar" solo se probó con fixtures y el 409 real.
