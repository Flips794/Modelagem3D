# Modelagem3D Web Lite v1 — relatório de validação

**Data:** 05/11/2026 · **Branch:** `web-lite-v1` (base `60f795d`; 15 commits das tarefas 0–13, 1 de correções da revisão final e este relatório) · **Spec:** `docs/superpowers/specs/2026-11-04-modelagem3d-web-lite-v1-design.md`

> **Situação: NÃO pronta para publicação.**
>
> - **Validação automática:** concluída e verde.
> - **Revisão independente do branch:** concluída; os achados críticos e importantes foram corrigidos e testados.
> - **Antes de publicar falta:**
>   1. Validação manual da interface no navegador (seção 9).
>   2. Troca da senha comprometida e limpeza do histórico do git.
>   3. Limite de requisições por IP.
>   4. Escolha do servidor e do domínio.
>
> Ver a seção 10.

## 1. Testes

| Suíte | Comando | Resultado |
|---|---|---|
| Backend (pytest no container) | `bash scripts/testar_backend.sh` | **1926 aprovados**, 28 pulados (21 só de host + 7 anteriores), 1 xfail |
| Frontend (Vitest + build) | `bash scripts/testar_frontend.sh` | **68 aprovados**, build e checagem de tipos sem erro |
| Host: segredos, `.env`, produção, backup e restauração | `python3 -m unittest backend/tests/test_no_secrets.py backend/tests/test_garantir_env.py backend/tests/test_producao_compose.py` | **28 aprovados** |
| Fumaça da pilha de produção (porta 8088) | `bash scripts/fumaca_producao.sh` | **22/22** (com a ressalva de `no-new-privileges`, seção 7) |
| Dependências Python | `pip-audit -r backend/requirements.txt` | nenhuma vulnerabilidade conhecida |
| Dependências do frontend (produção) | `npm audit --omit=dev` | 5 moderadas, 0 altas ou críticas (seção 7) |

- **O xfail:** é o radical `[CH3]`, que vira CH₄ ao passar pelo grafo do editor. É uma limitação documentada, com correção prevista na etapa 2 (spec §11).
- **Falha antiga fora da suíte padrão:** `IA/ammonium_classifier_smoke_test.py` também falha na base `60f795d`, então não foi introduzida por este branch.

## 2. Campos indisponíveis (painel químico)

Análise pelo `/analyze` com e sem a geometria 3D sob demanda. Cada molécula tem 131 campos com estado.

| Molécula | Indisponíveis ou não se aplica (2D) | Com 3D | Campos sem motivo escrito |
|---|---|---|---|
| SDS | 38 | 29 | **0** |
| Fenol | 59 | 49 | **0** |
| Acetato | 60 | 51 | **0** |
| Betaína C12 | 49 | 39 | **0** |

- **Fenol e acetato** não são surfactantes: a maior parte dos campos micelares e de CMC deles é "não se aplica".
- **Motivos mais comuns:**
  - métodos da etapa 2, como propriedades térmicas, quânticas, HOMO/LUMO e Fukui ("sem método validado");
  - geometria 3D não solicitada;
  - raio total, que exige espessura da cabeça;
  - ΔG de iônicos, que exige β.
- **Por átomo e por ligação:** todo campo indisponível também tem motivo.

## 3. Métodos e limites de validade (como implementados)

| Campo(s) | Método | Confiança | Limite (vai na nota) |
|---|---|---|---|
| Posição 3D, raio de giração, NPR, volume, SASA, superfície vdW, energia, tipo MMFF, comprimentos | ETKDGv3 + MMFF94, por fragmento e em ordem canônica, **sob demanda** (botão) | medium | 1 confórmero em fase gasosa. Sem parâmetros MMFF, fica indisponível (sem UFF). SASA com raios vdW do RDKit. |
| Momento dipolar | Cargas MMFF94 × coordenadas | low | Indisponível para íons (carga líquida ≠ 0) |
| Gasteiger, pares livres, VSEPR, R/S | RDKit | low (Gasteiger); high (demais) | Gasteiger é empírico |
| Ressonância | `ResonanceMolSupplier` (≤ 64 estruturas) | high | Estruturas de Lewis formais, sem peso; carga por átomo como faixa |
| pKa, espécie e carga no pH, LogD | Tabela SMARTS (CRC) com qualidade por sítio; Henderson–Hasselbalch | estimated | Pares acoplados validados (glicina, sarcosina, betaína, fosfato). Outros sítios a ≤ 7 ligações: carga, espécie, LogD e pKa único indisponíveis. Ácido forte: só limite superior. |
| Classe do surfactante | Regras estruturais + espécie no pH (separadas) | high, medium ou low | Anfotérico e zwitteriônico não exclusivos. Cabeça fraca: "surfactante ou cossurfactante". |
| CMC experimental | NSRDS-NBS 36 (composto exato) | experimental | Água pura, 20–30 °C |
| CMC calculada | Ajuste por família aos dados NSRDS (seção 4) | estimated | Sem extrapolar fora de n, m, T, I e solvente |
| Limite geométrico da esfera | 4/3·π·l_max³/v (Tanford) | estimated | Rotulado como limite teórico, não como número de agregação |
| Raio do núcleo e do cilindro | l_max, escolhidos pelo CPP | estimated (iônicos) | Área da cabeça fixa por classe, não medida. **Não iônicos e zwitteriônicos: indisponível.** |
| ΔG de micelização | RT·ln X_cmc, com X = c/(55,5 + c) | estimated | Só não iônicos; iônicos exigem β (indisponível) |
| N_agg, β, espessura da cabeça, raio total | — | indisponível | Sem referência verificada |
| Térmicas, transporte, quânticas, HLD, NAC | — | indisponível | Etapa 2 (xTB, MOPAC, Joback validado) |

