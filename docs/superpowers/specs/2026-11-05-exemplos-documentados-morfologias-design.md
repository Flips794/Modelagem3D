# Exemplos documentados de morfologias — Especificação (complemento da Web Lite 1.0)

Data: 05/11/2026
Status: arquitetura aprovada pelo autor em 05/11/2026; revisão 2 incorpora os ajustes 1–4 dessa aprovação
Base: branch `web-lite-v1` (commit `9d9d214`); trabalho no branch `web-lite-v1-exemplos`

## 1. Objetivo

Demonstrar **5 morfologias com 4 anfifílicos** no ambiente 3D existente. Cada exemplo tem condições tiradas de referências experimentais e uma origem da forma declarada sem ambiguidade:

| id | Morfologia mostrada | Anfifílico | Origem da forma |
|---|---|---|---|
| `sds_esferica` | micela esférica (aproximação) | SDS | **calculada** pelo motor atual (previsão validada) |
| `ctab_nasal_vermiforme` | micela cilíndrica/vermiforme | CTAB + salicilato de sódio | **exemplo documentado** (demonstração representativa) |
| `dppc_bicamada_hidratacao` | recorte de bicamada de uma estrutura lamelar | DPPC | **exemplo documentado** (protocolo de preparo) |
| `dppc_vesicula_extrusao` | vesícula unilamelar | DPPC | **exemplo documentado** (protocolo de preparo) |
| `aot_inversa_isooctano` | micela inversa com núcleo aquoso | AOT | **exemplo documentado** (parâmetro principal w0) |

### Critérios de sucesso

1. Cada exemplo, carregado pelo painel 2D→3D e dentro das suas condições documentadas, termina a visualização na morfologia da tabela acima, com cabeças polares e caudas apolares na orientação correta (testes de tendência, seção 8).
2. O DPPC e o AOT aparecem com **duas caudas** por molécula, ligadas à mesma cabeça.
3. A resposta diz explicitamente de onde veio a forma: `morphology_source = "calculated"` ou `"documented_example"`.
4. Fora das condições documentadas, o motor volta ao cálculo normal e avisa: "fora das condições documentadas", com o motivo.
5. Nenhuma CMC, CPP, parâmetro ou transição inventados. Cada limite traz a sua natureza: **condição experimental verificada**, **condição de protocolo citada** ou **limite técnico** (seção 2).
6. Sem `documented_example_id`, o comportamento atual não muda: a suíte existente inteira continua verde.
7. Desempenho dentro dos limites atuais da tela 3D (≤ 900 partículas, ≤ 240 moléculas visuais por pedido).

### Fora do escopo

- Outras morfologias, outros anfifílicos e transições entre formas.
- Qualquer motor universal de previsão de forma, novas famílias de CMC ou novo cálculo de CPP.
- Correção do ajuste de sal do SDS (seção 10, pendência registrada).
- Ramificação da cadeia 2‑etil‑hexila do AOT: cada cauda é uma cadeia linear de contas. Isso é declarado na nota do exemplo.
- Representar várias lamelas empilhadas ou a vesícula multilamelar do DPPC hidratado.
- Reconhecer automaticamente essas moléculas quando desenhadas à mão no editor.

## 2. Catálogo

Arquivo novo: `backend/app/modules/micelium/documented_examples.py`, com dados imutáveis (dataclasses `frozen`). Cada exemplo tem:

- `id`, `title`, `example_version` (`"1.0.0"`) e `last_reviewed_at` (`"2026-11-05"`);
- `kind`: `"validated_prediction"` (só o SDS) ou `"representative_demo"`;
- `documented_morphology`: rótulo no vocabulário do motor (`"micela esférica"`, `"micela cilíndrica/wormlike"`, `"bicamada plana/lamelar"`, `"vesícula/bicamada fechada"`, `"micela inversa"`);
- `components`: SMILES, nome, papel, quantidade em mmol e, quando necessário, `is_surfactant`, `tail_carbon_count` (carbonos **por cadeia**) e `tail_chain_count` (seção 4.4), todos com valor factual;
- `environment`: volume, temperatura, solvente e força iônica;
- `conditions`: lista de condições conferidas pela função `evaluate(example, request) -> ExampleVerdict(within_range, reasons)`. Cada condição tem:
  - `parameter` e o intervalo ou valor;
  - `basis`, com um destes valores:
    - `"experimental"`: medida ou observada na referência citada;
    - `"protocol"`: prática de preparo descrita em fonte citada;
    - `"technical"`: tolerância de entrada, limite físico do meio ou concordância com o modelo, sem valor experimental;
  - `source` (referência ou justificativa) e `label` (texto que aparece na tela);
