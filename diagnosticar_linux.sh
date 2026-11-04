#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$PROJECT_DIR"
COMPOSE=(docker compose -f "$PROJECT_DIR/backend/docker-compose.yml")
"${COMPOSE[@]}" ps
"${COMPOSE[@]}" logs --tail=50 backend frontend
"${COMPOSE[@]}" exec -T backend python -m scripts.verificar_instalacao
