# Modelagem3D Web Lite v1 — Especificação

Data: 04/11/2026
Status: aprovada com ajustes em 04/11/2026 (itens 1–6 da revisão do autor)
Base: commit `0fedfdc` (estado inicial versionado)

## 1. Objetivo

Lançar uma versão web estável e honesta do Modelagem3D: desenhar a molécula em 2D, ver os parâmetros físico-químicos calculados com métodos leves e confiáveis, identificar a classe do surfactante por regras químicas, montar misturas e visualizar em 3D uma representação do comportamento micelar coerente com esses cálculos.

A versão científica completa (OpenMM, Martini 3, xTB, DFT, MOPAC, dinâmica avançada, IAs treinadas) fica para a etapa 2, descrita na seção 11 apenas como direção.

### Critérios de sucesso

1. Nenhuma resposta HTTP 500 em toda a bateria de regressão (seção 8).
2. Todo campo do painel químico mostra um valor ou um motivo explícito (`não se aplica` ou `indisponível: <motivo>`). Nenhum campo vazio sem explicação.
3. Todo valor estimado traz fonte, método e confiança. Nenhum valor inventado.
4. As cinco classes de surfactante são identificadas corretamente no conjunto rotulado da seção 8.3.
5. Um surfactante comum acima da CMC (SDS, CTAB, C12E5, betaína, laurato) termina a visualização 3D organizado na morfologia prevista, e não em "monômeros/pré-agregados".
6. A aplicação roda atrás de um domínio público com HTTPS, configurada por variáveis de ambiente, sem segredos no repositório.

### Regras da etapa

- Não excluir funcionalidades nem módulos. Código não utilizado permanece onde está.
- Não alterar a arquitetura sem necessidade. Mudanças pequenas, cada uma com teste.
- Preservar o PostgreSQL, o volume `modelagem3d_pgdata` e as migrações Alembic existentes.
- Preservar o editor 2D, o painel químico e a preparação de misturas.
- Sem treinamento de IA.

## 2. Diagnóstico medido (04/11/2026, API em execução)

| Área | Medição | Consequência para a v1 |
|---|---|---|
| Endpoint `/chemistry/parameters/analyze` | 151 atalhos + 10 casos extremos: 159 respostas 200, 2 respostas 400 corretas (SMILES vazio ou inválido), 0 respostas 500. p95 ≈ 10 ms. Logs do container sem 500. | Os 500 relatados não se reproduzem por SMILES. A bateria precisa cobrir também o caminho `internal_molecule` (grafo do editor), `/micelium/simulate`, `/micelium-ai/*` e as rotas de moléculas e pacotes de análise. |
| Campos indisponíveis no painel | 37 a 55 de 137 campos por molécula. Por átomo, 10 campos (Gasteiger, pares livres, geometria eletrônica, R/S, posição 3D, SASA local, tipo de campo de força, Fukui, reatividade). Por ligação, `comprimento_ideal`. | Grande parte é calculável com RDKit, que já está instalado (seção 4). |
| CMC | Calculada só para os homólogos de alquilsulfato de sódio e de alquiltrimetilamônio. C12E5, laurato de sódio, betaína e demais famílias retornam `None`. | **Causa raiz do 3D travado:** sem CMC, o motor cai em "monômeros/pré-agregados". Uma mistura com qualquer componente sem CMC zera c/CMC da mistura inteira. |
| Motor Micelium | SDS a 3,9×CMC e CTAB a 34×CMC: tendência prevista "micela esférica", morfologia observada após 120 passos "agregado em reorganização" (5 clusters de 4–8 moléculas). | A visualização não converge para a morfologia prevista. |
| Identificação | N-dodecilglicina (anfotérico) → não iônico. Óxido de dodecildimetilamina → não iônico. Dodecanol (álcool graxo, cossurfactante) → surfactante não iônico. Betaína → zwitteriônico (correto). Não existe `amphoteric_ai` e o roteador envia anfotéricos para `zwitterionic_ai`. | As regras de classe precisam de grupos ionizáveis e de estado de protonação. |
| Hospedagem | `VITE_API_URL` fixa em `127.0.0.1` no build. CORS só para localhost. Senha do Postgres escrita no `docker-compose.yml`. Frontend servido por `vite preview`. `APP_ENV: development`. Portas vinculadas a 127.0.0.1. | Seção 7. |
| Hardware de desenvolvimento | 12 CPUs, 6 GB de RAM, sem GPU NVIDIA. OpenMM do container com plataformas `CPU` e `Reference`. PubChem acessível do container. | A v1 não depende de GPU nem de simulação pesada. |

