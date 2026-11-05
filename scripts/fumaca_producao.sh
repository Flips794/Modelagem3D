#!/usr/bin/env bash
# Teste de fumaça da pilha de PRODUÇÃO, local, na porta 8088.
# Usa um projeto separado (m3d_fumaca) com volume próprio e senha aleatória:
# não toca a pilha de desenvolvimento nem o banco real. No fim remove só o que criou.
# Uso: bash scripts/fumaca_producao.sh        (FORCAR=1 ignora a checagem de RAM livre)
set -Eeuo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PROJECT="m3d_fumaca"
readonly BASE_URL="http://127.0.0.1:8088"
SDS='CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]'

available_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
if (( available_mb < 1500 )) && [[ "${FORCAR:-0}" != 1 ]]; then
  echo "RAM disponível: ${available_mb} MB (< 1500). Feche programas ou rode com FORCAR=1." >&2
  exit 2
fi

# Docker via snap não lê o /tmp do host: área temporária em .runtime/ (ignorada pelo git).
mkdir -p "$PROJECT_DIR/.runtime"
RUN_DIR="$(mktemp -d "$PROJECT_DIR/.runtime/fumaca.XXXXXX")"
ENV_FILE="$RUN_DIR/env"
umask 077
cat > "$ENV_FILE" <<ENV
POSTGRES_PASSWORD=$(openssl rand -hex 32)
SITE_ADDRESS=:80
HTTP_PORT=8088
HTTPS_PORT=8443
BACKEND_CORS_ORIGINS=[]
UVICORN_WORKERS=1
ENV

COMPOSE_FILES=(-f "$PROJECT_DIR/backend/docker-compose.yml" -f "$PROJECT_DIR/backend/docker-compose.prod.yml")
NNP_VERIFIED=1
if ! docker run --rm --security-opt no-new-privileges:true --entrypoint true postgres:16 >/dev/null 2>&1; then
  # Host incompatível com no-new-privileges (ex.: Docker via snap): teste local sem essa opção.
  NNP_VERIFIED=0
  COMPOSE_FILES+=(-f "$PROJECT_DIR/backend/docker-compose.compat-local.yml")
  echo "AVISO: este host não executa containers com no-new-privileges; a fumaça roda sem essa opção."
  echo "       Em produção (Docker oficial no VPS) ela continua ativa no docker-compose.prod.yml."
fi

compose_fumaca() {
  docker compose -p "$PROJECT" "${COMPOSE_FILES[@]}" --env-file "$ENV_FILE" "$@"
}

cleanup() {
  echo "== Limpeza: removendo só o projeto $PROJECT (containers, volume de fumaça e imagens)"
  compose_fumaca down -v --remove-orphans --rmi local >/dev/null 2>&1 || true
  rm -rf -- "$RUN_DIR"
}
trap cleanup EXIT

failures=0
check() {
  local description="$1"; shift
  if "$@"; then echo "  OK   $description"; else echo "  FALHA $description"; failures=$((failures + 1)); fi
}

container() { compose_fumaca ps -q "$1"; }
psql_fumaca() { compose_fumaca exec -T postgres psql -U modelagem3d -d modelagem3d_db -tA -v ON_ERROR_STOP=1 -c "$1"; }
wait_healthy() {
  local id; id="$(container "$1")"
  for _ in $(seq 120); do
    [[ "$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null)" == healthy ]] && return 0
    sleep 2
  done
  return 1
}

echo "== Subindo a pilha de produção ($PROJECT) — a primeira vez compila as imagens"
compose_fumaca up -d --build --wait --wait-timeout 600

echo "== Borda (Caddy)"
headers="$(curl -fsS -D - -o "$RUN_DIR/index.html" "$BASE_URL/")"
check "/ responde 200 com o HTML da interface" grep -q 'id="root"' "$RUN_DIR/index.html"
check "cabeçalhos de segurança (nosniff, X-Frame-Options)" \
  bash -c 'grep -qi "x-content-type-options: nosniff" <<<"$1" && grep -qi "x-frame-options: deny" <<<"$1"' _ "$headers"
check "rota interna da interface (/3d) devolve o index.html" \
  bash -c '[[ "$(curl -fsS -o /dev/null -w "%{content_type}" "$1/3d")" == text/html* ]]' _ "$BASE_URL"

echo "== API através do Caddy"
check "health/database conectado" bash -c 'curl -fsS "$1/api/v1/health/database" | grep -q "\"connected\""' _ "$BASE_URL"
check "simulate responde compactado (gzip)" bash -c '
  curl -fsS -D - -o /dev/null -H "Accept-Encoding: gzip" -H "Content-Type: application/json" \
    -d "{\"molecules\":[{\"name\":\"SDS\",\"smiles\":\"$2\",\"count\":40,\"real_amount_mmol\":3.0}],\"environment\":{\"volume_ml\":100.0},\"steps\":120,\"seed\":13}" \
    "$1/api/v1/micelium/simulate" | grep -qi "content-encoding: gzip"' _ "$BASE_URL" "$SDS"
