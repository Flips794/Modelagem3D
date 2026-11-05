#!/usr/bin/env bash
# Backup do banco de produção (pg_dump -Fc) em backups/producao/, mantendo os 7 mais recentes.
# Uso: bash scripts/backup_producao.sh
# Variáveis: ENV_FILE (backend/.env.production), COMPOSE_PROJECT (modelagem3d_prod),
#            BACKUP_DIR (backups/producao), KEEP (7).
# Cron diário, por exemplo: 30 3 * * * cd /caminho/do/projeto && bash scripts/backup_producao.sh
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/backend/.env.production}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-modelagem3d_prod}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups/producao}"
KEEP="${KEEP:-7}"

compose() {
  docker compose -p "$COMPOSE_PROJECT" -f "$PROJECT_DIR/backend/docker-compose.yml" \
    -f "$PROJECT_DIR/backend/docker-compose.prod.yml" --env-file "$ENV_FILE" "$@"
}

umask 077
mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/modelagem3d_$(date +%Y%m%d_%H%M%S).dump"
partial="$target.parcial"
trap 'rm -f "$partial"' EXIT

# Pipe para cat: o docker via snap falha ao escrever direto num arquivo redirecionado.
if ! compose exec -T postgres pg_dump -U modelagem3d -d modelagem3d_db -Fc | cat > "$partial"; then
  echo "ERRO: pg_dump falhou; nenhum backup foi gravado." >&2
  exit 1
fi
if [[ ! -s "$partial" ]]; then
  echo "ERRO: o dump saiu vazio; nenhum backup foi gravado." >&2
  exit 1
fi
mv "$partial" "$target"
chmod 600 "$target"

# Retenção: nomes com data/hora ordenam do mais antigo ao mais novo.
mapfile -t dumps < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'modelagem3d_*.dump' | sort)
excess=$(( ${#dumps[@]} - KEEP ))
for (( i = 0; i < excess; i++ )); do
  rm -f -- "${dumps[$i]}"
done

echo "Backup: $target ($(stat -c %s "$target") bytes)"
