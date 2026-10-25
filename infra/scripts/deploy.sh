#!/usr/bin/env bash
set -euo pipefail

INFRA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${INFRA_DIR}"

ENV_FILE="${ENV_FILE:-${INFRA_DIR}/.env}"
PROJECT="${COMPOSE_PROJECT_NAME:-agent-zero}"
MIN_SECRET_LENGTH=32

if [ ! -f "${ENV_FILE}" ]; then
  echo "Falta ${ENV_FILE}. Genera uno con scripts/generate-secrets.sh." >&2
  exit 1
fi

read_var() {
  grep -E "^$1=" "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true
}

fail=0
if grep -qE "^[A-Z_]+=reemplazar" "${ENV_FILE}"; then
  echo "El .env conserva valores de la plantilla (reemplazar-...)." >&2
  fail=1
fi
require_length() {
  local value
  value="$(read_var "$1")"
  if [ "${#value}" -lt "$2" ]; then
    echo "$1 mide ${#value} caracteres; el mínimo es $2." >&2
    fail=1
  fi
}

require_length AGENT_ZERO_OPERATOR_SECRET "${MIN_SECRET_LENGTH}"
require_length AGENT_ZERO_GUARD_API_KEY "${MIN_SECRET_LENGTH}"
require_length AGENT_ZERO_IDENTITY_SIGNING_KEY "${MIN_SECRET_LENGTH}"
require_length AGENT_ZERO_MEMORY_ENCRYPTION_KEY 44
require_length POSTGRES_PASSWORD 16
require_length AGENT_ZERO_DOMAIN 3
require_length ACME_EMAIL 3

if [ "$(read_var AGENT_ZERO_ENVIRONMENT)" != "production" ]; then
  echo "AGENT_ZERO_ENVIRONMENT debe ser production." >&2
  fail=1
fi

mode="$(read_var AGENT_ZERO_LLM_MODE)"
if [ "${mode}" = "live" ]; then
  require_length AGENT_ZERO_LLM_API_KEY 20
elif [ "${mode}" != "demo" ]; then
  echo "AGENT_ZERO_LLM_MODE debe ser live o demo." >&2
  fail=1
fi

if [ "${fail}" -ne 0 ]; then
  exit 1
fi

DOMAIN="$(read_var AGENT_ZERO_DOMAIN)"
TAG="${AGENT_ZERO_IMAGE_TAG:-$(read_var AGENT_ZERO_IMAGE_TAG)}"
TAG="${TAG:-latest}"
export AGENT_ZERO_IMAGE_TAG="${TAG}"

compose() {
  docker compose -p "${PROJECT}" --env-file "${ENV_FILE}" -f compose.prod.yaml "$@"
}

previous="$(docker inspect --format '{{.Config.Image}}' "${PROJECT}-backend-1" 2>/dev/null || true)"

echo "Desplegando con AGENT_ZERO_IMAGE_TAG=${TAG}"
compose pull
compose up -d --wait --remove-orphans

SMOKE_URL="${SMOKE_URL:-https://${DOMAIN}}"
if "${INFRA_DIR}/scripts/smoke.sh" "${SMOKE_URL}"; then
  echo "Despliegue verificado en ${SMOKE_URL}"
  exit 0
fi

echo "El smoke falló contra ${SMOKE_URL}." >&2
if [ -n "${previous}" ]; then
  echo "Imagen anterior del backend: ${previous}" >&2
fi
echo "Para volver atrás: AGENT_ZERO_IMAGE_TAG=<tag-anterior> ${INFRA_DIR}/scripts/deploy.sh" >&2
exit 1
