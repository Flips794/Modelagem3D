# Publicar o Modelagem3D Web Lite

Guia para colocar a versão web no ar: num VPS com Docker (caminho testado localmente) ou num serviço gerenciado compatível.

> **Antes de qualquer publicação:**
> 1. A senha antiga do banco de desenvolvimento **já foi trocada e removida do histórico do git** (14/11/2026). Veja [Credenciais comprometidas e histórico do git](#credenciais-comprometidas-e-histórico-do-git) se precisar repetir o procedimento.
> 2. Produção usa **uma senha nova**, nunca a de desenvolvimento.

## Como a pilha funciona

```
Internet ──80/443──► frontend (Caddy: HTTPS automático, interface, /api/* → backend:8000)
                                   backend (FastAPI + RDKit, sem porta publicada)
                                      └── postgres 16 (volume persistente, sem porta publicada)
```

- **Arquivos:**
  - `backend/docker-compose.yml`: desenvolvimento, sem mudanças;
  - `backend/docker-compose.prod.yml`: sobreposto a ele em produção;
  - `backend/.env.production`: valores reais. Você cria esse arquivo a partir de `backend/.env.production.example`; o git o ignora.
- **Portas:** só o Caddy publica portas (80 e 443). Backend e banco só se falam pela rede interna do Docker.
- **Persistência:**
  - dados do banco: volume `modelagem3d_prod_modelagem3d_pgdata`;
  - certificados HTTPS: volumes `caddy_data` e `caddy_config`;
  - `docker compose down` **sem `-v`** preserva os três.
- **Reinicialização:**
  - todos os serviços usam `restart: unless-stopped`: voltam sozinhos se o processo cair e quando o Docker reinicia com o servidor;
  - cada serviço tem healthcheck, e o Caddy só sobe depois que o backend responde.
- **Limites de recursos** (padrões, ajustáveis no `.env.production`):

  | Serviço | CPU | Memória | Uso medido na fumaça |
  |---|---|---|---|
  | backend | 1,5 | 1 GB | ≈ 100 MB após uma simulação 3D |
  | postgres | 0,5 | 384 MB | ≈ 26–50 MB |
  | frontend (Caddy) | 0,5 | 128 MB | ≈ 11 MB |

- **Segurança:**
  - backend sem root, com sistema de arquivos só leitura;
  - Caddy sem capacidades extras (só abrir as portas 80 e 443) e também só leitura;
  - `no-new-privileges` em todos os serviços;
  - logs limitados a 3 × 10 MB por serviço;
  - em produção a API desliga `/docs` e a rota de demonstração OpenMM, e recusa corpos acima de 2 MB (413);
  - em produção a API não devolve mensagens nem tracebacks internos (o detalhe vai para o log), fecha as rotas que gravam no banco (`ENABLE_DB_WRITES=false`; a API não tem login) e limita cada simulação 3D a 2.500 partículas, 300 passos e 12 moléculas (`PUBLIC_MAX_*`);
  - **ainda não há limite de requisições por IP**: veja "Pendências antes de publicar" no relatório `documentacao/validacao/WEB_LITE_V1.md`.
- **Um processo do backend (`UVICORN_WORKERS=1`):** a animação 3D guarda o estado entre trechos na memória do processo. Com mais de um processo, trechos da mesma mistura podem cair em processos diferentes e a cena recomeça.

## Teste local antes de publicar (fumaça)

```bash
bash scripts/fumaca_producao.sh
```

- **O que faz:** sobe a pilha de produção num projeto separado (`m3d_fumaca`), com volume próprio e senha aleatória, em http://127.0.0.1:8088. Não toca a pilha de desenvolvimento nem o banco real.
- **O que verifica (22 itens):**
  - interface, cabeçalhos de segurança, gzip e o limite 413;
  - backend e banco sem porta publicada, `/docs` desligado, backend sem root e só leitura, limites de CPU e memória;
  - retorno automático após queda e após religar a pilha, com os dados preservados;
  - backup e restauração.
- **No fim:** remove só o que criou.
- **Memória:** exige 1,5 GB de RAM disponível; `FORCAR=1` ignora essa checagem.
- **Docker via snap:** em computadores com Docker instalado pelo snap, `no-new-privileges` impede os containers de rodar. A fumaça detecta isso, roda sem essa opção (`backend/docker-compose.compat-local.yml`, só para teste local) e avisa. No VPS, confira com o passo 6 abaixo.

## Caminho 1 — VPS com Docker (recomendado)

**Requisitos:**
- 2 vCPUs, 2 GB de RAM e 20 GB de disco;
- Ubuntu 24.04 LTS ou equivalente;
- um domínio.

1. **Docker oficial** (não o pacote snap):

   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo systemctl enable --now docker      # o Docker e os containers voltam após reiniciar o servidor
   sudo usermod -aG docker "$USER"         # depois saia e entre de novo na sessão SSH
   ```

2. **Firewall:** só SSH, HTTP e HTTPS.

   ```bash
   sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
   sudo ufw enable
   ```

   Backend e banco não publicam portas, então não precisam de regra.

3. **DNS:** crie um registro `A` (e `AAAA`, se houver IPv6) do domínio apontando para o IP do VPS. Espere a propagação antes do passo 5: o Caddy precisa do domínio resolvendo para emitir o certificado.

4. **Código e ambiente:**
   - Copie o projeto para o servidor, por exemplo de um repositório **privado** já limpo, ou com `rsync` ou `scp`.
   - Depois crie o `.env.production`:

   ```bash
   cp backend/.env.production.example backend/.env.production
   chmod 600 backend/.env.production
   openssl rand -hex 32        # cole o resultado em POSTGRES_PASSWORD
   nano backend/.env.production   # POSTGRES_PASSWORD, SITE_ADDRESS=seu.dominio
   ```

5. **Subir:**

   ```bash
   docker compose -f backend/docker-compose.yml -f backend/docker-compose.prod.yml \
     --env-file backend/.env.production up -d --build --wait
   ```

   A primeira vez compila as imagens (alguns minutos). As migrações do banco rodam sozinhas quando o backend inicia.

6. **Verificar:**

   ```bash
   curl -fsS https://seu.dominio/api/v1/health/database      # {"status":"ok","database":"connected"}
   docker compose -p modelagem3d_prod ps                      # todos "healthy"
   docker run --rm --security-opt no-new-privileges:true --entrypoint true postgres:16 && echo "no-new-privileges OK"
   ```

   Abra `https://seu.dominio` no navegador e repita o teste manual da tarefa 11 (painel 2D e ambiente 3D).

7. **Backup diário:**
   - O script grava `pg_dump` em `backups/producao/`, com permissão 600, e mantém os 7 mais recentes.
   - Teste uma vez à mão (`bash scripts/backup_producao.sh`) e agende no `crontab -e`:

   ```
   30 3 * * * cd /caminho/do/projeto && bash scripts/backup_producao.sh >> backups/producao/backup.log 2>&1
   ```

   - Copie os backups periodicamente para fora do VPS (outro servidor ou armazenamento externo): um backup no mesmo disco não protege contra a perda do servidor.

### Restaurar um backup

```bash
bash scripts/restaurar_producao.sh backups/producao/modelagem3d_AAAAMMDD_HHMMSS.dump
```

- **Antes de restaurar:** pede que você digite `RESTAURAR` e faz um backup do estado atual em `backups/producao/antes_restauracao/`, fora da rotação diária. Assim a rotação nunca apaga o dump que está sendo restaurado.
- **Durante:** para o backend e restaura numa única transação; se falhar, nada muda.
- **Depois:** religa o backend.
- **Sem terminal interativo:** `CONFIRMAR=RESTAURAR bash scripts/restaurar_producao.sh <arquivo>`.
- **Restaurar num servidor novo:** suba a pilha (passo 5), copie o `.dump` para `backups/producao/` e rode o comando acima.

### Operação do dia a dia

```bash
P="docker compose -f backend/docker-compose.yml -f backend/docker-compose.prod.yml --env-file backend/.env.production"
$P logs --tail=100 backend          # logs
$P up -d --build --wait             # atualizar após trazer código novo (faça um backup antes)
$P restart backend                  # reiniciar um serviço
$P down                             # parar tudo SEM apagar dados (nunca use -v em produção)
```

## Caminho 2 — serviço gerenciado (Render, Railway, Fly.io e similares)

Este caminho não foi testado em provedor real; ele usa as mesmas imagens.

- **Banco:** PostgreSQL 16 gerenciado. Anote a URL de conexão.
- **Backend:** serviço Docker a partir de `backend/Dockerfile`.
  - A imagem lê a porta de `PORT` e aplica as migrações sozinha ao iniciar.
  - Variáveis:

  | Variável | Valor |
  |---|---|
  | `DATABASE_URL` | `postgresql+psycopg://USUARIO:CHANGE_ME@HOST:5432/BANCO`, com a senha real no lugar de CHANGE_ME (troque `postgres://` por `postgresql+psycopg://`) |
  | `APP_ENV` | `production` |
  | `UVICORN_WORKERS` | `1` (ver acima) |
  | `BACKEND_CORS_ORIGINS` | `[]` se a interface estiver no mesmo domínio; senão `["https://endereco-da-interface"]` |
  | `PORT` | definida pelo provedor (padrão 8000) |
  | `FORWARDED_ALLOW_IPS` | `*` só se o backend estiver atrás do proxy do provedor e sem acesso direto |

- **Interface**, uma de duas opções:
  - **Imagem do Caddy:** `frontend/Dockerfile`, estágio `prod`, com `SITE_ADDRESS=:80` (o provedor cuida do HTTPS) e `API_UPSTREAM=<endereço interno do backend>:<porta>`. Interface e API ficam no mesmo domínio.
  - **Site estático:** `npm ci && npm run build` com `VITE_API_URL=https://endereco-do-backend/api/v1`, publicando a pasta `frontend/dist`. Nesse caso, configure `BACKEND_CORS_ORIGINS` no backend com o endereço da interface.
- **Backups:** use os do provedor e confira se a retenção é de pelo menos 7 dias.

## Credenciais comprometidas e histórico do git

> **Executado em 14/11/2026:** a senha do banco local foi trocada e o histórico reescrito com as substituições abaixo (nenhuma credencial restante; árvores dos commits finais idênticas). A seção fica como referência caso uma credencial volte a ser commitada.

A senha do banco de desenvolvimento esteve em commits antigos. O procedimento para removê-la foi:

1. **Trocar a senha do banco de desenvolvimento.** O volume é preservado; só a senha muda.

   ```bash
   NOVA=$(openssl rand -hex 32)
   docker exec -i modelagem3d_postgres psql -U modelagem3d -d modelagem3d_db \
     -c "ALTER USER modelagem3d WITH PASSWORD '$NOVA';"
   ```

   Depois troque `POSTGRES_PASSWORD` e a senha dentro de `DATABASE_URL` em `backend/.env` pelo mesmo valor e rode `bash iniciar_linux.sh`.

   O container ainda tem a senha antiga na variável de ambiente, que o `garantir_env_backend.sh` lê. Recrie o container do Postgres com `docker compose -f backend/docker-compose.yml up -d --force-recreate postgres`, sem `-v`, para alinhar.

2. **Reescrever o histórico** com [`git filter-repo`](https://github.com/newren/git-filter-repo), num clone novo e com backup do repositório:

   **Atenção:** a senha antiga é uma palavra comum de química e aparece legitimamente no código (descrição de atalho de molécula, relatórios). Uma substituição simples da palavra trocaria esse texto também. Substitua **só onde ela é credencial**:

   ```bash
   S='<senha-antiga>'
   {
     printf 'regex:(POSTGRES_PASSWORD\\s*[:=]\\s*["'"'"']?)%s==>\\1REMOVIDO\n' "$S"
     printf 'regex:(postgresql(\\+psycopg)?://[^:/\\s]+:)%s@==>\\1REMOVIDO@\n' "$S"
   } > /fora/do/repo/substituicoes.txt
   git filter-repo --replace-text /fora/do/repo/substituicoes.txt
   # As duas contagens devem dar 0 (credencial removida do histórico inteiro):
   git log -p --all | grep -cE "POSTGRES_PASSWORD.{0,4}$S"
   git log -p --all | grep -cE "://[^:/ ]+:$S@"
   ```

   - Troque `<senha-antiga>` pela senha real só nesse terminal, sem salvá-la em arquivo do repositório. Apague `substituicoes.txt` depois.
   - Confira também que o termo químico continua no código atual (`git grep -c` do termo deve dar o mesmo número de antes).
   - Depois da reescrita, todos os hashes de commit mudam: faça backup do repositório antes (`git bundle create ../antes.bundle --all`).

3. **Conferir** que nenhum segredo ficou: `python3 -m unittest backend/tests/test_no_secrets.py`.
4. Só então crie o repositório remoto (privado, de preferência) e faça o push.
