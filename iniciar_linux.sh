#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$PROJECT_DIR"
COMPOSE=(docker compose -f "$PROJECT_DIR/backend/docker-compose.yml")

if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker não encontrado. Instale Docker Engine e o plugin Compose para continuar.' >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo 'O plugin docker compose não está disponível neste terminal.' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo 'O Docker não respondeu. Confirme se o serviço está ativo e se seu usuário tem acesso.' >&2
  exit 1
fi

on_error() {
  local result=$?
  echo 'A inicialização não terminou. Últimas mensagens dos serviços:' >&2
  "${COMPOSE[@]}" logs --tail=60 >&2 || true
  echo 'Envie a saída do terminal para verificarmos o erro. Nenhum volume foi removido.' >&2
  exit "$result"
}
trap on_error ERR

# backend/.env guarda a senha do banco fora do git.
bash "$PROJECT_DIR/scripts/garantir_env_backend.sh" "$PROJECT_DIR"

echo 'Iniciando PostgreSQL...'
"${COMPOSE[@]}" up -d --wait --wait-timeout 120 postgres

# Preserve the current database before applying migrations.
mkdir -p -- "$PROJECT_DIR/backups"
BACKUP_PATH="$PROJECT_DIR/backups/modelagem3d_$(date +%Y%m%d_%H%M%S)_$$.dump"
BACKUP_TEMP_PATH="$BACKUP_PATH.partial"
BACKUP_REMOTE_PATH="/tmp/$(basename -- "$BACKUP_PATH")"
echo 'Salvando uma cópia do banco antes das migrações...'
if ! "${COMPOSE[@]}" exec -T --interactive=false postgres \
  pg_dump -U modelagem3d -d modelagem3d_db -Fc --file="$BACKUP_REMOTE_PATH"; then
  echo 'O backup falhou. A migração não será iniciada.' >&2
  exit 1
fi

# Validate the archive inside the container. Do not stream binary backup bytes
# through the Docker CLI's stdout: write a file and copy it to the host instead.
if ! "${COMPOSE[@]}" exec -T --interactive=false postgres \
  sh -c 'pg_restore --list "$1" >/dev/null' sh "$BACKUP_REMOTE_PATH"; then
  echo 'O arquivo de backup não passou na conferência. A migração não será iniciada.' >&2
  exit 1
fi

if ! "${COMPOSE[@]}" cp "postgres:$BACKUP_REMOTE_PATH" "$BACKUP_TEMP_PATH"; then
  echo 'Não foi possível copiar o backup para o SSD. A migração não será iniciada.' >&2
  echo "A cópia dentro do container permanece em $BACKUP_REMOTE_PATH" >&2
  exit 1
fi

if [[ ! -s "$BACKUP_TEMP_PATH" ]]; then
  echo 'A cópia do backup está vazia. A migração não será iniciada.' >&2
  exit 1
fi

mv -- "$BACKUP_TEMP_PATH" "$BACKUP_PATH"
"${COMPOSE[@]}" exec -T --interactive=false postgres \
  rm -f -- "$BACKUP_REMOTE_PATH" || true
echo "Backup salvo: $BACKUP_PATH"

echo 'Preparando backend, bibliotecas químicas e interface...'
"${COMPOSE[@]}" up -d --build --wait --wait-timeout 180
"${COMPOSE[@]}" ps
echo
echo 'Interface: http://localhost:5173'
echo 'Documentação da API: http://127.0.0.1:8000/docs'
echo "Backup do banco: $BACKUP_PATH"
echo 'Para conferir os serviços: bash diagnosticar_linux.sh'
echo 'Para parar a interface e a API: bash parar_linux.sh'