## 4. CMC por família (NSRDS-NBS 36, NIST)

Forma: log10 CMC = a + b·n (+ c·m). Cada valor foi conferido na imagem da página. A validação é por exclusão de um ponto (LOO).

| Família | Faixa | Pontos | LOO máx. (log10) |
|---|---|---|---|
| Alcanossulfonato de sódio | n 8–12 | 3 | 0,10 |
| Cloreto de alquiltrimetilamônio | n 10–14 | 3 | 0,18 |
| Cloreto de alquilpiridínio | n 12–18 | 3 | 0,07 |
| Alquil β-D-glicosídeo | n 8–12 | 3 | 0,01 |
| Álcool etoxilado CnEm | n 6–16, m 3–21 | 13 | 0,21 |

- **SDS e CTAB (correlações existentes, inalteradas):** erro ≤ 0,05 log em relação ao NIST.
- **Famílias excluídas** por falta de dados suficientes na tabela recomendada:
  - carboxilatos;
  - óxidos de amina;
  - alquilbenzenossulfonatos;
  - brometos de piridínio;
  - **betaínas e sulfobetaínas** (sem nenhum valor).

  Por isso **a betaína não tem CMC e não forma micela no 3D** (seção 8).
- Relatório completo: `documentacao/validacao/cmc_familias.md`.

## 5. Identificação das cinco classes

Conjunto rotulado pela literatura (`backend/tests/fixtures/surfactant_classes.json`, 50 moléculas). **50/50 corretas.**

| Esperado → obtido | aniônico | catiônico | não iônico | zwitteriônico | anfotérico | não surfactante |
|---|---|---|---|---|---|---|
| aniônico | **9** | | | | | |
| catiônico | | **9** | | | | |
| não iônico | | | **9** | | | |
| zwitteriônico | | | | **6** | | |
| anfotérico | | | | | **6** | |
| não surfactante | | | | | | **11** |

Os casos que estavam errados no diagnóstico agora estão certos:
- N-dodecilglicina → anfotérico;
- óxido de dodecildimetilamina → anfotérico (espécie não iônica no pH 7);
- dodecanol → "surfactante ou cossurfactante".

## 6. Desempenho e memória

Medições numa máquina de desenvolvimento com 12 CPUs. Servidor HTTP real (uvicorn, 1 worker), sem outras cargas.

| Medida | Resultado |
|---|---|
| `/analyze`, 170 moléculas (catálogo + casos extremos) | p50 **14,6 ms**, p95 **22,6 ms**, máx. 341 ms. Meta da spec: p95 ≤ 300 ms. 170 respostas 200, nenhum 500. |
| Geometria 3D sob demanda, 151 moléculas, primeira vez | p50 320 ms, p95 929 ms, máx. 4,7 s (moléculas grandes com segunda tentativa de embed) |
| Geometria 3D já em cache | p50 16 ms, p95 22 ms |
| Simulação 3D, 40 moléculas de SDS (160 partículas) | 3,1–4,3 s por trecho; resposta 1.219 KB → **534 KB com gzip** |
| Simulação 3D, SDS + C12E5 (320 partículas) | 7,3–10,2 s por trecho (o frontend espera até 600 s) |
| Simulação 3D, CTAB (200 partículas) | 3,8–6,2 s por trecho |
| Memória do backend | Pico de 195 MB após o lote de geometria 3D; cerca de 100–110 MB na pilha de produção após uma simulação |
| Memória do Postgres e do Caddy (produção) | 26–50 MB e cerca de 11 MB |
| Bundle do frontend | 1.022,9 KB (**276,5 KB gzip**); antes, 275 KB gzip. Abaixo de 1 MB gzip, então sem divisão de código. |

