#!/usr/bin/env bash
# Garante backend/.env (ignorado pelo git) com POSTGRES_PASSWORD e DATABASE_URL.
#
# - Se backend/.env já existe, não altera nada.
# - Se o container modelagem3d_postgres existe, reutiliza a senha com que o banco
#   foi criado (trocar a senha no .env NÃO troca a senha de um banco existente).
# - Instalação nova (sem container e sem volume): gera uma senha aleatória.
# - Volume do banco sem container: não adivinha a senha; pede o .env manual.
#
# Uso: bash scripts/garantir_env_backend.sh [PASTA_DO_PROJETO]
set -Eeuo pipefail

PROJECT_DIR="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="$PROJECT_DIR/backend/.env"
EXAMPLE_FILE="$PROJECT_DIR/backend/.env.example"
CONTAINER_NAME="modelagem3d_postgres"

if [[ -f "$ENV_FILE" ]]; then
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "O Docker não respondeu; backend/.env não foi criado para não gerar uma senha diferente da do banco." >&2
  exit 1
fi

password="$(docker inspect "$CONTAINER_NAME" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
  | sed -n 's/^POSTGRES_PASSWORD=//p' | head -n 1 || true)"

if [[ -z "$password" ]]; then
  if docker volume ls --format '{{.Name}}' 2>/dev/null | grep -Eq '(^|_)modelagem3d_pgdata$'; then
    {
      echo "Existe um volume do banco (modelagem3d_pgdata), mas não o container $CONTAINER_NAME."
      echo "Não é possível descobrir a senha atual do banco automaticamente."
      echo "Crie backend/.env a partir de backend/.env.example e preencha POSTGRES_PASSWORD"
      echo "e DATABASE_URL com a senha usada quando o banco foi criado."
    } >&2
    exit 1
  fi
  password="$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')"
fi

umask 077
tmp_file="$ENV_FILE.partial"
{
  echo "# Gerado por scripts/garantir_env_backend.sh. NÃO versionar (backend/.env está no .gitignore)."
  echo "# Alterar POSTGRES_PASSWORD aqui não muda a senha de um banco já criado (use ALTER USER)."
  while IFS= read -r line || [[ -n "$line" ]]; do
    printf '%s\n' "${line//CHANGE_ME/$password}"
  done < "$EXAMPLE_FILE"
} > "$tmp_file"
chmod 600 "$tmp_file"
mv -- "$tmp_file" "$ENV_FILE"
echo "Criado backend/.env (permissão 600)."