## 3. Funcionalidades da v1

### 3.1 Mantidas sem mudança de comportamento

- Editor 2D completo (desenho, atalhos, tabela periódica, minimapa, hidrogênios, otimização 2D, conversão grafo↔SMILES).
- Biblioteca de moléculas da sessão e preparação de misturas (quantidade em mmol, volume, concentração, Clint).
- Persistência em PostgreSQL (moléculas, pacotes de análise, dados de referência, tabela de treino da IA).

### 3.2 Corrigidas ou completadas

1. **Estabilidade:** bateria de regressão em todas as rotas usadas pela interface (seção 8.1), com correção pontual de cada falha encontrada.
2. **Painel químico completo:** propriedades calculáveis com RDKit preenchidas. As demais vêm com motivo explícito (seção 4).
3. **Ressonância:** número de estruturas de ressonância, átomos e ligações deslocalizados, sistemas conjugados e carga deslocalizada por átomo.
4. **Ionização dependente do pH:** pKa por grupo funcional (tabela de literatura), espécie predominante, carga líquida no pH do ambiente e LogD.
5. **CMC para mais famílias**, por correlações de homólogos publicadas e com domínio declarado (seção 4.4), e CMC de mistura por Clint apenas quando todas as CMCs forem conhecidas, com mensagem explicando qual componente faltou.
6. **Teoria micelar leve:** ΔG de micelização, número de agregação, raios e carga residual pelas equações de Tanford e de pseudofase (seção 4.5).
7. **Identificação das cinco classes por regras** (seção 5).
8. **Visualização 3D coerente com os cálculos** e rotulada como visualização (seção 6).
9. **Preparação para hospedagem web** (seção 7).

### 3.3 Fora da v1

OpenMM, Martini 3, xTB, DFT, MOPAC, dinâmica molecular avançada, treinamento ou inferência de IA especializada, contas de usuário e login, e consultas ao PubChem durante o cálculo do painel. A consulta ao PubChem que já existe permanece opcional, como hoje.

## 4. Cálculos físico-químicos

### 4.1 Arquitetura

Pacote novo, aditivo: `backend/app/modules/chemistry/properties/`. Cada módulo recebe uma molécula RDKit já validada e devolve `dict[str, ParameterValue]`, no mesmo formato `ParameterValue` usado hoje (`value`, `unit`, `source`, `available`, `confidence`, `note`).

```
chemistry/properties/
├── base.py              contrato: ParameterValue, helpers not_applicable() e unavailable()
├── conformer3d.py       ETKDGv3 + MMFF94
├── electronic_basic.py  Gasteiger, pares livres, VSEPR, R/S
├── resonance.py         ResonanceMolSupplier
├── ionization.py        pKa por grupo, espécie no pH, LogD
├── cmc_correlations.py  CMC por família (seção 4.4)
├── micelle_theory.py    Tanford e pseudofase (seção 4.5)
└── orchestrator.py      chama os provedores e devolve um dict único
```

Integração com o código existente:

- `chemistry/parameters/router.py`: `make_response` chama `orchestrator.compute(mol, environment)` e mescla o resultado nos campos atuais. A regra de mescla é: o valor do provedor novo só substitui um campo hoje `available: false`. Campos que já têm valor ficam como estão, exceto os corrigidos por um teste que falhou.
- `chemistry/parameters/validated_calculations.py` continua sendo o núcleo de classe, CMC (SDS/CTAB), HLB e CPP, usado pelo painel e pela IA. `cmc_correlations.py` é chamado pelo núcleo quando a família não é SDS/CTAB.
- Os nomes dos 137 campos e o contrato do frontend não mudam.
- `calculation_page.py`, `miriam21_engine.py` e os arquivos `*_example.py` não são importados hoje e continuam onde estão, sem alteração.

### 4.2 Desempenho

Todos os provedores da v1 são leves (RDKit). Meta: p95 do `/analyze` ≤ 300 ms para moléculas com até 100 átomos pesados, medido pela bateria.

- `conformer3d` gera 1 confórmero com semente fixa (`randomSeed=0xf00d`), no máximo 500 iterações de MMFF e tempo limite de 2 s. Se o tempo se esgotar, os campos 3D voltam `indisponível: geração 3D excedeu o tempo`.
- Cache LRU em memória no processo (chave: SMILES canônico + ambiente), com 512 entradas.
- Moléculas com mais de 150 átomos pesados pulam `conformer3d` e `resonance` (`indisponível: molécula acima do limite da versão web`).

