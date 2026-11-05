# Exemplos documentados de morfologias — Especificação (complemento da Web Lite 1.0)

Data: 05/11/2026
Status: rascunho para revisão do autor (Partes 1 e 2 aprovadas no chat, com ajustes incorporados)
Base: branch `web-lite-v1` (commit `9d9d214`); trabalho no branch `web-lite-v1-exemplos`

## 1. Objetivo

Demonstrar **5 morfologias com 4 anfifílicos** no ambiente 3D existente. Cada exemplo tem condições tiradas de referências experimentais e uma origem da forma declarada sem ambiguidade:

| id | Morfologia | Anfifílico | Origem da forma |
|---|---|---|---|
| `sds_esferica` | micela esférica (aproximação) | SDS | **calculada** pelo motor atual (previsão validada) |
| `ctab_nasal_vermiforme` | micela cilíndrica/vermiforme | CTAB + salicilato de sódio | **exemplo documentado** (demonstração representativa) |
| `dppc_bicamada_hidratacao` | bicamada plana (multilamelar) | DPPC | **exemplo documentado** (protocolo de preparo) |
| `dppc_vesicula_extrusao` | vesícula unilamelar | DPPC | **exemplo documentado** (protocolo de preparo) |
| `aot_inversa_isooctano` | micela inversa com núcleo aquoso | AOT | **exemplo documentado** (parâmetro principal w0) |

### Critérios de sucesso

1. Cada exemplo, carregado pelo painel 2D→3D e dentro da sua faixa documentada, termina a visualização na morfologia da tabela acima, com cabeças polares e caudas apolares na orientação correta (testes de tendência, seção 8).
2. A resposta diz explicitamente de onde veio a forma: `morphology_source = "calculated"` ou `"documented_example"`.
3. Fora da faixa documentada, o motor volta ao cálculo normal e avisa: "fora das condições documentadas", com o motivo.
4. Nenhuma CMC, CPP, parâmetro ou transição inventados. Quantidades sem fonte são rotuladas como ilustrativas.
5. Sem `documented_example_id`, o comportamento atual não muda: a suíte existente inteira continua verde.
6. Desempenho dentro dos limites atuais da tela 3D (≤ 900 partículas, ≤ 240 moléculas visuais por pedido).

### Fora do escopo

- Outras morfologias, outros anfifílicos e transições entre formas.
- Qualquer motor universal de previsão de forma, novas famílias de CMC ou novo cálculo de CPP.
- Correção do ajuste de sal do SDS (seção 10, pendência registrada).
- Representar as duas caudas do DPPC e do AOT como cadeias separadas: os dois continuam com uma cadeia coarse‑grained, o que é declarado como limitação na nota do exemplo.
- Reconhecer automaticamente essas moléculas quando desenhadas à mão no editor.

## 2. Catálogo

Arquivo novo: `backend/app/modules/micelium/documented_examples.py`, com dados imutáveis (dataclasses `frozen`). Cada exemplo tem:

- `id`, `title`, `example_version` (`"1.0.0"`) e `last_reviewed_at` (`"2026-11-05"`);
- `kind`: `"validated_prediction"` (só o SDS) ou `"representative_demo"`;
- `documented_morphology`: rótulo no vocabulário do motor (`"micela esférica"`, `"micela cilíndrica/wormlike"`, `"bicamada plana/lamelar"`, `"vesícula/bicamada fechada"`, `"micela inversa"`);
- `components`: SMILES, nome, papel, quantidade em mmol e, quando necessário, campos já existentes do pedido (`is_surfactant`, `tail_carbon_count`) com valor factual;
- `environment`: volume, temperatura, solvente e força iônica;
- `range`: as condições documentadas, conferidas pela função `evaluate(example, request) -> ExampleVerdict(within_range, reasons)`;
- `protocol`: texto curto do preparo e das condições;
- `references`: lista com autores, ano, revista e DOI ou URL;
- `notes`: limitações declaradas.

