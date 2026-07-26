#!/usr/bin/env bash
# Run the Playwright e2e suite against an ISOLATED test stack (own Postgres +
# backend + frontend, ephemeral DB). Never touches the dev database.
#
# Usage:
#   scripts/e2e.sh                       # whole suite
#   scripts/e2e.sh tests/api_receive.spec.js -g "receive"   # forwarded to playwright
#
# Leaves the stack up between runs for speed; tear down with:
#   scripts/e2e.sh --down
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT=comnet_test
COMPOSE=(docker compose -f docker-compose.test.yml -p "$PROJECT")

if [[ "${1:-}" == "--down" ]]; then
  "${COMPOSE[@]}" --profile test down -v
  exit 0
fi

# Bring the stack up (idempotent) and wait for backend health.
"${COMPOSE[@]}" up -d --build postgres backend frontend

echo "⏳ waiting for test backend to be healthy…"
until [ "$("${COMPOSE[@]}" ps -q backend | xargs -r docker inspect -f '{{.State.Health.Status}}' 2>/dev/null)" = "healthy" ]; do
  sleep 2
done

# Mount the live tests dir so edits are picked up without rebuilding the image.
"${COMPOSE[@]}" --profile test run --rm \
  -v "$PWD/tests/e2e/tests:/e2e/tests" \
  playwright npx playwright test "$@"