- `protocol`: texto curto do preparo e das condições;
- `references`: lista com autores, ano, revista e DOI ou URL;
- `notes`: limitações declaradas.

A tela mostra cada condição com a sua natureza. Um limite técnico nunca aparece como faixa experimental.

### 2.1 SDS — micela esférica (previsão validada)

- Ponto: SDS `CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]`, 3 mmol em 100 mL (30 mM), água, 298,15 K, força iônica 0,01 mol/L.
- Condições:

  | Parâmetro | Valor | Natureza | Fonte ou justificativa |
  |---|---|---|---|
  | solvente | água | experimental | SANS de SDS em água sem sal ([PMC4487321](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4487321/)) |
  | c/CMC | > 1 | experimental | CMC de 8,16 mM a 25 °C (NSRDS‑NBS 36, já no projeto) |
  | temperatura | 20–30 °C | technical | domínio atual da correlação de CMC do projeto |
  | força iônica | ≤ 0,07 mol/L | technical | maior valor em que o modelo atual ainda prevê esfera; ver seção 10 |

- Forma: vem do cálculo existente.
- Nota: os estudos de SANS descrevem a micela de SDS em água sem sal como elipsoide levemente achatado; a tela mostra "esférica (aproximação)".
- Se o cálculo devolver outra forma dentro das condições, a resposta traz o aviso "cálculo diverge da referência" (não deve ocorrer; há teste).

### 2.2 CTAB + salicilato de sódio — vermiforme (demonstração representativa)

- Ponto:
  - CTAB `CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]`, 1 mmol em 100 mL (10 mM);
  - salicilato de sódio `O=C([O-])c1ccccc1O.[Na+]`, 5 mmol (50 mM; razão sal/CTAB = 5);
  - água, 293,15 K;
  - força iônica 0,06 mol/L, **derivada** de ½Σcz² com dissociação completa e rotulada assim.
