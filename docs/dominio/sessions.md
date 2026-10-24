# `sessions`: participantes e identidad sintética

Categoría: arena · Responsable: Francisco · Issues: #4

## Propósito

Representa a cada participante: su alias, el cliente sintético que le toca y la ruta en la que está. Es la única fuente de la identidad del cliente durante un intento.

## Estado inicial del diseño

La implementación actual, sus contratos y pruebas están en [núcleo implementado](../nucleo.md). El inventario siguiente conserva el punto de partida de esta especificación.

| Archivo | Contenido |
| --- | --- |
| `models.py` | `ArenaSession`: `id`, `alias`, `customer_id`, `route`, `created_at`. |
| `schemas.py` | `SessionCreate` (alias de 2 a 40 caracteres) y `SessionRead`. |
| `session_creation_service.py` | Asigna un cliente sintético al azar y ruta `protected`. |
| `repository.py`, `router.py` | `POST /api/sessions` devuelve 201 con `id`, `alias` y `created_at`. |

Falta el token firmado: hoy cualquier cliente que conozca un `id` de sesión podría usarlo.

## Responsabilidades

1. Crear la sesión tras aceptar las reglas de participación.
2. Emitir un token de sesión firmado con HMAC, con vencimiento y sin datos personales.
3. Verificar el token en cada intento y resolver `customer_id` y ruta del lado del servidor.
4. Aplicar cupo de sesiones por ronda.
5. Cambiar la ruta a `honeypot` cuando lo decida `routing`, de forma definitiva.
6. Cerrar todas las sesiones al reiniciar la ronda.

## Contratos

| Contrato | Campos |
| --- | --- |
| `SessionCreate` | `alias`, aceptación de reglas. |
| `SessionIssued` | `id`, `alias`, `token`, `expires_at`, cliente visible (nombre ficticio), objetivos de la ronda. |
| Token | `session_id`, `exp`, firma; nunca `customer_id` en claro. |

## Eventos

- **Produce:** `route_changed` cuando la sesión pasa al señuelo, con visibilidad `operator`.
- **Consume:** decisiones de `routing`.

## Reglas

- El alias no puede contener datos personales evidentes; se pasa por la redacción de PII de Armor.
- La ruta solo cambia de `protected` a `honeypot`, nunca al revés.
- El token de sesión no sirve para rutas de operación; esas usan el secreto de operador.

## Uso de la flota

- `identity` aporta la firma HMAC y el patrón de vencimiento; el token de sesión es distinto de la credencial del agente.
- `armor` redacta PII del alias.

## Estructura prevista

| Archivo | Responsabilidad |
| --- | --- |
| `session_token.py` | Firma y verificación del token. |
| `session_creation_service.py` | Creación con cupo. |
| `session_route_service.py` | Cambio de ruta. |
| `dependencies.py` | `CurrentSession` para FastAPI. |

## Pruebas de éxito

- Un token alterado o vencido devuelve 401.
- Dos sesiones distintas nunca comparten `customer_id` en la misma ronda cuando hay cupo.
- Una sesión en `honeypot` no puede volver a `protected`.
