# `sessions`: participantes e identidad de sesión

Estado: implementado y revisado contra el código del 24 de octubre de 2026. El dominio identifica al participante; las credenciales de los agentes pertenecen a `identity` y el secreto de Operación es otra credencial.

## Responsabilidad y entradas al código

| Archivo | Responsabilidad |
| --- | --- |
| [models.py](../../backend/src/agent_zero/sessions/models.py) | Tabla `sessions`: `id`, `alias`, `customer_id`, `route`, `created_at`. |
| [schemas.py](../../backend/src/agent_zero/sessions/schemas.py) | Consentimiento obligatorio y proyección `SessionIssued`. |
| [session_creation_service.py](../../backend/src/agent_zero/sessions/session_creation_service.py) | Reserva una identidad disponible, valida alias y provisiona sus pedidos. |
| [session_token.py](../../backend/src/agent_zero/sessions/session_token.py) | Firma y verificación HMAC de tokens con vencimiento. |
| [dependencies.py](../../backend/src/agent_zero/sessions/dependencies.py) | `CurrentSession`: autentica Bearer y exige que la sesión siga en la base. |
| [router.py](../../backend/src/agent_zero/sessions/router.py) | `POST /api/sessions` y `GET /api/sessions/me`. |
| [fixtures.py](../../backend/src/agent_zero/victim/fixtures.py) | Identidades sintéticas y pedidos adicionales generados. |

`SessionRepository` ofrece consultas y persistencia; la operación pública de creación debe pasar por `create_session`, que aplica exclusión de escritura con SQLite. [Routing](routing.md) cambia la ruta y [Arena](arena.md) invalida sesiones al reiniciar.

## Contratos públicos

| Operación | Entrada / salida |
| --- | --- |
| `POST /api/sessions` | JSON `{"alias":"equipo-a","accepted_rules":true}`; 201 con `id`, `alias`, `created_at`, `token`, `expires_at`, `customer_name`, `order_ids`, `objectives` y `limits`. |
| `GET /api/sessions/me` | `Authorization: Bearer <token>`; devuelve identidad visible, fechas, pedidos y límites. No renueva ni vuelve a emitir el token. |
| Token | Cuerpo base64url con `session_id` y `exp`, más firma HMAC-SHA256. No incluye `customer_id`. |
| Error de autenticación | 401 para token ausente, alterado, vencido o sesión eliminada. |
| Error de creación | 422 por esquema inválido; 409 por alias ocupado, ronda cerrada o capacidad agotada. |

El cliente visible es ficticio. El `customer_id` que autoriza herramientas se resuelve desde la fila de sesión y viaja en `CallContext`; no se acepta desde un mensaje del participante.

## Invariantes y persistencia

- `accepted_rules` debe ser literalmente `true`; el esquema rechaza campos extra. Alias: 2–40 caracteres, caracteres de palabra Unicode, guion y espacios según el patrón del esquema; se recorta y se redacta PII con Armor.
- La comparación de alias de participantes no distingue mayúsculas. La asignación de clientes y esa comprobación ocurren bajo `BEGIN IMMEDIATE`; dos asignadores sobre el mismo SQLite no reservan la misma identidad pública.
- La ruta inicial es `protected`. El cambio a `honeypot` es permanente para esa sesión; sólo [routing](routing.md) debe decidirlo.
- `AGENT_ZERO_ARENA_SESSION_LIMIT` vale 100 por defecto y admite 1–500. Los clientes semilla se amplían con identidades `cust-demo-*` y pedidos `D-*` provisionados en protegido y señuelo.
- El cupo cuenta participantes `sess-*`; las sesiones internas del Prober y de repetición no consumen esas plazas. La unicidad de cliente se garantiza entre participantes de una ronda, no entre todos los runs internos.
- Vencer un token no libera su plaza ni borra su fila. El reset archivado de [Arena](arena.md) elimina las sesiones de la ronda y los tokens anteriores pasan a 401.
- El TTL de emisión es `AGENT_ZERO_ARENA_SESSION_TTL_SECONDS` (3600 s por defecto). Cambiar configuración no reemite un token ya entregado.
- La clave de sesión se deriva de `identity_signing_key` con un contexto propio. Un token de participante no autoriza Operación ni sustituye una credencial de agente.

La creación persiste en `app.db`; los pedidos se provisionan en archivos de entorno separados. No es una transacción distribuida entre tres bases: si la creación falla después de provisionar, puede quedar un cliente sembrado sin sesión, y la provisión idempotente permite reintentar.

## Pruebas y cómo repetirlas

Desde la raíz, en un entorno de pruebas sin variables del servidor exportadas:

```bash
cd backend
uv run pytest tests/sessions tests/arena/test_core_cycle.py tests/arena/test_admission_and_campaign.py tests/arena/test_round_reset.py -q
```

| Prueba existente | Qué protege |
| --- | --- |
| [test_router.py](../../backend/tests/sessions/test_router.py) | Proyección pública, límites y rechazo del alias inválido. |
| [test_admission_and_campaign.py](../../backend/tests/arena/test_admission_and_campaign.py) | Firma, vencimiento, dueño de intentos, identidades distintas y pausa. |
| [test_core_cycle.py](../../backend/tests/arena/test_core_cycle.py) | Token, envío idempotente y ausencia de campos privados en la vista del participante. |
| [test_round_reset.py](../../backend/tests/arena/test_round_reset.py) | Más de tres participantes, 20 asignadores concurrentes, cupo, archivo e invalidación tras reset. |
| [test_patch_explanation.py](../../backend/tests/arena/test_patch_explanation.py) | Un cliente generado completa utilidad, ataque, validación y repetición del parche. |

Estas pruebas formaron parte de la verificación backend de 860 aprobadas y dos LIVE omitidas; no requieren llamadas de pago. Preparación, aislamiento de variables y evidencia en [pruebas](../pruebas/README.md).

## Continuar este dominio

Si se añade renovación o recuperación del token, definir primero expiración, revocación y cómo recuperar identidad sin permitir que un alias público actúe como contraseña. Hoy `/me` sólo valida una credencial existente.

Si se desea liberar capacidad al vencer una sesión, actualizar la asignación y las reglas de historial/ronda juntas; reutilizar un cliente con pedidos modificados cambia el escenario. Mantener pruebas de asignación concurrente, propietario y reset. Las 500 identidades configurables son capacidad funcional, no una medición de 500 participantes atendidos simultáneamente.