### 2.1 SDS — micela esférica (previsão validada)

- Ponto: SDS `CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]`, 3 mmol em 100 mL (30 mM), água, 298,15 K, força iônica 0,01 mol/L.
- Faixa:
  - força iônica ≤ 0,07 mol/L;
  - c/CMC > 1;
  - condições dentro do domínio atual da correlação de CMC (água, 20–30 °C).
- Forma: vem do cálculo existente. A CMC experimental de 8,16 mM já está no projeto (NSRDS‑NBS 36).
- Nota: os estudos de SANS descrevem a micela de SDS em água sem sal como elipsoide levemente achatado; a tela mostra "esférica (aproximação)".
- Referências: Mukerjee & Mysels, NSRDS‑NBS 36 (1971); SANS sem sal ([PMC4487321](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4487321/)).
- Se o cálculo devolver outra forma dentro da faixa, a resposta traz o aviso "cálculo diverge da referência" (não deve ocorrer; há teste).

### 2.2 CTAB + salicilato de sódio — vermiforme (demonstração representativa)

- Ponto:
  - CTAB `CCCCCCCCCCCCCCCC[N+](C)(C)C.[Br-]`, 1 mmol em 100 mL (10 mM);
  - salicilato de sódio `O=C([O-])c1ccccc1O.[Na+]`, 5 mmol (50 mM; razão sal/CTAB = 5);
  - água, 293,15 K;
  - força iônica derivada de ½Σcz² com dissociação completa: 0,06 mol/L. O valor é marcado como derivado.