### 4.3 Métodos e limites de validade

| Campo(s) | Método | `confidence` | Limite de validade (vai na `note`) |
|---|---|---|---|
| posição 3D, raio de giração, NPR1, NPR2, volume de van der Waals, SASA total e local, energia conformacional, tipo de átomo MMFF, comprimento de ligação | RDKit ETKDGv3 + MMFF94; SASA por `rdFreeSASA`; volume por `AllChem.ComputeMolVolume` | `medium` | Um confórmero de baixa energia em fase gasosa. Não representa o conjunto de conformações em solução. Sem parâmetros MMFF (alguns metais), a otimização usa UFF e o rótulo informa isso. Se nem UFF servir, `indisponível`. |
| vetor de momento dipolar | Cargas de Gasteiger × coordenadas MMFF | `low` | Estimativa por cargas empíricas. Serve para direção e ordem de grandeza, não como valor experimental. |
| carga de Gasteiger, pares livres, geometria eletrônica, R/S | RDKit (`ComputeGasteigerCharges`, contagem de elétrons de valência, regra VSEPR por domínios, `AssignStereochemistry`/CIP) | `high` para pares livres, R/S e VSEPR; `low` para Gasteiger | Gasteiger é empírico e só indica tendência de polarização. |
| ressonância: número de estruturas, átomos e ligações deslocalizados, sistemas conjugados, carga deslocalizada | `rdkit.Chem.ResonanceMolSupplier` (no máximo 64 estruturas) | `high` | Enumera estruturas de Lewis formais e não pondera a contribuição de cada uma. |
| pKa, espécie predominante, carga líquida no pH, LogD | Tabela SMARTS de pKa de literatura por grupo (ácido carboxílico 4,8; ácido sulfônico −1,9; monoéster sulfato −3; fosfato 2,1 e 7,2; fenol 10,0; amina primária alifática 10,6; secundária 11,0; terciária 9,8; piridina 5,2; anilina 4,6; imidazol 7,0; óxido de amina 4,6; amônio quaternário: carga permanente) + Henderson–Hasselbalch por sítio | `estimated` | Sítios tratados como independentes, sem acoplamento eletrostático nem tautomeria. Erro típico de ±1 unidade de pKa. A tabela de valores e suas referências fica no próprio módulo. |
| densidade, pontos de fusão e ebulição, pressão de vapor, tensão superficial, viscosidade, ΔG de solvatação, calor de formação, HOMO, LUMO, gap, potencial de ionização, afinidade eletrônica, cargas quânticas, Fukui | Nenhum na v1 | `indisponível` | Nota: "Exige método da etapa 2 (xTB, MOPAC, Joback ou dado experimental). A v1 não estima este valor." |
| HLD, NAC | Nenhum na v1 | `indisponível` | Exige parâmetros empíricos de óleo e de surfactante tabelados. |

**Decisão:** propriedades térmicas e de transporte (Tb, Tm, densidade, viscosidade etc.) **não** recebem estimativa por contribuição de grupos na v1. A lista de exclusões da etapa inclui só métodos quânticos, mas a regra "não inventar valores" pede que cada estimativa venha com validação própria, e isso aumentaria o escopo. Essas propriedades ficam para a etapa 2, junto com o Joback validado.

### 4.4 CMC por correlações de homólogos

Forma: `log10(CMC / mol·L⁻¹) = A − B·n`, com `n` = carbonos da cauda linear, em água a 25 °C. Os valores de A e B vêm de tabelas de livro-texto para cada família.

| Família | Domínio de n | Referência das constantes |
|---|---|---|
| Alquilsulfato de sódio | 8–18 | Correlação já existente (âncora SDS), mantida |
| Brometo de alquiltrimetilamônio | 8–18 | Correlação já existente (âncora CTAB), mantida |
| Alquilsulfonato de sódio | 10–16 | Rosen e Kunjappu, *Surfactants and Interfacial Phenomena*, 4ª ed., capítulo 3 (tabelas de constantes A e B; página e tabela exatas registradas na implementação) |
| Carboxilato (sabão) de sódio ou potássio | 8–18 | Idem |
| Cloreto de alquiltrimetilamônio | 10–18 | Idem |
| Alquilpiridínio (cloreto/brometo) | 10–16 | Idem |
| Alquilbetaína / alquilsulfobetaína | 10–16 | Idem |
| Óxido de alquildimetilamina | 10–14 | Idem |
| Álcool etoxilado linear CnEm | n 8–16, m 4–12 | Correlação de dois parâmetros em n e m, com constantes da mesma fonte |