check "corpo acima de 2 MB recusado (413)" bash -c '
  [[ "$(head -c 3000000 /dev/zero | tr "\0" x | curl -sS -o /dev/null -w "%{http_code}" \
      -H "Content-Type: application/json" --data-binary @- "$1/api/v1/chemistry/parameters/analyze")" == 413 ]]' _ "$BASE_URL"

echo "== Proteção do backend e do banco"
check "postgres sem porta publicada" bash -c '[[ -z "$(docker port "$1" | cat)" ]]' _ "$(container postgres)"
check "backend sem porta publicada" bash -c '[[ -z "$(docker port "$1" | cat)" ]]' _ "$(container backend)"
check "backend em produção: /docs desligado" bash -c '
  [[ "$(docker exec "$1" python -c "import urllib.request as u, urllib.error as e
try: u.urlopen(\"http://127.0.0.1:8000/docs\")
except e.HTTPError as x: print(x.code)")" == 404 ]]' _ "$(container backend)"
check "backend roda sem root" bash -c '[[ "$(docker exec "$1" id -u)" != 0 ]]' _ "$(container backend)"
check "sistema de arquivos do backend só leitura" bash -c '! docker exec "$1" sh -c "touch /app/teste" 2>/dev/null' _ "$(container backend)"
for service in postgres backend frontend; do
  check "limites de CPU e memória em $service" bash -c '
    read -r memory cpus <<<"$(docker inspect -f "{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}}" "$1")"
    (( memory > 0 && cpus > 0 ))' _ "$(container "$service")"
done

echo "== Uso de memória após simulate (limite entre parênteses)"
docker stats --no-stream --format '  {{.Name}}: {{.MemUsage}}' \
  "$(container postgres)" "$(container backend)" "$(container frontend)" | cat

echo "== Reinicialização"
backend_id="$(container backend)"
restarts_before="$(docker inspect -f '{{.RestartCount}}' "$backend_id")"
# A imagem slim não tem o comando kill: encerra o processo principal (PID 1) pelo Python.
docker exec "$backend_id" python -c "import os, signal; os.kill(1, signal.SIGTERM)" || true
sleep 3
check "backend volta sozinho após o processo cair (restart: unless-stopped)" wait_healthy backend
check "contador de reinícios aumentou" bash -c '(( $(docker inspect -f "{{.RestartCount}}" "$1") > $2 ))' _ "$backend_id" "$restarts_before"

psql_fumaca "CREATE TABLE fumaca_marcador (valor text); INSERT INTO fumaca_marcador VALUES ('persistiu');" >/dev/null
echo "== Pilha inteira desligada e religada (sem apagar o volume)"
compose_fumaca down >/dev/null 2>&1
compose_fumaca up -d --wait --wait-timeout 300 >/dev/null 2>&1
check "dados do Postgres persistem após recriar os containers" \
  bash -c '[[ "$1" == persistiu ]]' _ "$(psql_fumaca 'SELECT valor FROM fumaca_marcador;')"
check "API responde após religar" bash -c 'curl -fsS "$1/api/v1/health/database" | grep -q connected' _ "$BASE_URL"

echo "== Backup e restauração"
backups="$RUN_DIR/backups"
ENV_FILE="$ENV_FILE" COMPOSE_PROJECT="$PROJECT" BACKUP_DIR="$backups" bash "$PROJECT_DIR/scripts/backup_producao.sh"
dump="$(find "$backups" -name 'modelagem3d_*.dump' | sort | tail -n 1)"
check "backup gravado e não vazio" test -s "$dump"
psql_fumaca "DELETE FROM fumaca_marcador;" >/dev/null
sleep 1   # o backup de segurança da restauração ganha outro nome (data/hora)
ENV_FILE="$ENV_FILE" COMPOSE_PROJECT="$PROJECT" BACKUP_DIR="$backups" CONFIRMAR=RESTAURAR \
  bash "$PROJECT_DIR/scripts/restaurar_producao.sh" "$dump"
check "restauração recupera os dados apagados" \
  bash -c '[[ "$1" == persistiu ]]' _ "$(psql_fumaca 'SELECT valor FROM fumaca_marcador;')"
check "backend saudável após a restauração" wait_healthy backend

echo
if (( NNP_VERIFIED == 0 )); then
  echo "Não verificado neste host: no-new-privileges (verificar no VPS: ver PUBLICAR.md)."
fi
if (( failures > 0 )); then
  echo "RESULTADO: $failures verificação(ões) falharam."
  exit 1
fi
echo "RESULTADO: todas as verificações passaram."