- Faixa: CTAB de 2,5 a 15 mM; razão NaSal/CTAB de 2,5 a 10; 293,15 ± 0,1 K; solvente água.
- Fonte: Lam, Hong, Do & Chen, "Evolution of CTAB/NaSal Micelles: Structural Analysis by SANS", ORNL ([arXiv:1812.07138](https://arxiv.org/abs/1812.07138)). O estudo encontrou micelas vermiformes para razão ≥ 2,5 em CTAB de 2,5 a 15 mM a 20,0 °C, com raio da seção transversal ≈ 22 Å.
- Notas:
  - as amostras do estudo foram feitas em D₂O;
  - CMC do CTAB em água: 0,9 mM a 25 °C, citada no mesmo artigo.
- Regra representativa de orientação: o salicilato fica na interface do cilindro, com o anel aromático para dentro e o carboxilato para o meio. Base: estudos de RMN citados por Lam et al. (Olsson, Söderman & Guéring, J. Phys. Chem. 1986; Rao, Manohar et al., J. Phys. Chem. 1987).

### 2.3 DPPC — bicamada plana por hidratação (demonstração por protocolo)

- Ponto:
  - DPPC `CCCCCCCCCCCCCCCC(=O)OCC(COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC`, água, 328,15 K (55 °C);
  - quantidade **ilustrativa** de 1 mmol em 100 mL: o protocolo não fixa uma concentração única, e o rótulo diz isso.
- Faixa: T > 314,15 K (Tm = 41 °C) e T < 373,15 K (limite físico da água líquida a 1 atm, rotulado como tal); solvente água; método: hidratação sem extrusão.
- Base: hidratação de filme lipídico seco acima de Tm forma dispersões multilamelares (Bangham, Standish & Watkins, J. Mol. Biol. 13:238–252, 1965). Tm de 41 °C ([PMC3508262](https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/)).
- Sem CMC: a tela mostra "CMC: não usada neste exemplo (base: Tm e protocolo)".
- A cena mostra um trecho plano de bicamada; a nota diz que a amostra real é multilamelar.

### 2.4 DPPC — vesícula por extrusão (demonstração por protocolo)

- Ponto: mesma dispersão e mesma quantidade ilustrativa; 328,15 K.
- Faixa: 324,15 ≤ T ≤ 334,15 K (51–61 °C; a extrusão é feita 10–20 °C acima de Tm); solvente água; método: extrusão por membrana de 100 nm.
- Base: Hope, Bally, Webb & Cullis, Biochim. Biophys. Acta 812:55–65 (1985). Extrusão repetida por filtros de policarbonato de 100 nm gera vesículas unilamelares de 60–100 nm ([PubMed](https://pubmed.ncbi.nlm.nih.gov/23008845/)). Faixa de temperatura de extrusão: [PMC3508262](https://pmc.ncbi.nlm.nih.gov/articles/PMC3508262/).
- Sem CMC, como em 2.3.

### 2.5 AOT em isooctano — micela inversa (parâmetro principal w0)

- Ponto:
  - AOT `CCCCC(CC)COC(=O)CC(C(=O)OCC(CC)CCCC)S(=O)(=O)[O-].[Na+]`, 10 mmol em 100 mL (0,1 M), com `is_surfactant = true` e `tail_carbon_count = 8` (cadeia 2‑etil‑hexila, 8 carbonos);
  - **w0 = 10**;
  - água derivada: n(água) = w0 × n(AOT) = 100 mmol;
  - solvente: isooctano `CC(C)CC(C)(C)C`;
  - 298,15 K;
  - constante dielétrica 1,94 ([tabela Stenutz](https://www.stenutz.eu/chem/solv23.php?s=3&p=1), fonte secundária; usada só no perfil visual do meio).
- Faixa: AOT 0,1 M (± 1 %); 10 ≤ w0 ≤ 20; 294,15–298,15 K; solvente isooctano.
- Bases:
  - raio do núcleo aquoso r ≈ 0,186·w0 nm a 298 K, com 0,1 M de AOT e w0 de 10 a 40 (estudo de aniquilação de pósitrons, J. Phys. Chem. 1996, [repositório UC](https://baes.uc.pt/bitstream/10316/10313/1/Four-Component%20Analysis%20and%20Modeling%20of%20Positron%20Annihilation.pdf));
  - forma esférica até w0 ≤ 20 a 100 mM de AOT (Bohidar & Behboudnia, Colloids Surf. A, 2001).
- O backend calcula w0 a partir das quantidades do pedido: w0 = n(água) / n(AOT).
- CMC: "não se aplica (meio apolar)". Nenhum número é mostrado.
- Na cena, o raio do núcleo cresce na proporção de w0. A contagem visual de águas é sublinear, como para qualquer componente, e não representa w0 numericamente; a nota diz isso.

## 3. Contrato da API

### 3.1 Pedido (`MiceliumSimulationRequest`)

- Campo novo opcional `documented_example_id: Literal[<5 ids>] | None = None`. Um id desconhecido gera 422 pela validação.
- Componente com papel derivado no exemplo AOT: a água continua sendo um item comum da mistura (papel `reagent`). Nada na lógica geral da mistura muda. O backend identifica a água do núcleo pelo exemplo (SMILES `O` com `role = "reagent"` num pedido com `documented_example_id = aot_inversa_isooctano`).

### 3.2 Resposta (`analysis`)

- `morphology_source: "calculated" | "documented_example"`, sempre presente.
- `documented_example: {id, title, kind, example_version, last_reviewed_at, documented_morphology, within_range, out_of_range_reasons, protocol, references, notes, w0}`, ou `null` sem id. `w0` é preenchido só no AOT.
- Nas demonstrações dentro da faixa:
  - `predicted_morphology` = forma documentada;
  - `predicted_regime` = "demonstração representativa (protocolo documentado)";
  - `morphology_basis` cita o exemplo e a referência.
- Fora da faixa: `morphology_source = "calculated"`, com o aviso "fora das condições documentadas: <motivos>" em `warnings`.
- `measured_morphology` e os demais campos observados continuam vindo das coordenadas, sem mudança.

### 3.3 Catálogo para o painel

`GET /api/v1/micelium/documented-examples` devolve os 5 exemplos: componentes com fórmula e massa molar calculadas por RDKit, ambiente, faixa em texto, protocolo, referências, versão e tipo. É uma rota só de leitura, ativa em produção e sem acesso ao banco.

## 4. Motor (mudanças mínimas, todas protegidas pelo id do exemplo)

1. **Plano de formação:** depois de `choose_formation_plan`, se houver id e `within_range`:
   - nas demonstrações, a morfologia do plano passa a ser a documentada;
   - a fase e as frações visuais usam os valores que o motor já aplica a "micelização estabelecida", rotulados como visuais;
   - no SDS, o plano calculado não é alterado.
2. **AOT, núcleo aquoso:** as moléculas de água do exemplo recebem alvos dentro da camada de cabeças de cada micela inversa. O raio do núcleo na cena é proporcional a w0 (relação linear da seção 2.5). O isooctano continua como meio contínuo.
3. **CTAB + salicilato, salicilato interfacial:** só neste exemplo, o salicilato é representado por duas contas:
   - anel, apolar (índice 0);
   - carboxilato, polar e com carga −1 (índice 1).

   Os alvos ficam na superfície do cilindro, com o anel voltado ao eixo e o carboxilato para fora. O tipo das contas continua `solute`, para não entrar na contagem de surfactantes.
4. **Perfil do isooctano:** o ramo apolar de `infer_solvent_profile` passa a reconhecer "isooctano", "isooctane" e "2,2,4‑trimetilpentano". É a única mudança fora do caminho do exemplo; ela tem teste próprio e não altera nenhum outro solvente.
5. **Desempenho:** sem novas forças nem passos. Os ajustes só mudam os alvos iniciais e a representação de um soluto.

## 5. Frontend

- **Painel 2D→3D (`pages/2dto3d/transfer.tsx`):** seção "Exemplos documentados", com 5 cartões.
  - Cada cartão mostra título, selo do tipo ("Previsão validada" ou "Demonstração representativa"), ponto carregado e versão.
  - O botão "Carregar exemplo" substitui a mistura e o meio e grava `documentedExampleId` nos metadados da transferência.
  - Você pode editar os campos depois de carregar; o backend decide se o pedido ainda está na faixa.
- **w0 no AOT:** o cartão carregado mostra o campo w0. A quantidade de água é derivada (w0 × AOT) e aparece na linha da água como "derivada de w0". Ela é recalculada quando w0 ou a quantidade de AOT mudam. A lógica geral da mistura (adicionar, remover e editar itens) não muda.
- **Tela 3D (`pages/3dpage/3dpage.tsx`):** o pedido inclui `documented_example_id`. No card "Previsto":
  - linha "Origem da forma": "calculada" ou "exemplo documentado";
  - nas demonstrações: título, protocolo, referências e notas;
  - fora da faixa: aviso com os motivos;
  - no AOT: w0 e o raio do núcleo da referência.

  O selo "Visualização representativa — não é simulação física" continua.
- **Consistência visual:** segue o fluxo ui‑consistency já usado no projeto: checklist da região, implementação e verificação por um agente separado.

## 6. Erros e casos-limite

- Id desconhecido: 422.
- Id de um exemplo com a mistura alterada para fora da faixa: 200, cálculo normal e aviso com os motivos.
- Exemplo AOT sem água ou sem AOT: fora da faixa, com o motivo "w0 indefinido".
- Exemplo com componente removido ou trocado (SMILES diferente do catálogo): fora da faixa, com o motivo "componentes diferentes do exemplo".
- Limites de produção (`PUBLIC_MAX_*`) continuam valendo.

## 7. Documentação

- `documentacao/validacao/WEB_LITE_V1.md` ganha uma seção com:
  - os 5 exemplos, as referências e o resultado dos testes;
  - as capturas de tela;
  - a pendência científica do sal no SDS.
- `GUIA_MOLECULAS_TESTE_MORFOLOGIAS.md` (já existente, com DDAB e outros sem fonte) ganha no topo uma nota apontando para os exemplos documentados. Nada é apagado.

## 8. Testes

### 8.1 Backend (pytest)

- **Catálogo:** 5 exemplos; cada um com versão, data de revisão, ao menos uma referência, protocolo e tipo; só o SDS é `validated_prediction`.
- **Rota do catálogo:** 200 com 5 itens, fórmula e massa molar.
- **Dentro da faixa:** `predicted_morphology` e `morphology_source` esperados para cada exemplo.
- **Geometria por tendência:** no último quadro de um trecho com seed fixa, critérios tolerantes; sem coordenadas rígidas.
  - **Esfera:** em ≥ 70 % das moléculas agregadas, a cabeça fica mais longe do centro do agregado do que o centro da cauda.
  - **Cilindro:** o mesmo, em relação ao eixo principal do agregado. A razão entre o maior e o menor eixo principal fica acima da medida para a esfera do SDS.
  - **Salicilato:** em ≥ 70 % das moléculas, o anel fica mais perto do eixo do que o carboxilato.
  - **Bicamada:** cabeças concentradas em duas faixas paralelas, ao longo da normal do plano principal, com a mediana das caudas entre elas.
  - **Vesícula:** distância radial das cabeças com duas populações (interna e externa), com a mediana das caudas entre elas.
  - **Micela inversa:** em ≥ 70 % das moléculas, a cabeça fica mais perto do centro do que a cauda. A mediana radial das águas fica dentro da mediana radial das cabeças.
  - **w0:** o raio mediano do núcleo aquoso com w0 = 20 é maior do que com w0 = 10.
- **Fora da faixa:** um caso por exemplo, com `morphology_source = "calculated"` e aviso com motivo.
- **Sem id:** a resposta de um pedido existente (SDS 3 mmol) é idêntica antes e depois da mudança, com a mesma seed.
- **Isooctano:** o perfil reconhece o meio como apolar; água, etanol e hexano não mudam.
- **Desempenho:** tempo de um trecho de cada exemplo medido e registrado, com limite de aceitação de 15 s por trecho no ambiente de teste.

### 8.2 Frontend (Vitest)

- Carregar um exemplo preenche componentes, quantidades e meio, e grava o id.
- No AOT, mudar w0 recalcula a água; mudar a quantidade de AOT também.
- O pedido montado para o 3D leva `documented_example_id`.
- Editar a mistura carregada mantém o id; remover o exemplo limpa o id.
- O card "Previsto" mostra a origem da forma, as referências e o aviso de fora da faixa (teste de rótulos, como os existentes).

### 8.3 Conferência visual

- Capturas de tela dos 5 exemplos no Google Chrome desta máquina, com a pilha de desenvolvimento rodando o código novo.
- As capturas são avaliadas por um agente separado, que não escreveu o código, contra a tabela da seção 1 e a orientação cabeça/cauda.
- Depois, o autor confere no navegador seguindo o roteiro do relatório.

## 9. Riscos

- **Captura do 3D em Chrome sem tela:** o WebGL pode não renderizar no modo headless. Nesse caso, uso o Chrome com janela e, se ainda falhar, registro isso e a conferência visual fica só com o autor.
- **Ajustes de alvo vs. forças atuais:** as forças podem desfazer a forma no último quadro. Nesse caso, o critério de tendência falha e o ajuste é revisto dentro do mesmo exemplo, sem tocar nas forças gerais.

## 10. Pendência científica registrada (não corrigida aqui)

O ajuste de sal do motor faz o SDS virar "micela cilíndrica" a partir de força iônica de 0,08 mol/L. A literatura situa a transição de esfera para bastão do SDS acima de cerca de 0,2–0,3 mol/L de NaCl; as fontes divergem e a transição é gradual ([Springer 2025](https://link.springer.com/article/10.1007/s10895-025-04227-9); [Missel et al.](https://link.springer.com/chapter/10.1007/978-1-4684-4061-4_45)). O exemplo do SDS fica limitado a força iônica ≤ 0,07 mol/L, e a pendência vai para o relatório.
