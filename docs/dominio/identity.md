# Identity: credenciales y revocación

Estado: implementado. Autentica agentes de la flota antes de ejecutar herramientas o acceder a memoria. Los tokens de participantes pertenecen a [sessions](./sessions.md); el secreto de operación autoriza la API administrativa. Son tres contratos distintos.

## Código y flujo

| Archivo | Función |
| --- | --- |
| [schemas.py](../../backend/src/agent_zero/identity/schemas.py) | `AgentGrant`, `AgentPrincipal` e `IssuedCredential`, cerrados e inmutables. |
| [token_codec.py](../../backend/src/agent_zero/identity/token_codec.py) | Codificación y comprobación de la credencial firmada. |
| [credential_issuer.py](../../backend/src/agent_zero/identity/credential_issuer.py) | Emisión con id de credencial, versión, scopes, clasificación, regiones y vencimiento. |
| [credential_verifier.py](../../backend/src/agent_zero/identity/credential_verifier.py) | Firma/formato, expiración, revocación y scope solicitado. |
| [revocation_service.py](../../backend/src/agent_zero/identity/revocation_service.py) | Revoca una credencial, un agente o una versión. |
| [registry_admission.py](../../backend/src/agent_zero/fleet/registry_admission.py) | Sólo deriva grants de manifiestos aprobados e íntegros. |
| [token_vault.py](../../backend/src/agent_zero/fleet/token_vault.py), [vault_principal_guard.py](../../backend/src/agent_zero/fleet/vault_principal_guard.py) | Custodian el token y vuelven a comprobar el principal presentado. |

La admisión emite una credencial para cada paso del runtime. `TokenVault` conserva el token en memoria; el handler recibe un principal y un acceso a herramientas ligado a esa identidad. La memoria compara el principal recibido con la credencial verificada: copiarlo y ampliar sus scopes no funciona.

Los scopes tienen forma `recurso:accion`, por ejemplo `memory:read` o `tool:get_order`. La clasificación sigue `public < internal < confidential < restricted`; las regiones autorizadas se contrastan después en el gateway.

## Persistencia y configuración

Las revocaciones se guardan en `identity_revoked_credentials` y `identity_revoked_agents`, dentro de `app.db`; [models.py](../../backend/src/agent_zero/identity/models.py) es la referencia de campos y razones de negación. La bóveda de tokens no se persiste. Al recuperar un run, la admisión genera otra credencial y consulta las revocaciones persistidas.

| Variable | Uso |
| --- | --- |
| `AGENT_ZERO_IDENTITY_SIGNING_KEY` | Firma de identidad y derivación de la clave de auditoría. |
| `AGENT_ZERO_IDENTITY_TOKEN_TTL_SECONDS` | Vigencia; valor base 900 segundos. |
| `AGENT_ZERO_OPERATOR_SECRET` | API de operación y firma de tokens de participante; usar una clave distinta de la anterior. |

Fuera de `local` y `test`, [startup_guard.py](../../backend/src/agent_zero/fleet/startup_guard.py) exige secretos distintos, de al menos 32 caracteres y diferentes de los valores predeterminados. La memoria exige además una clave Fernet configurada. Los secretos no forman parte de los manifiestos, eventos públicos ni artefactos de prueba.

## Garantías y fronteras

Cada llamada al gateway verifica expiración, revocación y permiso. La revocación no cancela retroactivamente una herramienta que ya terminó: afecta las verificaciones siguientes. El runtime comprueba la admisión al iniciar cada paso, no antes de cada línea de código Python.

`CredentialIssuer` es una primitiva interna capaz de firmar un grant; el requisito de aprobación lo impone `RegistryAdmission`. Para registrar un agente nuevo, usar el camino completo de [registry](./registry.md) y flota, no emitir grants desde datos enviados por el navegador.

## Pruebas

```bash
cd backend
uv run pytest tests/identity -q
uv run pytest tests/fleet/test_registry_admission.py tests/fleet/test_vault_principal_guard.py tests/fleet/test_token_vault.py tests/fleet/test_startup_guard.py -q
```

| Archivo de prueba | Cobertura |
| --- | --- |
| [test_token_codec.py](../../backend/tests/identity/test_token_codec.py) | Credenciales malformadas y alteración de firma. |
| [test_credential_verifier.py](../../backend/tests/identity/test_credential_verifier.py) | Expiración, scopes y razones de rechazo diferenciadas. |
| [test_revocation_service.py](../../backend/tests/identity/test_revocation_service.py) | Persistencia de revocaciones entre sesiones de base de datos. |
| [test_vault_principal_guard.py](../../backend/tests/fleet/test_vault_principal_guard.py) | Un principal modificado no obtiene acceso a memoria. |
| [test_startup_guard.py](../../backend/tests/fleet/test_startup_guard.py) | Configuración local frente a arranque con secretos débiles fuera del laboratorio. |

La fecha, alcance y resultados generales están en [pruebas](../pruebas/README.md). El ensayo de flota verificó por HTTP que un agente revocado deja de ejecutar su siguiente run.

## Continuidad

No existe un servidor OAuth ni una API pública para emitir identidades de agentes. Antes de añadir autenticación externa, conservar la distinción participante/agente/operador, la revocación persistida y la comprobación en cada herramienta. La rotación de la clave de firma necesita un diseño explícito: también cambia la verificación del historial de auditoría derivado de esa clave.
