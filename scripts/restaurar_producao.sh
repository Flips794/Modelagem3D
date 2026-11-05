#!/usr/bin/env bash
# Restaura um backup do banco de produção. SUBSTITUI os dados atuais.
# Uso: bash scripts/restaurar_producao.sh backups/producao/modelagem3d_AAAAMMDD_HHMMSS.dump
# Antes de restaurar, faz um backup do estado atual (scripts/backup_producao.sh).
# Confirmação: digitar RESTAURAR, ou CONFIRMAR=RESTAURAR em execução não interativa.
# Variáveis: ENV_FILE, COMPOSE_PROJECT, BACKUP_DIR (as mesmas do backup).
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/backend/.env.production}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-modelagem3d_prod}"
export ENV_FILE COMPOSE_PROJECT

dump="${1:-}"
if [[ -z "$dump" || ! -f "$dump" ]]; then
  echo "ERRO: informe um arquivo .dump existente. Uso: $0 <arquivo.dump>" >&2
  exit 1
fi
if [[ ! -s "$dump" ]]; then
  echo "ERRO: $dump está vazio." >&2
  exit 1
fi

compose() {
  docker compose -p "$COMPOSE_PROJECT" -f "$PROJECT_DIR/backend/docker-compose.yml" \
    -f "$PROJECT_DIR/backend/docker-compose.prod.yml" --env-file "$ENV_FILE" "$@"
}

echo "Isto substitui TODOS os dados do banco do projeto '$COMPOSE_PROJECT' por: $dump"
answer="${CONFIRMAR:-}"
if [[ -z "$answer" ]]; then
  read -r -p "Digite RESTAURAR para continuar: " answer || true
fi
if [[ "$answer" != "RESTAURAR" ]]; then
  echo "Cancelado: nada foi alterado." >&2
  exit 1
fi

echo "1/4 Backup do estado atual..."
bash "$PROJECT_DIR/scripts/backup_producao.sh"

echo "2/4 Parando o backend (sem conexões abertas durante a restauração)..."
compose stop backend
trap 'echo "Religando o backend..." >&2; compose start backend >/dev/null 2>&1 || true' ERR

echo "3/4 Restaurando..."
cat -- "$dump" | compose exec -T postgres pg_restore -U modelagem3d -d modelagem3d_db \
  --clean --if-exists --no-owner --single-transaction

trap - ERR
echo "4/4 Religando o backend..."
compose start backend
echo "Restauração concluída a partir de $dump."
