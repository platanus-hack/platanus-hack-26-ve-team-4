# Bitácora del equipo

Registro cronológico de cada cambio que entra al repo: qué cambió, por qué, cómo se verificó y qué queda pendiente. Sirve para que una persona, o un agente de IA, retome el trabajo sin depender de conversaciones ni de la memoria de quien lo hizo.

La bitácora no reemplaza los documentos de dominio (`docs/dominio/`), que describen cómo funciona el sistema **hoy**. La bitácora cuenta **cómo se llegó ahí**.

## Una entrada por cambio

- **Un archivo por PR**, con el nombre `AAAA-MM-DD-tema-corto.md`. Por ejemplo: `2026-10-24-direcciones-entrega.md`.
- **El nombre ordena por fecha:** para ver lo más reciente, listar la carpeta. No hay un índice que mantener, así que dos PRs en paralelo nunca chocan.
- **La entrada va en el mismo PR que el cambio.** Si el PR cambia en la revisión, se actualiza la entrada.
- **Una entrada ya integrada no se reescribe.** Si algo cambia después, va en una entrada nueva que enlace a la anterior.

## Formato

```markdown
---
fecha: 2026-10-24
autor: "@usuario"
rama: feat/tema
pr: 25            # número del PR, o "pendiente" mientras no exista
estado: en revisión | integrado | descartado
dominios: [victim, evals]
requisitos: [CORE-06]
---

# Título en una línea

## Qué cambió
## Por qué
## Archivos
## Cómo se verificó
## Riesgos y efectos en otros frentes
## Pendiente
```

## Reglas

- **Fechas absolutas,** nunca "hoy" ni "ayer". Si importa la hora, va con zona: "11:00 (Caracas)".
- **Citar rutas, commits y PRs reales.** Algo que no se comprobó va marcado `[SUPUESTO]`.
- **Solo lo hecho.** Un trabajo planeado aparece como una línea en "Pendiente", nunca como entrada propia.
- **Sin secretos:** ninguna clave, contraseña ni contenido del `.env`. Basta con nombrar la variable.
- **Sin textos de ataque,** jailbreaks ni payloads. Los ataques se describen por su estructura.

## Para agentes

Antes de construir algo:
1. Leer las últimas entradas de esta carpeta.
2. Leer `docs/continuidad.md` y el documento del dominio que vas a tocar.
3. Hacer `git pull` de `origin/main`.

Al terminar un cambio, crear su entrada siguiendo el formato.