Regras:

- Antes de implementar, cada par (A, B) é transcrito com página e tabela da referência para o arquivo `cmc_correlations.py`. Se a constante de uma família não puder ser verificada na fonte, essa família fica fora da v1 e o campo volta `indisponível: família sem correlação verificada`.
- Fora do domínio de n, fora da água ou fora de 15–40 °C: `indisponível` com o motivo.
- A correção salina que já existe em `validated_calculations.py` continua a valer só para iônicos. As famílias novas usam essa mesma correção apenas se a referência da família trouxer o coeficiente correspondente; caso contrário, a CMC só é dada para força iônica ≤ 0,01 mol/L e a nota informa isso.
- `confidence: estimated`. A nota informa a família, a faixa de n e que é correlação de homólogos.
- Mistura (Clint): a mesma regra de hoje. Se um componente não tiver CMC, a mensagem passa a nomear esse componente.

### 4.5 Teoria micelar leve

Só é calculada quando o painel tem CMC disponível e cauda hidrocarbonada linear.

| Campo | Equação | Notas |
|---|---|---|
| comprimento máximo da cauda | l_max = 0,154 + 0,1265·n (nm) | Tanford |
| volume da cauda | v = 0,0274 + 0,0269·n (nm³) | Tanford |
| número de agregação estimado | N_agg = (4/3)·π·l_max³ / v (teto geométrico da esfera) | Rotulado como limite superior geométrico, não como medição |
| raio do núcleo hidrofóbico | R_núcleo = l_max | Micela esférica |
| raio da micela esférica | R = l_max + espessura da cabeça (tabela por família) | `estimated` |
| raio da micela cilíndrica | R_cil = l_max | Só quando CPP está entre 1/3 e 1/2 |
| ΔG de micelização | Não iônico: ΔG = RT·ln X_cmc. Iônico: ΔG = (1+β)·RT·ln X_cmc, com X_cmc = CMC / 55,5 | β por família (SDS ≈ 0,6 e CTAB ≈ 0,8, valores de literatura documentados no módulo). Sem β conhecido, iônicos ficam `indisponível`. |
| carga residual, contraíons ligados, densidade de carga | Carga residual = N_agg·(1−β); contraíons = N_agg·β; σ = carga residual · e / (4πR²) | Iônicos com β conhecido |
| comportamento micelar previsto | CPP < 1/3 → esférica; 1/3–1/2 → cilíndrica; 1/2–1 → bicamada ou vesícula; > 1 → inversa | Israelachvili–Mitchell–Ninham (1976). Já existe; mantido. |

## 5. Identificação das cinco classes por regras

Componente: `micelium/IA/molecular_identity_ai.py` (existente, aprimorado), que usa `chemistry/properties/ionization.py`.

### 5.1 Pré-condição de surfactante

A molécula precisa ter um domínio hidrofóbico (cauda alquílica linear ou ramificada com pelo menos 8 carbonos contíguos ou equivalente aromático-alquílico) **e** um grupo de cabeça reconhecido.

**Anfifílicos de cabeça fraca** (álcoois graxos com um único –OH, como dodecanol; ácidos graxos neutros; aminas graxas neutras) não recebem classificação absoluta. A identificação devolve:

- classe estrutural `nonionic` (ou a classe correspondente ao grupo ionizável, no caso de ácido ou amina), com `amphiphile_role: "surfactant_or_cosurfactant"`;
- a nota: "Cabeça polar fraca: pode atuar como surfactante ou cossurfactante, conforme o sistema (outros surfactantes, óleo, concentração). A v1 não decide esse papel.";
- nenhuma CMC calculada por correlação de família, porque não há correlação fundamentada de CMC para esses anfifílicos na v1.

Em mistura com um surfactante, o painel mostra o anfifílico de cabeça fraca como possível cossurfactante. No 3D, ele aparece como soluto disperso que pode ser incorporado aos agregados, sem CMC própria.

### 5.2 Regras de classe

A classe é estrutural e não muda com o pH. A espécie predominante é calculada à parte, no pH do ambiente.

