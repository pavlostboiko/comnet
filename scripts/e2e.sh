#!/usr/bin/env bash
# Run the Playwright e2e suite against an ISOLATED test stack (own Postgres +
# backend + frontend, ephemeral DB). Never touches the dev database.
#
# Each run is HERMETIC by default: the stack is recreated so the DB starts empty
# (tmpfs), which keeps tests reproducible and free of cross-run residue.
#
# Usage:
#   scripts/e2e.sh                       # fresh DB, whole suite
#   scripts/e2e.sh tests/api_receive.spec.js -g "receive"   # fresh DB, subset
#   scripts/e2e.sh --keep tests/api_x.spec.js               # reuse running stack (fast, not fresh)
#   scripts/e2e.sh --down                                    # tear the stack down
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT=comnet_test
COMPOSE=(docker compose -f docker-compose.test.yml -p "$PROJECT")

FRESH=1
ARGS=()
for a in "$@"; do
  case "$a" in
    --down) "${COMPOSE[@]}" --profile test down -v; exit 0 ;;
    --keep) FRESH=0 ;;
    *) ARGS+=("$a") ;;
  esac
done

# Hermetic by default: drop the stack so Postgres (tmpfs) comes up empty.
if [[ $FRESH -eq 1 ]]; then
  "${COMPOSE[@]}" --profile test down --remove-orphans >/dev/null 2>&1 || true
fi

"${COMPOSE[@]}" up -d --build postgres backend frontend

echo "⏳ waiting for test backend to be healthy…"
until [ "$("${COMPOSE[@]}" ps -q backend | xargs -r docker inspect -f '{{.State.Health.Status}}' 2>/dev/null)" = "healthy" ]; do
  sleep 2
done

# Mount the live tests dir so edits are picked up without rebuilding the image.
"${COMPOSE[@]}" --profile test run --rm \
  -v "$PWD/tests/e2e/tests:/e2e/tests" \
  playwright npx playwright test ${ARGS[@]+"${ARGS[@]}"}
