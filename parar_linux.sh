#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$PROJECT_DIR/backend/docker-compose.yml" stop backend frontend
echo 'Interface e API paradas. O PostgreSQL e os dados foram preservados.'