| Classe | Regra estrutural | Exemplos |
|---|---|---|
| Aniônica | Só grupos ácidos de cabeça: sulfato, sulfonato, carboxilato, fosfato ou fosfonato, sem grupo básico ou catiônico na cabeça | SDS, laurato de sódio, LAS |
| Catiônica | Só grupos catiônicos ou básicos: amônio quaternário, piridínio, imidazólio, amina protonável, sem grupo ácido na cabeça | CTAB, DTAB, cloreto de cetilpiridínio |
| Zwitteriônica | Cátion **permanente** (N⁺ quaternário, P⁺) + grupo aniônico | Betaínas, sulfobetaínas, fosfatidilcolina |
| Anfotérica | Grupo básico **ionizável** (amina primária, secundária ou terciária, óxido de amina) + grupo ácido ionizável, ou óxido de amina isolado, com carga líquida dependente do pH | N-alquilglicina, anfoacetatos, óxido de dodecildimetilamina |
| Não iônica | Cabeça polar sem grupos ionizáveis no intervalo de pH 2–12: polioxietileno, poliglicerol, açúcar (glicosídeo), éster de sorbitano, amida de etanolamina | C12E5, Tween, APG |

Saída adicional, em `MolecularIdentityResult.provenance` e `descriptors.raw_descriptors`, sem mudar o esquema público:

- `rules_fired`: lista das regras SMARTS que dispararam.
- `species_at_ph`: carga líquida e classe efetiva no pH do ambiente (por exemplo: "anfotérico; em pH 2,0 comporta-se como catiônico").
- `class_confidence`: continua não calibrada (`class_confidence_calibrated: false`).

### 5.3 IAs especializadas

- O arquivo `amphoteric_ai.py` é criado seguindo `SpecializedSurfactantAI`, como as outras quatro classes.
- O `SurfactantAIRouter` passa a enviar `amphoteric` para `amphoteric_ai`.
- As cinco IAs mantêm a linha de base heurística atual, e a resposta delas informa `model_status: "not_trained"`. Não há treinamento nesta etapa.

O painel 2D passa a mostrar "anfotérico" e "zwitteriônico" separados, em vez de "anfotérico/zwitteriônico".

## 6. Ambiente 3D (Three.js)

### 6.1 Princípio

O ambiente 3D da v1 é uma **visualização representativa**: uma animação coarse-grained cujo estado final é definido pelos cálculos (CMC, c/CMC, CPP, N_agg). Não é simulação física. A interface diz isso explicitamente, e o termo "simulação física" fica reservado para a etapa 2.

### 6.2 Mudanças no motor Micelium (pequenas, no código existente)

1. **CMC para mais famílias** (seção 4.4) passa ao motor pela mesma interface `cmc_mmol_l` que já existe. Isso desbloqueia C12E5, laurato, betaína e os demais.
2. **Convergência:** quando c/CMC > 1, a visualização termina na morfologia prevista pelo CPP, com o tamanho dos agregados limitado pelo N_agg da seção 4.5 e escalado ao número de moléculas visuais. A fração de moléculas agregadas segue o balanço de pseudofase: monômeros livres ≈ CMC; o restante vai para os agregados. Ajustes no plano de formação e no número de passos efetivos, sem reescrever o motor.
3. **Abaixo da CMC:** monômeros dispersos com agregados transitórios (comportamento atual, mantido).
4. **Mistura com componente sem CMC:** o painel continua estrito, como manda a seção 4.4: a CMC da mistura fica `indisponível` e a nota nomeia o componente sem CMC. A visualização, para não travar em "monômeros/pré-agregados", usa a CMC de Clint dos componentes conhecidos e mostra o componente sem CMC como soluto disperso. O painel "Previsto" informa explicitamente: "visualização aproximada: ignora <componente> por falta de CMC".
5. **Movimento:** o movimento browniano e a flexibilidade das caudas que já existem continuam, e são o que dá à cena o aspecto de "ambiente real".

### 6.3 Mudanças no frontend 3D

- Selo fixo no visualizador: **"Visualização representativa — não é simulação física"**, com um link para um texto curto explicando o que define a cena.
- O painel de resultados separa **"Previsto pelos cálculos"** (CMC, c/CMC, CPP, morfologia, N_agg, com fonte e confiança) de **"Observado na visualização"** (clusters, tamanho médio, fração organizada).
- O renderizador continua com `InstancedMesh`. Meta de desempenho: ≥ 30 fps com 2.500 partículas num notebook com GPU integrada (o limite `max_particles` atual).

## 7. Otimizações e preparação para hospedagem

### 7.1 Backend