- Condições:

  | Parâmetro | Valor | Natureza | Fonte ou justificativa |
  |---|---|---|---|
  | CTAB | 2,5–15 mM | experimental | Lam et al. (ORNL), [arXiv:1812.07138](https://arxiv.org/abs/1812.07138) |
  | razão NaSal/CTAB | 2,5–10 | experimental | mesmo estudo: vermiformes nessa razão em todas as concentrações de CTAB estudadas |
  | temperatura | 20,0 °C (único valor medido) | experimental | mesmo estudo |
  | tolerância de temperatura na entrada | ± 0,5 K em torno de 20,0 °C | technical | só arredondamento do campo; o estudo não mediu outras temperaturas |
  | solvente | água | experimental | mesmo estudo, amostras em D₂O; nota na tela |

- Medida citada: raio da seção transversal ≈ 22 Å.
- CMC do CTAB em água: 0,9 mM a 25 °C, citada no mesmo artigo.
- Regra representativa de orientação: o salicilato fica na interface do cilindro, com o anel aromático para dentro e o carboxilato para o meio. Base: estudos de RMN citados por Lam et al. (Olsson, Söderman & Guéring, J. Phys. Chem. 1986; Rao, Manohar et al., J. Phys. Chem. 1987).

### 2.3 DPPC — recorte de bicamada de uma estrutura lamelar (demonstração por protocolo)

- Ponto:
  - DPPC `CCCCCCCCCCCCCCCC(=O)OCC(COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC`, com duas cadeias palmitoíla de 16 carbonos cada (`tail_chain_count = 2`, `tail_carbon_count = 16`);
  - água, 328,15 K (55 °C);
  - quantidade **ilustrativa** de 1 mmol em 100 mL: o protocolo não fixa uma concentração única, e o rótulo diz isso.
- O que a cena mostra: **um recorte representativo de uma lamela**. A hidratação de DPPC acima de Tm não produz uma bicamada plana isolada; produz uma dispersão multilamelar (lamelas concêntricas). O título e a nota da tela dizem isso.
- Condições:

  | Parâmetro | Valor | Natureza | Fonte ou justificativa |
  |---|---|---|---|
  | temperatura | > 41 °C (Tm) | experimental | transição principal do DPPC ([PMC3508262](https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/)) |
  | método | hidratação de filme seco, sem extrusão | protocol | Bangham, Standish & Watkins, J. Mol. Biol. 13:238–252 (1965) |
  | solvente | água | protocol | mesmo protocolo |
  | limite superior de temperatura | < 100 °C | technical | água líquida a 1 atm; não há limite superior experimental documentado aqui |

- Sem CMC: a tela mostra "CMC: não usada neste exemplo (base: Tm e protocolo)".

### 2.4 DPPC — vesícula por extrusão (demonstração por protocolo)

- Ponto: mesma molécula com duas caudas, mesma quantidade ilustrativa, 328,15 K.
- Condições:

  | Parâmetro | Valor | Natureza | Fonte ou justificativa |
  |---|---|---|---|
  | método | extrusão repetida por filtro de policarbonato de 100 nm | experimental | Hope, Bally, Webb & Cullis, BBA 812:55–65 (1985): vesículas unilamelares de 60–100 nm ([PubMed](https://pubmed.ncbi.nlm.nih.gov/23008845/)) |
  | temperatura de extrusão | 51–61 °C (10–20 °C acima de Tm) | protocol | prática descrita em [PMC3508262](https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/) |
  | solvente | água | protocol | mesmo protocolo |

- Sem CMC, como em 2.3.

### 2.5 AOT em isooctano — micela inversa (parâmetro principal w0)

- Ponto, que também é a única condição aceita:
  - AOT `CCCCC(CC)COC(=O)CC(C(=O)OCC(CC)CCCC)S(=O)(=O)[O-].[Na+]`, 10 mmol em 100 mL (0,1 M), com `is_surfactant = true`, `tail_chain_count = 2` e `tail_carbon_count = 8` (duas cadeias 2‑etil‑hexila de 8 carbonos);
  - **w0 = 10**;
  - água derivada: n(água) = w0 × n(AOT) = 100 mmol;
  - solvente: isooctano `CC(C)CC(C)(C)C`;
  - 298,15 K;
  - constante dielétrica 1,94 ([tabela Stenutz](https://www.stenutz.eu/chem/solv23.php?s=3&p=1), fonte secundária; usada só no perfil visual do meio).
- **Por que um ponto e não uma faixa:** a literatura mostra mudanças estruturais na região de w0 de 10 a 20, e escolhemos o ponto mais documentado.
  - Forma esférica até w0 ≤ 20 com 100 mM de AOT, por DLS (Bohidar & Behboudnia, Colloids Surf. A, 2001).
  - Forma elipsoidal sugerida para w0 < 10, com razão entre eixos de 1,24 a 1,41 em simulação ([Abel et al., J. Phys. Chem. B 2004](https://pubs.acs.org/doi/10.1021/jp047138e)).
  - Alongamento com mais água, por SAXS.
  - Em w0 = 10, água de núcleo e água interfacial com dinâmicas distintas; a água do núcleo ainda não se comporta como água comum ([Fayer, PMC2721765](https://pmc.ncbi.nlm.nih.gov/articles/PMC2721765)).
  - Raio do núcleo ≈ 0,186·w0 nm a 298 K com 0,1 M de AOT ([estudo de pósitrons, J. Phys. Chem. 1996](https://baes.uc.pt/bitstream/10316/10313/1/Four-Component%20Analysis%20and%20Modeling%20of%20Positron%20Annihilation.pdf)), ou seja, ≈ 1,9 nm em w0 = 10.
- Condições:

  | Parâmetro | Valor | Natureza | Fonte ou justificativa |
  |---|---|---|---|
  | w0 | 10 | experimental | estudos acima |
  | tolerância de w0 na entrada | ± 0,5 | technical | só arredondamento do campo |
  | AOT | 0,1 M | experimental | estudo de pósitrons e DLS acima |
  | tolerância de AOT na entrada | ± 1 % | technical | só arredondamento |
  | temperatura | 25 °C | experimental | estudo de pósitrons (298 K) |
  | tolerância de temperatura na entrada | ± 0,5 K | technical | só arredondamento |
  | solvente | isooctano | experimental | todos os estudos citados |

- Forma na tela: "micela inversa aproximadamente esférica (pode ser levemente elipsoidal)".
- O backend calcula w0 a partir das quantidades do pedido: w0 = n(água) / n(AOT).
- Fora do ponto, o aviso cita a evidência: abaixo de 10, forma elipsoidal e água predominantemente interfacial; acima de 20, gotas deformadas ou alongadas.
- CMC: "não se aplica (meio apolar)". Nenhum número é mostrado.
- A contagem visual de águas é sublinear, como para qualquer componente, e não representa w0 numericamente; a nota diz isso.

## 3. Contrato da API

### 3.1 Pedido (`MiceliumSimulationRequest`)

- Campo novo opcional `documented_example_id: Literal[<5 ids>] | None = None`. Um id desconhecido gera 422 pela validação.
- Campo novo opcional em `MiceliumMoleculeInput`: `tail_chain_count: int | None = Field(None, ge=1, le=2)`. Sem ele, o modelo de uma cadeia atual não muda. Só o catálogo preenche o valor 2.
- A água do exemplo AOT continua sendo um item comum da mistura (papel `reagent`). Nada na lógica geral da mistura muda. O backend identifica a água do núcleo pelo exemplo (SMILES `O` com `role = "reagent"` num pedido com `documented_example_id = aot_inversa_isooctano`).

### 3.2 Resposta (`analysis`)

- `morphology_source: "calculated" | "documented_example"`, sempre presente.
- `documented_example: {id, title, kind, example_version, last_reviewed_at, documented_morphology, within_range, out_of_range_reasons, conditions, protocol, references, notes, w0}`, ou `null` sem id. `conditions` traz cada condição com a sua natureza; `w0` é preenchido só no AOT.
- Nas demonstrações dentro das condições:
  - `predicted_morphology` = forma documentada;
  - `predicted_regime` = "demonstração representativa (protocolo documentado)";
  - `morphology_basis` cita o exemplo e a referência.
- Fora das condições: `morphology_source = "calculated"`, com o aviso "fora das condições documentadas: <motivos>" em `warnings`.
- `measured_morphology` e os demais campos observados continuam vindo das coordenadas, sem mudança.

### 3.3 Catálogo para o painel

`GET /api/v1/micelium/documented-examples` devolve os 5 exemplos: componentes com fórmula e massa molar calculadas por RDKit, ambiente, condições com a natureza de cada uma, protocolo, referências, versão e tipo. É uma rota só de leitura, ativa em produção e sem acesso ao banco.

## 4. Motor (mudanças mínimas, todas opcionais ou protegidas pelo id do exemplo)

1. **Plano de formação:** depois de `choose_formation_plan`, se houver id e as condições forem atendidas:
   - nas demonstrações, a morfologia do plano passa a ser a documentada;
   - a fase e as frações visuais usam os valores que o motor já aplica a "micelização estabelecida", rotulados como visuais;
   - no SDS, o plano calculado não é alterado.
2. **AOT, núcleo aquoso:** as moléculas de água do exemplo recebem alvos dentro da camada de cabeças de cada micela inversa. O isooctano continua como meio contínuo.
3. **CTAB + salicilato, salicilato interfacial:** só neste exemplo, o salicilato é representado por duas contas:
   - anel, apolar (índice 0);
   - carboxilato, polar e com carga −1 (índice 1).

   Os alvos ficam na superfície do cilindro, com o anel voltado ao eixo e o carboxilato para fora. O tipo das contas continua `solute`, para não entrar na contagem de surfactantes.
4. **Duas caudas (`tail_chain_count = 2`):** em `mapping.build_particle_template`, o surfactante coarse‑grained ganha uma segunda cadeia de contas `tail` paralela à primeira.
   - As duas cadeias ficam deslocadas lateralmente (eixo local y) e ligadas à mesma conta `head`.
   - Cada cadeia tem o número de contas que a regra atual já dá a partir de `tail_carbon_count`: 4 contas por cadeia no DPPC (16 C) e 2 no AOT (8 C).
   - A primeira cadeia mantém os ids atuais (`:tail:i`). A segunda usa `:tail2:i`.
   - O posicionamento usa as coordenadas locais do modelo (`target_for_group` e `local_to_oriented`), então a orientação cabeça/cauda vale para as duas cadeias sem mudar forças.
   - Sem o campo, nada muda.
5. **Perfil do isooctano:** o ramo apolar de `infer_solvent_profile` passa a reconhecer "isooctano", "isooctane" e "2,2,4‑trimetilpentano". É a única mudança fora do caminho do exemplo; ela tem teste próprio e não altera nenhum outro solvente.
6. **Desempenho:** sem novas forças nem passos. As duas caudas aumentam o número de contas por molécula (DPPC: de 5 para 9; AOT: de 3 para 5). O limite de 900 partículas continua valendo pelo mecanismo atual de escala visual. O tempo de cada exemplo é medido.

## 5. Frontend

- **Painel 2D→3D (`pages/2dto3d/transfer.tsx`):** seção "Exemplos documentados", com 5 cartões.
  - Cada cartão mostra título, selo do tipo ("Previsão validada" ou "Demonstração representativa"), ponto carregado e versão.
  - O botão "Carregar exemplo" substitui a mistura e o meio e grava `documentedExampleId` nos metadados da transferência.
  - Você pode editar os campos depois de carregar; o backend decide se o pedido ainda atende às condições.
- **w0 no AOT:** o cartão carregado mostra o campo w0. A quantidade de água é derivada (w0 × AOT) e aparece na linha da água como "derivada de w0". Ela é recalculada quando w0 ou a quantidade de AOT mudam. A lógica geral da mistura (adicionar, remover e editar itens) não muda.
- **Tela 3D (`pages/3dpage/3dpage.tsx`):** o pedido inclui `documented_example_id`. No card "Previsto":
  - linha "Origem da forma": "calculada" ou "exemplo documentado";
  - nas demonstrações: título, protocolo, referências e notas;
  - condições, cada uma com a sua natureza ("experimental", "protocolo" ou "limite técnico");
  - fora das condições: aviso com os motivos;
  - no AOT: w0 e o raio do núcleo da referência.

  O selo "Visualização representativa — não é simulação física" continua.
- **Consistência visual:** segue o fluxo ui‑consistency já usado no projeto: checklist da região, implementação e verificação por um agente separado.

## 6. Erros e casos-limite

- Id desconhecido: 422.
- Id de um exemplo com a mistura alterada para fora das condições: 200, cálculo normal e aviso com os motivos.
- Exemplo AOT sem água ou sem AOT: fora das condições, com o motivo "w0 indefinido".
- Exemplo com componente removido ou trocado (SMILES diferente do catálogo): fora das condições, com o motivo "componentes diferentes do exemplo".
- `tail_chain_count` fora de 1–2: 422.
- Limites de produção (`PUBLIC_MAX_*`) continuam valendo.

## 7. Documentação

- `documentacao/validacao/WEB_LITE_V1.md` ganha uma seção com:
  - os 5 exemplos, as condições com a natureza de cada uma, as referências e o resultado dos testes;
  - as capturas de tela;
  - a pendência científica do sal no SDS.
- `GUIA_MOLECULAS_TESTE_MORFOLOGIAS.md` (já existente, com DDAB e outros sem fonte) ganha no topo uma nota apontando para os exemplos documentados. Nada é apagado.

## 8. Testes

### 8.1 Backend (pytest)

- **Catálogo:**
  - 5 exemplos, cada um com versão, data de revisão, ao menos uma referência, protocolo e tipo; só o SDS é `validated_prediction`;
  - toda condição tem natureza (`experimental`, `protocol` ou `technical`) e fonte;
  - nenhuma condição de natureza `technical` usa texto de faixa experimental.
- **Rota do catálogo:** 200 com 5 itens, fórmula e massa molar.
- **Duas caudas:**
  - com `tail_chain_count = 2`, o modelo tem duas cadeias `tail` com o mesmo número de contas, ambas ligadas à cabeça;
  - sem o campo, o modelo de uma cadeia é idêntico ao atual (ids, posições e ligações).
- **Dentro das condições:** `predicted_morphology` e `morphology_source` esperados para cada exemplo.
- **Geometria por tendência:** no último quadro de um trecho com seed fixa, critérios tolerantes; sem coordenadas rígidas.
  - **Esfera:** em ≥ 70 % das moléculas agregadas, a cabeça fica mais longe do centro do agregado do que o centro da cauda.
  - **Cilindro:** o mesmo, em relação ao eixo principal do agregado. A razão entre o maior e o menor eixo principal fica acima da medida para a esfera do SDS.
  - **Salicilato:** em ≥ 70 % das moléculas, o anel fica mais perto do eixo do que o carboxilato.
  - **Bicamada:** cabeças concentradas em duas faixas paralelas, ao longo da normal do plano principal, com a mediana das caudas entre elas.
  - **Vesícula:** distância radial das cabeças com duas populações (interna e externa), com a mediana das caudas entre elas.
  - **Micela inversa:** em ≥ 70 % das moléculas, a cabeça fica mais perto do centro do que a cauda. A mediana radial das águas fica dentro da mediana radial das cabeças.
  - **Duas caudas na cena:** no DPPC e no AOT, em ≥ 70 % das moléculas as duas cadeias apontam para o mesmo lado da cabeça (produto escalar positivo entre os vetores cabeça→centro de cada cadeia).
- **Fora das condições:** um caso por exemplo (incluindo AOT com w0 = 20 e CTAB a 25 °C), com `morphology_source = "calculated"` e aviso com motivo.
- **Sem id:** a resposta de um pedido existente (SDS 3 mmol) é idêntica antes e depois da mudança, com a mesma seed.
- **Isooctano:** o perfil reconhece o meio como apolar; água, etanol e hexano não mudam.
- **Desempenho:** tempo de um trecho de cada exemplo medido e registrado, com limite de aceitação de 15 s por trecho no ambiente de teste.

### 8.2 Frontend (Vitest)

- Carregar um exemplo preenche componentes, quantidades e meio, e grava o id.
- No AOT, mudar w0 recalcula a água; mudar a quantidade de AOT também.
- O pedido montado para o 3D leva `documented_example_id`.
- Editar a mistura carregada mantém o id; remover o exemplo limpa o id.
- O card "Previsto" mostra a origem da forma, as condições com a natureza, as referências e o aviso de fora das condições (teste de rótulos, como os existentes).

### 8.3 Conferência visual

- Capturas de tela dos 5 exemplos no Google Chrome desta máquina, com a pilha de desenvolvimento rodando o código novo.
- As capturas são avaliadas por um agente separado, que não escreveu o código, contra a tabela da seção 1, as duas caudas e a orientação cabeça/cauda.
- Depois, o autor confere no navegador seguindo o roteiro do relatório.

## 9. Riscos

- **Captura do 3D em Chrome sem tela:** o WebGL pode não renderizar no modo headless. Nesse caso, uso o Chrome com janela e, se ainda falhar, registro isso e a conferência visual fica só com o autor.
- **Ajustes de alvo vs. forças atuais:** as forças podem desfazer a forma no último quadro. Nesse caso, o critério de tendência falha e o ajuste é revisto dentro do mesmo exemplo, sem tocar nas forças gerais.
- **Segunda cadeia vs. código que supõe uma cadeia:** funções que percorrem as contas de cauda pelo índice (dobramento de cadeia, centro da cauda, analisador) podem supor uma cadeia contínua. O plano começa por um levantamento desses pontos e por testes de regressão do modelo de uma cadeia.

## 10. Pendência científica registrada (não corrigida aqui)

O ajuste de sal do motor faz o SDS virar "micela cilíndrica" a partir de força iônica de 0,08 mol/L. A literatura situa a transição de esfera para bastão do SDS acima de cerca de 0,2–0,3 mol/L de NaCl; as fontes divergem e a transição é gradual ([Springer 2025](https://link.springer.com/article/10.1007/s10895-025-04227-9); [Missel et al.](https://link.springer.com/chapter/10.1007/978-1-4684-4061-4_45)). O exemplo do SDS fica limitado a força iônica ≤ 0,07 mol/L como **limite técnico**, e a pendência vai para o relatório.