**Responsividade da interface:**
- O painel e os cards do 3D foram conferidos no código por um verificador independente, inclusive a largura de 390 px pelas regras CSS.
- O toque (um dedo gira, pinça dá zoom) tem teste unitário.
- **Nada disso foi renderizado num navegador real:** é item da validação manual (seção 9).

## 7. Segurança, Docker, banco e backup

- **Segredos:**
  - nenhum `.env` real em nenhum commit;
  - nenhuma credencial na árvore atual (teste de host);
  - `.gitignore` e `.dockerignore` excluem qualquer `.env.*` real;
  - a senha de produção vem só do arquivo de ambiente (`openssl rand -hex 32`).
- **Histórico do git:** a senha antiga do banco de desenvolvimento continua em commits antigos. Ela é **uma palavra comum de química**, fácil de adivinhar, e aparece legitimamente no código (descrição de atalho de molécula, relatórios). A limpeza precisa substituir **só onde ela é credencial**. As regras já testadas estão em `PUBLICAR.md`.
- **API em produção** (`APP_ENV=production`):
  - sem `/docs`, `/redoc` e `/openapi.json`;
  - sem a rota OpenMM de demonstração;
  - CORS só da configuração, sem credenciais;
  - corpo acima de 2 MB → 413, também sem Content-Length;
  - gzip;
  - erros sem traceback;
  - rotas que gravam no banco fechadas, porque não há login;
  - simulação limitada a 2.500 partículas, 300 passos e 12 moléculas.
- **Compose de produção:**
  - só o Caddy publica portas (80 e 443); backend e Postgres sem porta;
  - volumes persistentes do banco e dos certificados;
  - `restart: unless-stopped` e healthchecks;
  - limites de CPU e memória;
  - backend sem root e só leitura; Caddy só leitura com `cap_drop: ALL`;
  - logs limitados.
- **`no-new-privileges`:** está no compose de produção, mas **não pôde ser verificado nesta máquina**. Com o Docker instalado via snap, nenhum container roda com essa opção, nem `postgres:16` puro. Conferir no VPS com o comando do `PUBLICAR.md`.
- **Backup e restauração** (validados na fumaça):
  - backup com `pg_dump -Fc`, permissão 600, mantém 7 e não deixa arquivo vazio se falhar;
  - restauração com confirmação e cópia de segurança em `antes_restauracao/`, fora da rotação. Corrigido na revisão final: antes, a rotação podia apagar o próprio dump sendo restaurado;
  - restauração em transação única, religando o backend no fim;
  - na fumaça, os dados apagados voltaram.
- **Migrações:** uma única cabeça Alembic (`20261104_0002`). O backend aplica as migrações ao iniciar.
- **npm audit:** 5 vulnerabilidades moderadas, todas em `ketcher-react → dpdm → glob/minimatch`. São ferramentas de análise de dependências que não recebem entrada do usuário no navegador. Não rodei `npm audit fix` para não mexer no editor.

## 8. Limitações científicas e funcionalidades incompletas

1. **O 3D é uma visualização representativa, não uma simulação física.** Quando há molde previsto (CPP), os agregados organizados recebem o rótulo da previsão. A "forma dominante medida" do card Observado é a única medida que não usa a previsão.
2. **O CPP usa área de cabeça fixa por classe** (72 Å² iônicos, 60 Å² não iônicos, 56 Å² zwitteriônicos) e não a da molécula:
   - no painel, não iônicos e zwitteriônicos ficam sem veredito esfera/cilindro;
   - o motor 3D, que é anterior a este branch, ainda usa esse CPP para escolher o molde.
3. **Sem CMC, não há micela no 3D.** Isso vale para betaínas, carboxilatos, óxidos de amina e qualquer molécula fora das famílias da seção 4. Em mistura, o componente sem CMC aparece nomeado, e o C/CMC parcial é mostrado só como visualização.
4. **N_agg, β, espessura da cabeça, raio total e ΔG de iônicos** ficam indisponíveis até haver uma referência confiável.
5. **pKa:** valores de compostos-modelo do CRC; erro típico de cerca de ±1. Sítios acoplados sem par validado ficam sem carga, espécie, LogD e pKa único.
6. **Geometria 3D:** um confórmero em fase gasosa. Sem parâmetros MMFF (Se, B, metais), fica sem 3D.
7. **Radical desenhado no editor:** perde o radical (CH₃ → CH₄). Correção na etapa 2.
8. **Estado da animação 3D:**
   - fica na memória do processo, então o backend precisa de 1 worker;
   - é identificado pela composição da mistura, então dois usuários com a mesma mistura ao mesmo tempo continuam a cena um do outro. Efeito só visual, sem vazamento de dados; fica para a etapa 2.