- `APP_ENV` e `BACKEND_CORS_ORIGINS` passam a vir de `.env`, sem valor padrão de desenvolvimento em produção.
- Senha do Postgres e `DATABASE_URL` só em `.env` (o `docker-compose.yml` passa a referenciar `${POSTGRES_PASSWORD}`). A troca de senha de um banco que já existe é manual e documentada: o volume é preservado e a senha só muda via `ALTER USER` no banco existente.
- Uvicorn com `--workers` configurável (padrão 2) e `--proxy-headers`.
- Limite de tamanho do corpo da requisição e validação de `max_particles`/`steps`, que já existe, mantida.
- `/micelium/simulate` (1,9–6,3 s medidos) passa a responder com compressão gzip (`GZipMiddleware`).
- Rotas de demonstração (`openmm_stream` `/ws/openmm`) ficam desativadas em produção por configuração, sem exclusão do código.

### 7.2 Frontend

- `VITE_API_URL` relativa (`/api/v1`) por padrão, para o mesmo domínio servir interface e API através do proxy reverso.
- Servir o build estático pelo proxy reverso (Caddy), no lugar de `vite preview`.
- Medir o bundle de produção (`npm run build` com relatório de tamanho). Se o chunk principal passar de 1 MB gzip, aplicar code splitting com `React.lazy` no visualizador 3D e no editor 2D, nessa ordem.
- Debounce de 400 ms no recálculo do painel durante a edição, se ainda não houver, e cancelamento da requisição anterior com `AbortController`.

### 7.3 Publicação

**Decisão adiada:** VPS ou serviço gerenciado (ex.: Render, Railway, Fly.io com Postgres gerenciado). A v1 deixa as duas opções possíveis:

- As imagens Docker do backend e do frontend são autossuficientes, configuradas só por variáveis de ambiente (`DATABASE_URL`, `BACKEND_CORS_ORIGINS`, `APP_ENV`, `UVICORN_WORKERS`, `PORT`).
- O backend lê a porta de `PORT` (padrão 8000), como os serviços gerenciados exigem.
- O frontend tem uma imagem de produção (build estático servido por Caddy). Se o serviço gerenciado servir arquivos estáticos direto, ela não é necessária.
- O backend aplica as migrações Alembic na inicialização, como faz hoje, e funciona com qualquer PostgreSQL 16 acessível por `DATABASE_URL`.

O caminho VPS é documentado e testado localmente. O caminho gerenciado é documentado como lista de variáveis e comandos, sem teste em provedor real nesta etapa.

Caminho VPS: Docker Compose, o mesmo modelo de execução usado hoje no Ubuntu.

```
Internet ──HTTPS──► Caddy (TLS automático, Let's Encrypt)
                     ├── /           → arquivos estáticos do frontend (dist/)
                     └── /api/*      → backend:8000 (rede interna do Compose)
                                        └── postgres:5432 (rede interna, sem porta pública)
```

- Arquivo novo `docker-compose.prod.yml`, sobreposto ao atual (o arquivo de desenvolvimento continua funcionando como hoje).
- Serviço `caddy` novo; o Postgres não expõe porta pública.
- Backup: o `iniciar_linux.sh` já faz `pg_dump` antes das migrações. Em produção, um script `backup_producao.sh` faz o mesmo e mantém os últimos 7 dumps.
- Requisitos mínimos do servidor: 2 vCPUs, 2 GB de RAM e 20 GB de disco (estimativa para RDKit + Postgres + Caddy; validada pela medição de memória da seção 8.5).
- Documento `documentacao/publicacao/PUBLICAR.md` com o passo a passo: DNS, `.env`, `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`, verificação e backup.

A escolha entre VPS e serviço gerenciado, e do provedor, fica com o autor do projeto. A spec não depende dessa escolha.

### 7.4 Segredos e git

Auditoria de 04/11/2026: nenhum `.env` real nem dump entrou nos commits; `backups/` e `arquivo/` estão ignorados. A senha de desenvolvimento do Postgres está gravada em `backend/docker-compose.yml` (2×), `backend/alembic.ini`, `backend/.env.example` e `documentacao/recuperacao/CORRECOES_EXISTENTES.patch`. O repositório não tem remoto.

