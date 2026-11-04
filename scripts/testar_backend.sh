#!/usr/bin/env bash
# Roda a suíte do backend dentro da imagem backend-backend com o código montado.
# Uso: bash scripts/testar_backend.sh [argumentos do pytest]
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$PROJECT_DIR/backend/.testdeps"
if [[ $# -eq 0 ]]; then
  set -- tests app/modules/micelium/test_organization_geometry.py
fi
exec docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONPATH=/deps \
  -e DATABASE_URL=postgresql+psycopg://validation:validation@127.0.0.1/validation \
  -v "$PROJECT_DIR/backend:/app" -v "$PROJECT_DIR/backend/.testdeps:/deps" -w /app \
  backend-backend:latest sh -c \
  'test -f /deps/.ok || { pip install -q --disable-pip-version-check --target /deps pytest httpx && touch /deps/.ok; }; python -m pytest -p no:cacheprovider -q "$@"' _ "$@"
