# Shared y configuración

Estado: implementado. Son primitivas comunes y composición de arranque; no contienen las reglas de titularidad, reembolso o clasificación de hallazgos.

| Archivo | Responsabilidad |
| --- | --- |
| [config.py](../../backend/src/agent_zero/config.py) | `Settings` y nombres `AGENT_ZERO_*`. |
| [database.py](../../backend/src/agent_zero/shared/database.py) | Motor async, fábrica de sesiones, `AppBase`, creación y disposición. |
| [dependencies.py](../../backend/src/agent_zero/shared/dependencies.py) | Sesión de DB por petición y broker de la aplicación. |
| [clock.py](../../backend/src/agent_zero/shared/clock.py), [ids.py](../../backend/src/agent_zero/shared/ids.py) | Reloj UTC e identificadores. |
| [classification.py](../../backend/src/agent_zero/shared/classification.py) | Orden `public < internal < confidential < restricted`. |
| [health_router.py](../../backend/src/agent_zero/shared/health_router.py) | Endpoint backend `/health`. |
| [main.py](../../backend/src/agent_zero/main.py) | Fábrica FastAPI, estado de app, routers y lifespan. |

## Configuración sin ambigüedad

`Settings` lee variables de entorno y `.env` relativo al directorio de trabajo. Los targets Make de servidor cargan expresamente `../.env` al entrar en `backend/`; Compose interpola el `.env` de la raíz y configura el contenedor. `AGENT_ZERO_DATA_DIR=./data` también es relativo al proceso; usar rutas absolutas para compartir instrucciones entre terminales.

El ejemplo usa `demo`, aunque el valor predeterminado de `Settings.llm_mode` es `offline`. No cargar el `.env` de servidor para ejecutar una regresión normal: cambia los fixtures a través del entorno. Ver [pruebas](../pruebas/README.md) para un proceso hijo limpio.

Una sesión SQLAlchemy se usa dentro de `async with database.sessions()`. Los repositorios no deben conservarla fuera de su owner. `expire_on_commit=False` permite leer entidades devueltas, pero no autoriza a ejecutar nuevas consultas con la sesión cerrada. Las pruebas tratan fugas y excepciones ignoradas como errores.

## Esquema y ciclo de vida

`create_all` crea tablas que faltan; no migra columnas de instalaciones anteriores. `StoreBase` del escenario es separado de `AppBase`, y los entornos añaden su propia tabla de memoria. Revisar [arquitectura](../arquitectura.md) antes de cambiar bases o metadatos.

El cierre normal detiene workers, telemetría y motores. La limpieza ante un fallo de inicialización anterior al `yield` de `main.lifespan` sigue pendiente; no afirmar que la app recupera cualquier fallo de arranque sin recursos abiertos.

## Pruebas y extensión

```bash
cd backend
uv run pytest tests/shared tests/test_main.py tests/fleet/test_startup_guard.py -q
```

[test_health_router.py](../../backend/tests/shared/test_health_router.py), [test_classification.py](../../backend/tests/shared/test_classification.py) y [test_main.py](../../backend/tests/test_main.py) protegen salud, orden y arranque. Las pruebas de persistencia/recuperación se encuentran en runtime/arena y están enlazadas en [la matriz](../pruebas/por-dominio.md).

Al introducir una variable, actualizar `Settings`, `.env.example` sin secretos, Compose si afecta el despliegue, el documento del dominio y las instrucciones de pruebas. Las siguientes mejoras transversales son cleanup de arranque, migraciones y backup/restauración, descritas en [continuidad](../continuidad.md).
