#!/usr/bin/env bash
# Roda npm ci, Vitest e o build de produção no Node 24 (o mesmo do Dockerfile).
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e npm_config_cache=/tmp/.npm \
  -v "$PROJECT_DIR/frontend:/app" -w /app node:24-bookworm-slim sh -c \
  'npm ci --no-audit --no-fund --loglevel=error && npx vitest run --environment jsdom && npm run build'
