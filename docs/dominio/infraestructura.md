# Infraestructura: arranque, contenedores y verificaciones

Estado: configuración revisada sobre la base funcional `1d0e21d`. La entrega es una API FastAPI con workers internos, un frontend estático servido por nginx y SQLite persistente. El repositorio contiene imágenes construibles; una URL pública comprobada sigue pendiente.

## Entradas de ejecución

| Archivo | Responsabilidad |
| --- | --- |
| [main.py](../../backend/src/agent_zero/main.py) | Crea esquema, flota y gateway LLM; inicializa/reanuda núcleo y arranca workers. |
| [config.py](../../backend/src/agent_zero/config.py) | Fuente de variables `AGENT_ZERO_*`, valores por defecto y límites de configuración. |
| [.env.example](../../.env.example) | Configuración de demostración sin clave del proveedor. |
| [backend/Dockerfile](../../backend/Dockerfile) | Python 3.12, uv fijado, instalación congelada sin dependencias de desarrollo y usuario sin privilegios. |
| [frontend/Dockerfile](../../frontend/Dockerfile) | Node 24/pnpm, build congelado y nginx sin privilegios. |
| [compose.yaml](../../infra/compose.yaml) | Backend, frontend, dependencia de salud, puerto y volumen persistente. |
| [smoke.py](../../infra/scripts/smoke.py) | Verificación HTTP de sólo lectura y ejercicio explícito del ciclo completo. |
| [ci.yml](../../.github/workflows/ci.yml) | Definición de validación, contenedores y publicación de imágenes. |

## Configuración y persistencia

El ejemplo configura `demo`, 100 plazas, 5000 llamadas diarias y 1200 por campaña. Los valores internos de `Settings` no son idénticos en todos los casos: por ejemplo, el modo interno por defecto es `offline` y el límite de campaña 300. Para un ensayo amplio usar el ejemplo o establecer explícitamente el presupuesto requerido.

`Settings` lee `.env` relativo al directorio de ejecución. Los targets de servidor del [Makefile](../../Makefile) cargan el `.env` de la raíz antes de entrar en `backend/`. Evitar cargar ese archivo en la terminal de pruebas unitarias: variables exportadas pueden alterar los fixtures; consultar [pruebas](../pruebas/README.md).

Compose exige `AGENT_ZERO_OPERATOR_SECRET` mediante interpolación. Se puede definir en el `.env` de la raíz o exportarlo; no basta asumir un secreto no suministrado. No se incorpora al bundle: el operador lo introduce en la UI y ésta lo conserva sólo en memoria durante la visita.

El volumen `agent-zero-data` monta `/data` y conserva `app.db`, `protected.db`, `honeypot.db`, ledger/cassettes LLM y auditoría. `make down` conserva el volumen; `down --volumes` elimina los datos y se reserva al entorno efímero de CI o a una limpieza deliberada. Cambiar claves de memoria/firma sin un plan afecta descifrado, credenciales y verificación de auditoría.

Fuera de `local`/`test`, el arranque exige secretos de operador/firma distintos y de al menos 32 caracteres, y una clave Fernet de memoria explícita. Revisar [startup_guard.py](../../backend/src/agent_zero/fleet/startup_guard.py) y el dominio de [memoria](./memory-bank.md) antes de configurar otro entorno.

## Arranque local reproducible

Desde la raíz, con Docker y Compose instalados:

```bash
test -f .env || cp .env.example .env
make up
make smoke
```

Abrir `http://localhost:8080/`, `/arena` y `/operator`. `FRONTEND_PORT=18080 make up` cambia el puerto del host; en ese caso pasar la URL al smoke:

```bash
./infra/scripts/smoke.sh http://localhost:18080
```

La imagen del frontend recibe `VITE_PUBLIC_PARTICIPANT_URL` durante build; cambiarla exige reconstruir para fijar el nuevo valor predeterminado del QR. La edición de la tarjeta de la arena sólo afecta esa visita.

Para desarrollo sin Docker, instalar las dependencias según [desarrollo](../desarrollo.md), ejecutar `make arena-server ARENA_MODE=demo` y, en otra terminal, `make dev-frontend`. `ARENA_DATA` es relativo a `backend/`; una ruta absoluta evita dudas. El modo `live` consume proveedor y requiere su clave configurada.

## Proxy, caché y salud

[default.conf.template](../../frontend/nginx/default.conf.template) atiende las rutas SPA y redirige `/api/` a `BACKEND_URL`. Usa HTTP/1.1, sin buffer ni caché para SSE/API y timeout de lectura de una hora. Assets con hash llevan caché inmutable; el documento HTML debe revalidarse. [security-headers.conf](../../frontend/nginx/security-headers.conf) establece CSP del mismo origen, `nosniff`, política de referencias y bloqueo de frames.

`/healthz` comprueba nginx; `/readyz` consulta `/health` del backend. El healthcheck del contenedor frontend usa `/healthz`, por lo que un frontend `healthy` por sí solo no demuestra disponibilidad del backend. El smoke verifica ambas capas, autorización y SSE. Estos endpoints no sustituyen una ejecución de negocio.

## Pruebas hechas y cómo repetirlas

La verificación previa construyó ambas imágenes y pasó por nginx: SPA, readiness, API pública, autorización, SSE y el ejercicio útil → violación → ocho validaciones → activación → replay protegido impedido → revelación. También comprobó reset con archivado. No se afirma despliegue público ni revisión visual de navegador.

`make smoke` sólo lee estado. Para crear intentos y cerrar una ronda base abierta:

```bash
make smoke-exercise
```

Ese target carga el secreto del `.env`. Para repetir sobre otra ronda drenada y archivarla explícitamente:

```bash
set -a
. ./.env
set +a
./infra/scripts/smoke.sh http://localhost:8080 --exercise --reset-round
```

El script falla si el proveedor deja un intento inconcluso, el candidato se rechaza o el replay no queda impedido en protegido. Un 409 de reset exige revisar runs pendientes; no se debe borrar el volumen para ocultarlo. Los tests locales de estado/recuperación están en [arena](./arena.md), y los comandos generales en [pruebas](../pruebas/README.md).

## CI y puntos de continuidad

El YAML define jobs backend y frontend; después construye la pila con un secreto efímero, modo demo y ambos smokes. Publicar imágenes GHCR se limita al push a `main` tras aprobar contenedores. Los disparadores definidos son PR y push a `main`; un push de una rama de trabajo no demuestra que haya corrido CI. Revisar Actions para confirmar que el workflow esté habilitado y ver el resultado remoto.

Los requisitos locales son Python 3.12/uv, Node 24/pnpm fijado por `package.json` y Docker Compose compatible con el archivo. Dependencias se fijan en `uv.lock` y `pnpm-lock.yaml`; una actualización debe pasar build y smoke, además de tests de código.

Pendientes operativos: URL pública y TLS comprobados, respaldo/restauración del volumen, política de migraciones y medición de carga. `create_all` crea tablas faltantes pero no migra columnas existentes. El shutdown normal espera workers y libera recursos; un fallo de inicialización antes del `yield` de lifespan todavía no recorre el mismo bloque de limpieza. Documentar y probar esa ventana al reforzar el ciclo de vida. El archivo de ronda permite consultar evidencia; no existe una operación de restauración de snapshots que sustituya un backup del despliegue.
