#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/../production.env.example"
TARGET="${1:-.env}"

if [ -e "${TARGET}" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "${TARGET} ya existe. Usa FORCE=1 para sobrescribirlo." >&2
  exit 1
fi

random() {
  openssl rand -hex "$1"
}

umask 077
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT

while IFS= read -r line; do
  case "${line}" in
    AGENT_ZERO_OPERATOR_SECRET=*) echo "AGENT_ZERO_OPERATOR_SECRET=$(random 32)" ;;
    AGENT_ZERO_GUARD_API_KEY=*) echo "AGENT_ZERO_GUARD_API_KEY=$(random 32)" ;;
    AGENT_ZERO_IDENTITY_SIGNING_KEY=*) echo "AGENT_ZERO_IDENTITY_SIGNING_KEY=$(random 32)" ;;
    AGENT_ZERO_MEMORY_ENCRYPTION_KEY=*) echo "AGENT_ZERO_MEMORY_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')" ;;
    POSTGRES_PASSWORD=*) echo "POSTGRES_PASSWORD=$(random 24)" ;;
    *) echo "${line}" ;;
  esac
done < "${TEMPLATE}" > "${tmp}"

install -m 600 "${tmp}" "${TARGET}"
echo "Generado ${TARGET} (permisos 600). Edita AGENT_ZERO_DOMAIN, ACME_EMAIL y, si aplica, AGENT_ZERO_LLM_*."