9. **Ainda não implementados** (etapa 2): OpenMM/Martini 3, xTB, DFT, MOPAC, Joback, propriedades térmicas e de transporte, e o treinamento das 6 IAs. O módulo OpenMM e as IAs foram **preservados** (seção 11).

## 9. Validação manual pendente (navegador)

A pilha de desenvolvimento em execução ainda roda o código da tarefa 11. Antes de testar, reconstrua com `bash iniciar_linux.sh` e pressione Ctrl+F5 em http://localhost:5173. Roteiro na resposta final da tarefa 14 e no relatório da tarefa 11.

## 10. Pendências antes de publicar

**Bloqueantes:**
1. Validação manual da interface (seção 9), sem erros críticos.
2. Trocar a senha do banco de desenvolvimento e reescrever o histórico do git com as regras restritas a credenciais (`PUBLICAR.md`). Até lá, sem push e sem deploy público.
3. **Limite de requisições por IP.** Os limites atuais (tamanho de corpo e de simulação) não impedem muitas requisições seguidas, e uma simulação grande ocupa o único worker por até cerca de 1 minuto. Opções: limitador no proxy do provedor, Caddy com o módulo `rate_limit` (exige imagem customizada), ou fila de simulações na etapa 2.
4. Escolher VPS ou serviço gerenciado e o domínio; no VPS, conferir `no-new-privileges`.
5. Cópia dos backups para fora do servidor.

**Não bloqueantes** (pendências menores da revisão final):
- O aviso "C/CMC abaixo de 1" do analisador pode usar o valor parcial sem dizer que é parcial.
- Não há Content-Security-Policy no Caddy. Adicionar exige testar o editor Ketcher, que usa WebAssembly.
- 5 vulnerabilidades moderadas no npm (seção 7).

## 11. Módulos Research Full preservados

- **Arquivos:** nenhum arquivo apagado ou renomeado no branch (`git diff --diff-filter=DR` vazio).
- **Módulos intactos:**
  - `simulation/` (OpenMM) sem alteração;
  - IA da micelização só com acréscimos (`amphoteric_ai`, metadados de proveniência);
  - `calculation_page.py` e `miriam21_engine.py` sem alteração.
- **Importação:** todos importam no container. O WebSocket OpenMM continua ativo em desenvolvimento e desligado em produção por configuração (`ENABLE_DEMO_ROUTES`).
- Martini, MOPAC e Joback não tinham código antes do branch.

## 12. Desvios em relação à spec

| Spec | Implementado | Motivo |
|---|---|---|
| CMC por constantes A/B do Rosen | Ajuste próprio aos dados NSRDS-NBS 36, validado por exclusão de um ponto (LOO) | Constantes do Rosen não verificáveis na fonte; dados primários do NIST conferidos página a página |
| Famílias: carboxilato, betaína, óxido de amina | Excluídas | Menos de 3 homólogos ou nenhum valor recomendado |
| β e espessura da cabeça por família | Indisponíveis | Sem referência verificada (decisão do usuário) |
| X_cmc = CMC/55,5 | X = c/(55,5 + c) | Fração molar exata; diferença desprezível na faixa de CMC |
| N_agg = teto geométrico | Campo separado "limite geométrico da esfera"; N_agg indisponível | Decisão do usuário: teto não é número de agregação |
| Raio da micela pelo CPP | Iônicos com ressalva; não iônicos e zwitteriônicos indisponíveis | Área da cabeça fixa por classe (revisão final) |
| Tempo limite do confórmero de 2 s, com UFF de reserva | 8 s, segunda tentativa com coordenadas aleatórias, sem UFF | 2 s falhava sob carga; usuário pediu não inventar sem MMFF |
| `UVICORN_WORKERS` padrão 2 | Padrão 1 | Estado da animação na memória do processo |
| Debounce de 400 ms | 250 ms existente mantido | A spec pedia 400 ms só se não houvesse debounce |
| Serviço Caddy separado | A imagem de produção do frontend é a borda | Um container a menos; mesma função |
| Senha em base64 | Hexadecimal | Base64 quebra a URL do banco |
| (não previsto) | Produção fecha escrita no banco e limita o tamanho da simulação | Revisão final: API pública sem autenticação |
