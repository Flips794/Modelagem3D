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

## 13. Exemplos documentados de morfologia (05/11/2026)

**Spec:** `docs/superpowers/specs/2026-11-05-exemplos-documentados-morfologias-design.md` · **Plano:** `docs/superpowers/plans/2026-11-05-exemplos-documentados-morfologias.md` · **Catálogo:** `backend/app/modules/micelium/documented_examples.py` (versão 1.0.0 de cada exemplo).

O painel 2D→3D ganhou a lista **Exemplos documentados**. Cada exemplo carrega uma mistura com condições tiradas da literatura. Dentro dessas condições, o 3D mostra a forma documentada. Fora delas, o motor volta ao cálculo comum e avisa qual condição falhou.

Só o SDS é **previsão validada**: a forma vem do cálculo (CMC e CPP). Os outros quatro são **demonstrações representativas**: a forma vem da referência e a cena é guiada por forças visuais declaradas nas notas do card. **Nada nas cenas é evidência de dinâmica molecular real.**

### 13.1 Exemplos, condições e referências

Natureza de cada condição: **experimental** (medida no estudo), **protocolo** (método de preparo) ou **limite técnico** (tolerância de entrada ou domínio do modelo do projeto).

| Exemplo | Tipo | Condições | Referências |
|---|---|---|---|
| SDS — micela esférica (aproximação) | previsão validada | água (experimental); c/CMC > 1 (experimental); 20–30 °C (limite técnico); força iônica ≤ 0,07 mol/L (limite técnico, ver 13.5) | Mukerjee & Mysels, NSRDS-NBS 36 (1971); SANS de SDS sem sal ([PMC4487321](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4487321/)) |
| CTAB + salicilato de sódio — micela vermiforme | demonstração | CTAB 2,5–15 mM; NaSal/CTAB 2,5–10; 20,0 °C; água (estudo em D₂O) — todas experimentais; ± 0,5 K (limite técnico) | Lam et al. ([arXiv 1812.07138](https://arxiv.org/abs/1812.07138)); Olsson et al. (1986) e Rao et al. (1987), RMN |
| DPPC — recorte de bicamada (hidratação) | demonstração | > 41 °C (Tm, experimental); hidratação de filme, água (protocolo); < 100 °C (limite técnico) | Bangham et al. (1965); Tm do DPPC ([PMC3508262](https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/)) |
| DPPC — vesícula unilamelar (extrusão) | demonstração | extrusão por 100 nm (experimental); 51–61 °C, água (protocolo) | Hope et al. (1985) ([PubMed](https://pubmed.ncbi.nlm.nih.gov/23008845/)); Tm do DPPC |
| AOT em isooctano — micela inversa (w0 = 10) | demonstração | w0 = 10; AOT 0,1 M; 25 °C; isooctano — experimentais; tolerâncias ± 0,5 (w0), ± 1 % (AOT), ± 0,5 K (limite técnico) | aniquilação de pósitrons ([PDF](https://baes.uc.pt/bitstream/10316/10313/1/Four-Component%20Analysis%20and%20Modeling%20of%20Positron%20Annihilation.pdf)); Bohidar & Behboudnia (2001); Abel et al. ([doi](https://pubs.acs.org/doi/10.1021/jp047138e)); Fayer et al. ([PMC2721765](https://pmc.ncbi.nlm.nih.gov/articles/PMC2721765)); Stenutz (fonte secundária) |

### 13.2 Testes

| Suíte | Resultado |
|---|---|
| Backend completo (`bash scripts/testar_backend.sh`, rodado em 4 partes para caber no tempo do terminal) | **2040 aprovados**, 28 pulados, 1 falha esperada (xfail) |
| Só os exemplos (`tests/test_exemplos_*.py`) | 114 aprovados (66 + 22 de geometria + 26 de estabilidade e forma medida) |
| Frontend (`bash scripts/testar_frontend.sh`) | **87 aprovados**, build sem erro |
| Host (segredos, `.env`, produção) | **28 aprovados** |

**Nota sobre o tempo (rodada anterior):** numa das execuções, `test_tempo_por_trecho[dppc_bicamada_hidratacao]` falhou com 16,16 s (limite 15 s). A carga média da máquina era 5,8, com um Chrome aberto pedindo trechos ao mesmo backend. Todos os exemplos ficaram mais lentos ao mesmo tempo. Repetido logo depois, passou com 12,50 s, e o código desse caminho não mudou entre as execuções. Em máquina carregada, a bicamada pode passar do limite.

Os testes de geometria medem as coordenadas do backend depois de 3 trechos, sem usar a previsão:
- **SDS:** cabeças para fora.
- **CTAB:** cabeças longe do maior eixo, salicilato na interface, agregado mais alongado que a esfera do SDS.
- **Bicamada DPPC:** ≥ 70 % das cabeças nas duas faces, com caudas no meio. Medido: 100 % em 1, 3 e 5 trechos.
- **Vesícula DPPC:** cabeças internas < caudas < cabeças externas.
- **AOT:** cabeças para dentro, água no centro.
- **DPPC e AOT:** as duas caudas de cada molécula ficam do mesmo lado.

Testes de estabilidade e de forma medida (`tests/test_exemplos_estabilidade.py`):
- **AOT, 6 trechos seguidos:** em cada trecho, fração organizada > 50 % e rótulo "micela inversa". A tela mostra o card de cada trecho, não só o do 3º.
- **CTAB, 6 trechos seguidos:** em cada trecho, "micela cilíndrica/wormlike" confirmada pela forma medida "agregado alongado", com fração > 50 %. Outro teste garante que o rótulo nunca aparece sem essa confirmação.
- **Bicamada e vesícula, do 2º ao 5º trecho:** rótulo documentado, forma medida lamelar ou casca, fração > 50 %.
- **Vesícula com cavidade:** nenhuma conta de DPPC a menos de 1,0 do centro; cabeças internas a ≥ 1,4.
- **Agrupamento:** o raio entre moléculas cresce com √(nº de caudas). Lipídios de duas caudas a 2,8 de distância se agrupam; moléculas de uma cauda, não.
- **Notas do catálogo:** o CTAB declara o molde visual, e a vesícula declara a cavidade e a escala.
- **Pedidos comuns** (`test_organization_geometry.py`): cilindro e bicamada só são rotulados quando a forma medida confirma.
- **Forma medida sem a previsão:** bicamada → "agregado lamelar (duas folhas)"; vesícula → "casca fechada de duas folhas"; SDS, CTAB e AOT nunca recebem rótulo de membrana.
- **Coordenadas sintéticas:** bicamada e vesícula fechada são reconhecidas. Não são reconhecidas: taça aberta (incluindo taça de 80 % da esfera), estrela de seis direções, feixe estreito de 8 moléculas, micela, micela inversa, monocamada, orientação ao acaso e coordenada inválida (NaN).

### 13.3 Tempo por trecho (backend, container de teste)

| Exemplo | Partículas | Tempo por trecho |
|---|---|---|
| SDS | 236 | 4,29 s |
| CTAB + salicilato | 273 | 6,67 s |
| DPPC bicamada | 352 | 9,89 s |
| DPPC vesícula | 352 | 8,23 s |
| AOT | 235 | 6,59 s |

Última execução, com a pilha de desenvolvimento ativa. O número de partículas não mudou com os moldes. Os tempos variam com a carga da máquina: na rodada anterior, a bicamada chegou a 13,1 s e, numa vez, a 16,2 s. O limite do teste é 15 s.

### 13.4 Conferência visual (navegador e cortes)

Arquivos em `documentacao/validacao/exemplos_documentados/`, quatro por exemplo:
- `*_cena.png`: captura da cena 3D no Chrome, cerca de 60 s depois de o card mostrar a mistura (2º trecho), com o enquadramento automático e sem zoom manual; `2_ctab_nasal_vermiforme_cena_zoom.png` é a mesma cena com zoom;
- `*_cards.png`: cards Previsto e Observado no mesmo momento;
- `*_trilha.txt`: o card Observado lido a cada 5 s por mais 150 s (3º a 5º trecho); só as mudanças são gravadas;
- `*_corte.png`: corte 2D das coordenadas do backend após 3 trechos. Pedido no formato da tela; CTAB, vesícula e AOT foram refeitos com o código final.

Um agente separado avaliou a primeira rodada de capturas. Correções feitas a partir dessa avaliação e da segunda rodada, cada uma com teste que falhou antes e passou depois:

1. **Bicamada e vesícula DPPC apareciam como glóbulos.** Agora um molde visual de membrana atua só nesses dois exemplos e está declarado nas notas do card. A forma da membrana na cena é imposta pelo molde, não emergente.
2. **Fração organizada 0 % e "agregado em reorganização" no DPPC e no AOT.** O analisador exigia c/CMC ≥ 1, e nesses exemplos a CMC não se aplica, embora orientação (0,89–0,99), núcleo (1,0) e forma passassem. Agora, só nos exemplos cuja CMC não se aplica, a geometria decide sozinha. Fora deles, a exigência de c/CMC continua.
3. **Textos contraditórios no card.** A validação dizia "vem de CPP/c/CMC" nas demonstrações, e "não validado" aparecia ao lado de "previsão validada" no SDS. A nota de CMC do DPPC e do AOT estava ausente.
4. **CTAB e AOT com 0 % no 2º trecho.** A captura (≈ 60 s) cai no 2º trecho, e os testes só olhavam o 3º. Uma sonda de 8 trechos (`.runtime/sonda/`, fora do repositório) mostrou duas causas:
   - **AOT:** com dois núcleos, duas micelas inversas (20 + 19 moléculas) se fundiam no 2º trecho. O haltere reprovava a forma, e do 3º trecho em diante havia uma micela só, de 39. O exemplo agora usa um núcleo: uma micela de 39 forma-se já no 1º trecho e fica organizada em todos os trechos.
   - **CTAB:** o critério de cilindro reprovava no 2º trecho por pouco, com razão de **variâncias** 1,58 para o limite 1,6. Em eixos, é uma razão de só ~1,26. Com 27 moléculas, o cilindro-alvo das forças gerais é curto (meio comprimento 1,65 para raio 1,17). A oscilação era o sintoma; a causa era o critério aceitar um agregado quase redondo como cilindro (item 6).
5. **Bicamada e vesícula medidas como "aproximadamente esférico".** A forma medida sem a previsão ganhou um detector de membrana que usa só as coordenadas, com no mínimo 12 moléculas:
   - **Lamelar:** cadeias alinhadas (S ≥ 0,75); cabeças nas duas faces e mais longe do plano médio que a própria cauda; caudas espalhadas no plano (variância lateral > 2 × a normal).
   - **Casca fechada:** caudas numa casca oca; cabeças dentro e fora; cadeias radiais; nenhuma abertura sem caudas maior que 45°.
   - **Medido nas cenas:** bicamada com S = 0,94–0,98 e variância lateral 7,4 × a normal; vesícula com abertura máxima de 41°; SDS, CTAB e AOT com S ≤ 0,54.
6. **Revisão independente do branch (crítico): o CTAB aparecia como "micela cilíndrica/wormlike" 100 % organizado, com a forma medida "aproximadamente esférico".** (Estado intermediário; o item 7 substitui o resultado do CTAB e o escopo da regra.)
   - **Regra nova:** nos exemplos documentados, cilindro, bicamada e vesícula só recebem o rótulo da cena quando a forma medida sem a previsão concorda (alongado, lamelar ou casca). Sem isso, o agregado fica "agregado em reorganização" e não conta na fração organizada.
   - **Efeito no CTAB:** passa a 0 % em todos os trechos.
   - **Reversão:** um espaçamento axial tentado antes foi revertido. Ele só espalhava os centros de cauda, a mesma grandeza que o critério mede.
   - **Detector endurecido** a partir de achados importantes da mesma revisão: um feixe estreito virava lamelar, e uma taça de 80 % ou uma estrela viravam casca.
   - **Pedidos sem exemplo** mantêm o comportamento anterior (ver 13.5).

7. **Rodada final (autorizada pelo autor).**
   - **CTAB, molde visual cilíndrico exclusivo do exemplo:** cabeças numa hélice de ângulo áureo na superfície, caudas apontando para o eixo, 0,33 de comprimento por molécula. O salicilato continua na interface. O molde está declarado na nota do card como recurso ilustrativo, com a densidade não real.
   - **Vesícula com cavidade:** as cabeças internas ficam a 1,6 do centro. O agrupamento do analisador usava o raio de uma cauda (2,15) e partia a casca em fragmentos de 4–5 moléculas. O raio entre moléculas agora cresce com √(nº de caudas): 3,04 entre lipídios de duas caudas, e moléculas de uma cauda não mudam. A vesícula inteira (36) vira um agregado.
   - **Todo pedido:** cilindro, bicamada e vesícula só recebem o rótulo da previsão quando a forma medida sem a previsão confirma. Sem confirmação, com orientação e núcleo bons, o rótulo é "agregado orientado (forma prevista não confirmada)". CMC, CPP e a previsão não mudam. O teste geral que exigia o rótulo sem confirmação foi corrigido.
   - **Tela 3D:** a câmera enquadra o maior agregado quando chega uma mistura nova e orbita em volta dele. Uma verificação de UI por agente separado, com calibração plantada detectada, achou a órbita presa à origem; corrigido com teste. O chip "na cena" e a linha "Rótulo dos agregados na cena" acrescentam "(recurso visual ilustrativo)" quando a forma confirmada vem do molde de um exemplo documentado.

**Validação em vários trechos** (sonda de 8 trechos no backend e trilha do card no navegador até ~265 s):

| Exemplo | Rótulo na cena | Fração organizada | Forma medida sem a previsão |
|---|---|---|---|
| SDS | micela esférica (calculada) | 0 % no 1º trecho; 62–90 % do 2º ao 8º | pré-agregado → agregado orientado |
| CTAB + salicilato | micela cilíndrica/wormlike (recurso visual ilustrativo) | 100 % nos 8 trechos | agregado alongado (λ3/λ2 ≈ 14 em variância, ≈ 3,7 em eixos) |
| DPPC bicamada | bicamada plana/lamelar (recurso visual ilustrativo) | 100 % nos 8 trechos | agregado lamelar (duas folhas) |
| DPPC vesícula | vesícula/bicamada fechada (recurso visual ilustrativo) | 100 % nos 8 trechos (36 moléculas) | casca fechada de duas folhas |
| AOT | micela inversa (recurso visual ilustrativo) | 100 % nos 8 trechos | agregado aproximadamente esférico |

**O que a cena confirma, exemplo por exemplo:**

| Exemplo | Validação visual | Evidência e ressalva |
|---|---|---|
| SDS | passa | Várias micelas pequenas, com cabeças para fora. É a única forma calculada pelo motor. |
| CTAB + salicilato | passa, com ressalva | O corte mostra um bastão com cabeças nas duas superfícies, caudas para o eixo e salicilato na interface. No navegador, o agregado é uma faixa alongada, mas o salicilato e os íons cobrem boa parte dela; com zoom se lê melhor. A forma é imposta pelo molde. |
| DPPC bicamada | passa | Placa de duas folhas com as caudas no meio, enquadrada. A forma é imposta pelo molde. |
| DPPC vesícula | passa, com ressalva | Agora enquadrada. Casca radial em volta de uma cavidade pequena, com a folha externa esparsa (aspecto de estrela no corte). A forma é imposta pelo molde. |
| AOT | passa | Gota compacta: água e cabeças no centro, caudas para fora. |

### 13.5 Limitações e pendências

- **Pendência científica do SDS com sal (não corrigida).** O ajuste de sal do motor faz o SDS virar "micela cilíndrica" a partir de 0,08 mol/L de força iônica. A literatura situa a transição esfera→bastão acima de cerca de 0,2–0,3 mol/L de NaCl. Por isso o exemplo fica limitado a ≤ 0,07 mol/L, como limite técnico (spec §10).
- **Formas impostas por molde.** Cilindro do CTAB, bicamada e vesícula vêm de moldes visuais exclusivos dos exemplos, declarados nas notas e marcados "(recurso visual ilustrativo)" na cena. O detector confirma a geometria mostrada, não que ela se formaria sozinha. A micela inversa do AOT é guiada por forças visuais (núcleo único, água no centro), também declaradas.
- **Escala molecular simplificada.** O CTAB tem 27 moléculas visuais esticadas num trecho de ~9 unidades; uma micela vermiforme real tem centenas de nanômetros, e a densidade na cena não é a real. A vesícula tem 36 lipídios, com a folha externa esparsa e uma cavidade pequena; uma vesícula real de 60–100 nm tem milhares de lipídios. Nenhum dos dois ganhou partículas.
- **CTAB no navegador.** O salicilato (5 por CTAB na mistura; 1:1 na interface, o resto livre) e os íons cobrem boa parte do bastão na vista padrão. O alongamento é claro no corte 2D e com zoom.
- **Agrupamento por número de caudas.** O raio que liga moléculas num agregado agora depende do número de caudas: 2,15 com uma cauda, como antes, e 3,04 com duas. Isso vale para qualquer pedido com moléculas de duas caudas.
- **Rótulo novo nos pedidos comuns.** Um agregado orientado e compacto cuja forma medida não confirma cilindro, bicamada ou vesícula aparece como "agregado orientado (forma prevista não confirmada)" e não conta na fração organizada. Em pedidos que antes mostravam essas formas, a fração organizada pode cair.
- **Forma medida, classificação geral (menor, não corrigido).** Fora das membranas, o classificador geral ainda recebe orientação e núcleo calculados com o molde previsto. Só o detector de membrana é totalmente independente da previsão.
- **Outros menores (não corrigidos):**
  - a forma medida dominante é escolhida pelo número de agregados, não de moléculas: no SDS, três pré-agregados vencem a micela de 19;
  - os números da sonda de 8 trechos vêm de scripts fora do repositório (`.runtime/sonda/`);
  - o enquadramento automático acontece uma vez por mistura; trechos seguintes mantêm a câmera do usuário.
- **Ainda aberto da tarefa 8 (menor):** o w0 no cartão do catálogo aparece sem formato pt-BR (10.5 em vez de 10,5).
