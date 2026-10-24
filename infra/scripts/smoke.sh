#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

curl -fsS "${BASE_URL}/healthz" >/dev/null
echo "frontend responde en ${BASE_URL}"

session=$(curl -fsS -X POST "${BASE_URL}/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"alias":"smoke","accepted_rules":true}')
echo "${session}" | grep -q '"id":"sess-' || { echo "sesión inválida: ${session}"; exit 1; }
echo "API crea sesiones a través del proxy"

status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "${BASE_URL}/api/arena/events" || true)
[ "${status}" = "200" ] || { echo "SSE respondió ${status}"; exit 1; }
echo "SSE de la arena abre a través del proxy"

curl -fsS "${BASE_URL}/arena" | grep -q '<div id="root">' || { echo "SPA no sirve /arena"; exit 1; }
echo "SPA resuelve rutas del cliente"