- `docker-compose.yml` passa a usar `${POSTGRES_PASSWORD}` e `${DATABASE_URL}`, lidos de `backend/.env` (ignorado pelo git). O `iniciar_linux.sh` cria esse `.env` a partir do exemplo na primeira execução, preservando a senha atual do banco local para não quebrar o volume existente.
- `alembic.ini` e `.env.example` recebem um marcador (`CHANGE_ME`) no lugar da senha. O `alembic/env.py` já lê a URL de `settings.database_url`, então o valor do `.ini` não é usado.
- No patch histórico da documentação, só a senha é substituída por `<redacted>`.
- A senha de produção é sempre diferente da de desenvolvimento.
- Um teste (`tests/test_no_secrets.py`) falha se `git ls-files` incluir `.env` real ou se o conteúdo rastreado tiver a senha conhecida ou URL de banco com senha literal.
- Limpeza do histórico: os commits atuais ainda contêm a senha de desenvolvimento. Antes do primeiro envio para um remoto, o histórico é reescrito (o repositório é local e tem poucos commits), mediante confirmação do autor.

## 8. Testes

Todos os testes novos são automatizados. Os existentes (1.262 casos, segundo `documentacao/validacao/relatorio_validacao_calculos.md`) continuam passando.

### 8.1 Estabilidade HTTP (regressão permanente)

`backend/tests/test_api_stability.py`, parametrizado:

- `/chemistry/parameters/analyze` por SMILES e por `internal_molecule`, nos 151 atalhos de `tests/fixtures/molecular_catalog.json` mais estes casos extremos: SMILES vazio, SMILES inválido, radical, sal metálico, isótopo, estereocentro, cadeia com 160 carbonos, peptídeo, éster etoxilado, sal com vários contraíons.
- `/micelium-ai/analyze` e `/micelium-ai/predict` nos mesmos SMILES.
- `/micelium/simulate` com: um surfactante acima e abaixo da CMC, mistura de dois surfactantes, mistura com um componente sem CMC, não surfactante puro, solvente apolar.
- Rotas de moléculas e pacotes de análise usadas pela interface (salvar, listar, carregar).

Critérios: nenhuma resposta 5xx; entradas inválidas → 400/422 com mensagem; JSON sem NaN ou Infinity; todo `ParameterValue` com `available: false` tem `note` não vazia.

### 8.2 Cálculos (referências independentes, tolerância definida antes)

| Teste | Referência | Critério |
|---|---|---|
| Comprimentos de ligação MMFF | C–C 1,53; C=C 1,34; aromática 1,39; C=O 1,22; C–O 1,43 Å | ±0,03 Å |
| Geometria VSEPR | Metano tetraédrico, eteno trigonal, CO₂ linear, água angular com 2 pares livres | Exato |
| R/S | Alanina L = S; (R)-2-butanol | Exato |
| Ressonância | Benzeno 2 estruturas; acetato 2; nitrometano 2; acetamida 2; etano 1 | Exato |
| pKa e espécie no pH | Ácido acético, fenol, metilamina, piridina, anilina, glicina | Carga líquida correta em pH 2, 7 e 12 |
| CMC por família | Valor experimental de 2 membros por família, de fonte diferente da que forneceu as constantes (Mukerjee e Mysels, NSRDS-NBS 36, 1971) | Dentro de um fator 2 (±0,3 em log10) |
| Tanford | l_max e v para n = 12 | 1,672 nm e 0,350 nm³ (exato para a fórmula) |
| ΔG de micelização | SDS com CMC 8,2 mM e β 0,6 | Igual ao cálculo manual com tolerância de 1e-6 |
| Domínio de aplicação | Hexano, fenol e glicose não recebem CMC, CPP nem N_agg; cadeia fora do domínio de n recebe `indisponível` | Exato |
| Valores não inventados | Nenhum campo da lista "Nenhum na v1" da seção 4.3 aparece com valor | Exato |

### 8.3 Identificação das classes

`backend/tests/test_surfactant_identification.py`, com um conjunto rotulado montado na implementação a partir de surfactantes de literatura:

- 8 aniônicos, 8 catiônicos, 8 não iônicos, 6 zwitteriônicos e 6 anfotéricos, com SMILES e referência por item.
- 11 não surfactantes: hexano, etanol, glicose, ácido benzoico, nitrobenzeno, ureia, glicina, acetato de sódio, cloreto de tetrametilamônio, benzeno, octano.
- 3 anfifílicos de cabeça fraca: dodecanol, ácido dodecanoico neutro, dodecilamina neutra. Esperado: `amphiphile_role: "surfactant_or_cosurfactant"`, sem CMC por correlação.

Critério: 100 % de acerto nesse conjunto, com a matriz de confusão gravada num relatório. Um erro corrige a regra; o rótulo do conjunto não é alterado para fazer o teste passar.

Óxido de amina: óxido de dodecildimetilamina é classificado como anfotérico. Em pH 2, espécie catiônica (N–OH⁺); em pH 7, forma neutra/zwitteriônica N⁺–O⁻ predominante (pKa ≈ 4,6).

Teste de pH: N-dodecilglicina em pH 2 → espécie catiônica; em pH 12 → espécie aniônica; classe estrutural anfotérica nos dois casos.

### 8.4 Visualização 3D

`backend/app/modules/micelium/test_organization_geometry.py` (existente, ampliado):

- SDS, CTAB, C12E5 e betaína a 3×CMC: morfologia observada no último quadro igual à prevista pelo CPP.
- SDS a 0,1×CMC: sem agregado estável.
- Mistura SDS + componente sem CMC: resposta 200, componente sem CMC disperso e mensagem nomeando o componente.
- Ligações preservadas e coordenadas finitas em todos os quadros.

Frontend (Vitest): o selo "Visualização representativa" aparece, e o painel separa "Previsto" de "Observado".

### 8.5 Desempenho e publicação

- Bateria 8.1 com tempos: p95 do `/analyze` ≤ 300 ms; `/micelium/simulate` com 2.500 partículas ≤ 10 s.
- Memória do backend em repouso e sob a bateria (`docker stats`) registrada para dimensionar o servidor.
- Teste de fumaça da publicação: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` válido; com a pilha de produção em execução local, `/` responde 200, `/api/v1/health/database` responde 200 e o Postgres não fica acessível do host.
- `npm run build` e `npx vitest run` sem erros.

## 9. Ordem de execução

Cada passo é um commit pequeno com seus testes.

0. Segredos fora dos arquivos versionados (7.4).
1. Bateria de estabilidade (8.1) e correção pontual das falhas encontradas.
2. Provedores RDKit: `electronic_basic`, `conformer3d`, `resonance` + mescla no painel.
3. `ionization` + regras das cinco classes + `amphoteric_ai` + roteador.
4. `cmc_correlations` + `micelle_theory`.
5. Convergência da visualização 3D + selo e separação "Previsto/Observado" no frontend.
6. Otimizações (7.1, 7.2) e medição do bundle.
7. Publicação (7.3) e teste de fumaça.

## 10. Riscos

| Risco | Mitigação |
|---|---|
| Constantes de CMC de uma família não verificáveis na fonte | A família fica fora da v1 (regra 4.4); as demais continuam |
| Geração 3D lenta ou falhando em moléculas grandes ou exóticas | Tempo limite, limite de átomos e retorno `indisponível` com motivo (4.2) |
| Mudança na classificação altera resultados que já estão salvos no banco | Resultados antigos não são reescritos; o painel recalcula ao abrir. A versão do motor de identificação sobe para que se possa distinguir resultados antigos dos novos |
| Troca de senha do Postgres em produção | Procedimento manual documentado; o volume é preservado |
| A visualização convergir sempre parecer "simulação" | Selo fixo e separação "Previsto/Observado" (6.3) |

## 11. Etapa 2 (só direção, sem compromisso nesta spec)

- Camada lenta `/analyze/deep` com xTB (orbitais, dipolo, IP/EA, Fukui), MOPAC PM7 (ΔHf), Joback validado e valores experimentais do PubChem, com prioridade por fonte e cache por InChIKey.
- Modo físico 3D com OpenMM + Martini 3 (biblioteca curada de topologias e mapeamento automático), começando por um benchmark de viabilidade em CPU, além do controle concentração solicitada × concentração da caixa.
- Interface `EnvironmentSurrogate` para IA auxiliar opcional do ambiente.
- Treinamento das cinco IAs especializadas com a tabela `micelium_ai_training_samples`.
- **Preservar informação química na conversão do editor** (pedido do autor, 04/11/2026): o grafo do editor 2D (`GraphAtomInput` e o modelo do frontend) passa a carregar elétrons desemparelhados, hidrogênios explícitos, isótopo e estereoquímica, para que a ida e volta desenho → grafo → SMILES não altere a espécie. Hoje `[CH3]` vira CH₄, e isso está registrado como falha esperada em `tests/test_api_stability.py::test_editor_flow[radical]`. Critério de aceite: esse teste deixa de ser `xfail` e todos os 151 atalhos mantêm fórmula, carga, radicais, isótopos e estereocentros na ida e volta.
