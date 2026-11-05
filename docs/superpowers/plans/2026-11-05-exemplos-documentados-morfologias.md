# Exemplos documentados de morfologias — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:executing-plans (execução inline, já usada no projeto) ou superpowers:subagent-driven-development para executar tarefa por tarefa. Os passos usam caixas de seleção (`- [ ]`).

**Objetivo:** mostrar 5 morfologias com 4 anfifílicos (SDS, CTAB + salicilato, DPPC ×2, AOT) a partir de um catálogo de exemplos documentados, reaproveitando o motor 3D atual.

**Arquitetura:**
- Um catálogo imutável no backend define os exemplos com componentes, condições (cada uma com a sua natureza), protocolo e referências.
- O pedido de simulação ganha um `documented_example_id` opcional. Dentro das condições, as demonstrações usam a forma documentada; fora delas, o cálculo normal com aviso. O SDS sempre usa o cálculo.
- No motor, a mudança se limita a: modelo com duas caudas opcional, plano de formação substituído para os exemplos e duas forças específicas de exemplo (água no núcleo do AOT, salicilato interfacial).
- O painel 2D→3D carrega os exemplos pela rota do catálogo, e a tela 3D mostra a origem da forma.

**Tecnologias:** FastAPI + Pydantic 2, RDKit, numpy (backend); React + TypeScript + Vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-11-05-exemplos-documentados-morfologias-design.md` (revisão 2). A spec manda: valores, referências e condições de cada exemplo estão na seção 2 dela e não são repetidos aqui.

## Restrições globais

- Não inventar CMC, CPP, parâmetros ou transições. Cada condição tem a natureza `experimental`, `protocol` ou `technical` (spec §2).
- Sem `documented_example_id`, a resposta do motor é idêntica à atual (teste de linha de base da Tarefa 1).
- Não excluir funcionalidades nem módulos. Não alterar cálculos científicos existentes (CMC, CPP, classificação).
- Desempenho: ≤ 900 partículas e ≤ 240 moléculas visuais por pedido. Nenhuma força nova fora dos exemplos. ≤ 15 s por trecho de cada exemplo no ambiente de teste.
- PostgreSQL intocado: nenhuma migração, e a rota do catálogo não acessa o banco.
- Sem push, deploy, reescrita de histórico ou merge sem autorização do autor. Commits locais no branch `web-lite-v1-exemplos`.
- Testes do backend: `bash scripts/testar_backend.sh <arquivos>`. Suíte completa: `bash scripts/testar_backend.sh`. Frontend: `bash scripts/testar_frontend.sh` (Vitest + build).
- Textos da interface em português; nenhuma `@menção` em commits.
- Mensagens de commit terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Foco da revisão

1. **Chave de sessão entre exemplos:** a bicamada e a vesícula de DPPC têm a mesma composição e a mesma temperatura (55 °C). Sem o id na chave de sessão, a vesícula continuaria do último quadro da bicamada. Esperado: chaves diferentes. Teste na Tarefa 4.
2. **SMILES reescrito pelo editor:** o editor ou o painel podem gravar outro SMILES equivalente, por exemplo o salicilato em outra ordem. Esperado: os componentes são comparados por SMILES canônico do RDKit, e não por texto. Teste na Tarefa 3.
3. **Limites de produção:** cada exemplo, enviado com o tamanho que a tela usa (900 partículas e passos da tela), passa pelos limites `PUBLIC_MAX_*` em produção, com resposta 200. Teste na Tarefa 6.
4. **Duas caudas e o limite de partículas:** com 9 contas por DPPC, a escala visual não pode cortar uma molécula no meio nem passar de 900. Teste na Tarefa 2.
5. **Fora das condições com meio apolar:** AOT com w0 = 20 em isooctano cai no cálculo normal (sem CMC, "monômeros/pré-agregados"), com aviso e sem erro 500; a água continua comum (sem papel de núcleo). Teste na Tarefa 4.

---

### Tarefa 1: Linha de base do motor (proteção de regressão)

**Arquivos:**
- Criar: `backend/tests/exemplos_helpers.py`
- Criar: `backend/tests/fixtures/micelium_baseline_sds.json`
- Criar: `backend/tests/test_exemplos_baseline.py`

**Interfaces:**
- Produz:
  - `screen_request(components: list[dict], environment: dict, documented_example_id: str | None = None) -> dict`: monta o pedido exatamente como `buildMiceliumRequest` + `getVisualRenderCountFromAmount` do frontend fazem hoje:
    - contagem visual do reagente: `round(8 + √mmol·36)`, limitada a 5000;
    - contagem do solvente: `round(110 + √volume·13 + 8)`, limitada a 80–360;
    - escala para 240 moléculas visuais;
    - passos de 120, 160 ou 220 conforme o total visual (> 220, > 120 ou o restante);
    - `max_particles` 900, `dt` 0,016 e seed 13;
    - `real_concentration_mmol_l = mmol / (volume/1000)`.

    É usada por todos os testes de exemplos;
  - `baseline_signature(response_json: dict) -> dict`: os ids, os tipos e as posições das partículas arredondadas a 6 casas, o último quadro e os campos de `analysis`, sem `notes`. Usada nas Tarefas 2–5 para provar que um pedido sem id não muda.

- [ ] **Passo 1: gerar a linha de base com o código atual, antes de qualquer mudança.** Use `screen_request` com SDS 3 mmol e água em 100 mL a 298,15 K, com `_MICELIUM_SESSION_STATE.clear()` antes. Grave a assinatura em `fixtures/micelium_baseline_sds.json` por um script de uma só execução, sem deixar o script no repositório.
- [ ] **Passo 2: escrever `test_resposta_sem_exemplo_identica_a_linha_de_base`**, que monta o mesmo pedido e verifica `baseline_signature(resp) == json.load(fixture)`.
- [ ] **Passo 3: rodar.** `bash scripts/testar_backend.sh tests/test_exemplos_baseline.py`. Esperado: PASS. Este é um teste de caracterização: deve passar já agora.
- [ ] **Passo 4: commit.** `test: linha de base do motor para pedidos sem exemplo documentado`.

### Tarefa 2: Duas caudas opcionais no modelo coarse-grained

**Arquivos:**
- Modificar: `backend/app/modules/micelium/schemas.py`:
  - `MiceliumMoleculeInput` ganha `tail_chain_count: int | None = Field(None, ge=1, le=2)`;
  - `MiceliumParticle` ganha `chain_index: int = 0`.
- Modificar: `backend/app/modules/micelium/mapping.py` (`build_particle_template`).
- Modificar: `backend/app/modules/micelium/organization.py` (`apply_chain_bending_forces` e `apply_finite_cluster_forces`).
- Modificar: `backend/app/modules/micelium/engine.py` (`apply_molecule_flexibility`).
- Teste: `backend/tests/test_exemplos_duas_caudas.py`.

**Interfaces:**
- Produz:
  - `organization.tail_chains(indices: list[int], particles: list[MiceliumParticle]) -> list[list[int]]`: cadeias de cauda agrupadas por `chain_index`, cada uma ordenada da ponta para a cabeça (`bead_index` crescente);
  - **numeração da segunda cadeia:** com n contas por cadeia, a primeira cadeia usa `bead_index` 0..n−1 (ponta = 0), a cabeça n, e a segunda cadeia n+1..2n, com a ponta em n+1 e `chain_index = 1`;
  - ids no modelo: `:tail:i` e `:tail2:j`; nas cópias, `{molécula}:tail:{bead_index}`, que continuam únicos;
  - posição local da segunda cadeia: o mesmo x da conta correspondente da primeira, deslocada em y. As duas cadeias ficam em y = ±0,28; com uma cadeia, y continua 0.
- Consome: nada de tarefas anteriores além da linha de base.

- [ ] **Passo 1: escrever os testes que devem falhar.**
  - `test_modelo_duas_caudas_tem_duas_cadeias_ligadas_a_cabeca`: DPPC (spec §2.3) com `is_surfactant=True`, `tail_carbon_count=16` e `tail_chain_count=2` dá 4 + 4 contas `tail`, 1 `head`, `chain_index` {0, 1}, e uma ligação da conta mais próxima da cabeça de cada cadeia até a cabeça.
  - `test_modelo_uma_cadeia_inalterado`: sem o campo, o modelo do SDS é idêntico ao atual (ids, posições, ligações, `chain_index == 0`).
  - `test_tail_chains_ordena_ponta_para_cabeca`.
  - `test_duas_caudas_apontam_para_o_mesmo_lado`: cena com DPPC (`tail_chain_count=2`, `cmc_mmol_l=0.001` e `packing_parameter=0.7`, valores de teste explícitos e não do catálogo) acima da CMC. No último quadro, em ≥ 70 % das moléculas o produto escalar entre (centro da cadeia 0 − cabeça) e (centro da cadeia 1 − cabeça) é positivo.
  - `test_duas_caudas_respeitam_900_particulas`: pedido no formato da tela com 1 mmol de DPPC e água. Total ≤ 900, e cada molécula tem exatamente 9 contas.
  - `test_tail_chain_count_fora_de_1_a_2_da_422`: os valores 0 e 3 são rejeitados pela validação.
- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_exemplos_duas_caudas.py`. Esperado: FAIL (campo inexistente).
- [ ] **Passo 3: implementar o modelo de duas cadeias em `mapping.build_particle_template`**, só quando `tail_chain_count == 2`.
- [ ] **Passo 4: trocar o percurso por índice das caudas por `tail_chains`**:
  - em `apply_chain_bending_forces`: uma cadeia + cabeça por vez;
  - em `apply_finite_cluster_forces`: `radii` e `contour` calculados por posição dentro da cadeia; `tails[0]` continua sendo a ponta da cadeia 0;
  - em `apply_molecule_flexibility`: alavanca pela posição dentro da cadeia.

  Com uma cadeia, os cálculos ficam numericamente idênticos.
- [ ] **Passo 5: rodar os testes da tarefa e a linha de base.** `bash scripts/testar_backend.sh tests/test_exemplos_duas_caudas.py tests/test_exemplos_baseline.py`. Esperado: PASS.
- [ ] **Passo 6: rodar a suíte do backend completa.** Esperado: tudo verde.
- [ ] **Passo 7: commit.** `feat(micelium): modelo opcional com duas caudas por molécula`.

### Tarefa 3: Catálogo de exemplos e rota de leitura

**Arquivos:**
- Criar: `backend/app/modules/micelium/documented_examples.py`
- Modificar: `backend/app/modules/micelium/routes.py` (nova rota GET)
- Modificar: `backend/app/modules/micelium/schemas.py` (modelos de saída do catálogo)
- Teste: `backend/tests/test_exemplos_catalogo.py`

**Interfaces:**
- Produz:
  - `DocumentedExampleId = Literal["sds_esferica", "ctab_nasal_vermiforme", "dppc_bicamada_hidratacao", "dppc_vesicula_extrusao", "aot_inversa_isooctano"]`;
  - dataclasses `frozen`:
    - `Reference(label: str, url: str | None)`;
    - `Condition(parameter: str, label: str, basis: Literal["experimental","protocol","technical"], source: str, minimum: float | None = None, maximum: float | None = None, allowed: tuple[str, ...] | None = None)`. Uma linha sem limites é só informativa;
    - `ExampleComponent(key: str, name: str, smiles: str, role: Literal["reagent","solvent"], amount_mmol: float | None, is_surfactant: bool | None = None, tail_carbon_count: int | None = None, tail_chain_count: int | None = None, example_role: Literal["core_water","interfacial_aromatic_anion"] | None = None, derived_from_w0: bool = False)`;
    - `DocumentedExample(id, title, kind: Literal["validated_prediction","representative_demo"], example_version: str, last_reviewed_at: str, documented_morphology: str, components: tuple[ExampleComponent, ...], environment: dict[str, float | str], conditions: tuple[Condition, ...], protocol: str, references: tuple[Reference, ...], notes: tuple[str, ...], w0: float | None = None)`;
    - `ExampleVerdict(within_range: bool, reasons: tuple[str, ...], w0: float | None)`;
  - `EXAMPLES: dict[str, DocumentedExample]`, com os 5 exemplos exatamente como na spec §2;
  - `canonical_smiles(smiles: str) -> str | None` (RDKit);
  - `example_context(example, request, c_over_cmc: float | None) -> dict[str, float | str | None]`, com as chaves `temperature_c`, `ionic_strength`, `c_over_cmc`, `solvent`, `ctab_mm`, `nasal_ratio`, `aot_m`, `w0` e `method`. O método vem do próprio exemplo;
  - `evaluate(example, request, c_over_cmc) -> ExampleVerdict`, com os motivos "componentes diferentes do exemplo", "w0 indefinido" e "<label> fora de <faixa>";
  - `catalog_payload() -> list[dict]`, com fórmula e massa molar calculadas pelo RDKit;
  - rota `GET /api/v1/micelium/documented-examples` → `list[DocumentedExampleOut]`.
- Consome: `MiceliumSimulationRequest` (schemas existentes).

- [ ] **Passo 1: escrever os testes que devem falhar.**
  - `test_catalogo_tem_cinco_exemplos_versionados`: ids exatos; `example_version == "1.0.0"`; `last_reviewed_at == "2026-11-05"`; ao menos uma referência; só o SDS é `validated_prediction`.
  - `test_toda_condicao_tem_natureza_e_fonte`.
  - `test_limites_tecnicos_nao_se_apresentam_como_experimentais`: as condições de temperatura < 100 °C do DPPC, ± 0,5 K do CTAB, ± 0,5 de w0, ± 1 % de AOT, ± 0,5 K do AOT, força iônica ≤ 0,07 e 20–30 °C do SDS têm `basis == "technical"`.
  - `test_ponto_de_cada_exemplo_esta_dentro_das_condicoes`: um pedido montado a partir de `EXAMPLES[id]` dá `within_range is True`. No SDS, o c/CMC vem do motor.
  - `test_fora_das_condicoes_por_exemplo`, parametrizado:
    - SDS com força iônica 0,1;
    - CTAB com razão 1,0;
    - CTAB a 25 °C;
    - bicamada a 30 °C;
    - vesícula a 45 °C;
    - AOT com w0 = 20;
    - AOT em água.

    Cada caso dá `within_range is False`, e o motivo cita o parâmetro.
  - `test_componentes_trocados_saem_do_exemplo`: SDS no lugar do CTAB dá o motivo "componentes diferentes do exemplo".
  - `test_smiles_equivalente_e_aceito`: salicilato escrito `[Na+].[O-]C(=O)c1ccccc1O` continua dentro (Foco 2).
  - `test_w0_calculado_das_quantidades`: AOT 10 mmol + água 100 mmol dá `w0 == 10`; sem água, o motivo é "w0 indefinido".
  - `test_rota_catalogo_lista_cinco_com_formula`: GET devolve 200 e 5 itens com `formula` e `molar_mass` em cada componente. Funciona em produção, em `create_app(Settings(app_env="production"))`.
- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_exemplos_catalogo.py`. Esperado: FAIL (módulo inexistente).
- [ ] **Passo 3: implementar `documented_examples.py`** com os valores e referências da spec §2. Na tabela de condições, cada linha vira uma `Condition`; as tolerâncias técnicas são as linhas que levam limites.
- [ ] **Passo 4: implementar a rota GET em `routes.py` e os modelos de saída.**
- [ ] **Passo 5: rodar os testes da tarefa e a linha de base.** Esperado: PASS.
- [ ] **Passo 6: commit.** `feat(micelium): catálogo versionado dos cinco exemplos documentados`.

### Tarefa 4: Exemplo no pedido, plano de formação e resposta

**Arquivos:**
- Modificar: `backend/app/modules/micelium/schemas.py`:
  - `MiceliumSimulationRequest` ganha `documented_example_id: DocumentedExampleId | None = None`;
  - `MiceliumMoleculeInput` ganha `example_role: Literal["core_water","interfacial_aromatic_anion"] | None = None`;
  - `MiceliumParticle` ganha `example_role: str | None = None`;
  - `MiceliumAnalysis` ganha `morphology_source: Literal["calculated","documented_example"] = "calculated"` e `documented_example: DocumentedExampleReport | None = None`.
- Modificar: `backend/app/modules/micelium/engine.py`:
  - `FormationPlan` ganha `documented_example_id: str | None = None`;
  - extração pura de `_morphology_adjustments` a partir de `choose_formation_plan`;
  - `request_session_key` inclui o id do exemplo;
  - `MiceliumEngine.run`;
  - `infer_solvent_profile` reconhece o isooctano.
- Modificar: `backend/app/modules/micelium/documented_examples.py` (anotação do pedido e substituição do plano).
- Modificar: `backend/app/modules/micelium/mapping.py`: `example_role` é copiado para as partículas. Um soluto com `interfacial_aromatic_anion` vira duas contas `solute`: anel (índice 0, apolar, carga 0) e carboxilato (índice 1, polar, carga −1).
- Teste: `backend/tests/test_exemplos_motor.py`

**Interfaces:**
- Consome: `EXAMPLES`, `evaluate` e `canonical_smiles` (Tarefa 3); `tail_chain_count` (Tarefa 2).
- Produz:
  - `annotate_request(example, request, verdict) -> MiceliumSimulationRequest`:
    - grava `is_surfactant`, `tail_carbon_count` e `tail_chain_count` nos componentes por SMILES canônico, sempre que houver id;
    - grava `example_role` só com `verdict.within_range`;
  - `apply_documented_plan(plan: FormationPlan, example, verdict, surfactant_count: int) -> FormationPlan`:
    - só para `representative_demo` dentro das condições;
    - morfologia = `documented_morphology`;
    - `formation_phase = "demonstração representativa (protocolo documentado)"`;
    - `final_alpha` e `micellized_fraction` = os valores atuais de "micelização estabelecida" (0,72 e 0,62), passados por `_morphology_adjustments`;
    - `geometry_template = True`; `documented_example_id` preenchido;
    - `morphology_basis` cita o exemplo e a primeira referência;
  - `documented_example_report(example, verdict) -> DocumentedExampleReport`.
- **Ordem em `run`:**
  1. métricas;
  2. `evaluate`;
  3. `annotate_request`;
  4. métricas recalculadas;
  5. estado inicial;
  6. plano;
  7. `apply_documented_plan`;
  8. frames;
  9. análise.

  Depois da análise:
  - `morphology_source` vale `"documented_example"` só quando o plano foi substituído;
  - fora das condições, o aviso "fora das condições documentadas: …" vai para `warnings`;
  - no SDS dentro das condições com forma diferente da documentada, o aviso é "cálculo diverge da referência".

- [ ] **Passo 1: escrever os testes que devem falhar.**
  - `test_cada_exemplo_dentro_das_condicoes_tem_forma_e_origem`, parametrizado pelos 5 exemplos, com pedido no formato da tela:
    - `predicted_morphology` é a forma do catálogo;
    - `morphology_source` é `calculated` só no SDS;
    - `documented_example.within_range` é `True`.
  - `test_fora_das_condicoes_volta_ao_calculo_com_aviso`: os casos da Tarefa 3 pelo endpoint, com `morphology_source == "calculated"` e o aviso em `warnings`. Inclui o AOT com w0 = 20, que deve dar 200 e "monômeros/pré-agregados", sem `example_role` nas partículas (Foco 5).
  - `test_id_desconhecido_da_422`.
  - `test_chave_de_sessao_distingue_exemplos`: os pedidos de bicamada e de vesícula têm `request_session_key` diferentes (Foco 1).
  - `test_isooctano_e_meio_apolar`: polaridade < 0,35 no perfil; água, etanol e hexano mantêm o perfil atual.
  - `test_salicilato_tem_duas_contas_no_exemplo`: dentro das condições há duas contas `solute`, com `example_role` e cargas 0 e −1. Sem id, o salicilato continua com uma conta.
  - `test_dppc_e_aot_com_duas_caudas_no_exemplo`.
  - A linha de base da Tarefa 1 continua passando.
- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_exemplos_motor.py`. Esperado: FAIL.
- [ ] **Passo 3: implementar** na ordem da interface acima. A extração de `_morphology_adjustments` não muda números (a linha de base prova).
- [ ] **Passo 4: rodar os testes da tarefa, a linha de base e o catálogo.** Esperado: PASS. Depois, a suíte do backend completa, toda verde.
- [ ] **Passo 5: commit.** `feat(micelium): exemplo documentado no pedido, plano e origem da forma`.

### Tarefa 5: Forças específicas dos exemplos (núcleo aquoso do AOT, salicilato interfacial)

**Arquivos:**
- Criar: `backend/app/modules/micelium/documented_example_forces.py`
- Modificar: `backend/app/modules/micelium/engine.py`: chamada em `build_dynamic_formation_frames`, logo depois de `apply_finite_cluster_forces`, só quando `plan.documented_example_id` está preenchido.
- Teste: `backend/tests/test_exemplos_forcas.py`

**Interfaces:**
- Consome: `example_role` nas partículas e `organization_axis` do cluster (já gravado por `apply_finite_cluster_forces`).
- Produz: `apply_documented_example_forces(*, positions, velocities, particles, clusters, plan) -> None`.
  - Para cada cluster com surfactantes:
    - **`core_water`:** cada molécula é puxada para dentro do raio mediano das cabeças, medido a partir do centro do cluster. A água mais próxima é a do cluster;
    - **`interfacial_aromatic_anion`:** o anel é puxado para a distância radial mediana das cabeças menos 0,46 do eixo do cluster, e o carboxilato para essa distância mais 0,46.
  - As forças são proporcionais a `plan.final_alpha`, com a mesma ordem de grandeza da força de organização atual (0,065 × `final_alpha`). Não há outro efeito.

- [ ] **Passo 1: escrever os testes que devem falhar.**
  - `test_agua_fica_dentro_da_camada_de_cabecas_no_aot`: no último quadro, a mediana radial das águas é menor que a mediana radial das cabeças, no maior cluster.
  - `test_anel_do_salicilato_mais_perto_do_eixo_que_o_carboxilato`: em ≥ 70 % dos salicilatos associados a um cluster.
  - `test_sem_exemplo_nenhuma_forca_extra`: a linha de base continua passando.
- [ ] **Passo 2: rodar.** Esperado: FAIL.
- [ ] **Passo 3: implementar o módulo e a chamada.**
- [ ] **Passo 4: rodar a tarefa e a linha de base.** Esperado: PASS. Depois, a suíte completa, toda verde.
- [ ] **Passo 5: commit.** `feat(micelium): água no núcleo do AOT e salicilato interfacial nos exemplos`.

### Tarefa 6: Aceitação geométrica por tendência e desempenho

**Arquivos:**
- Criar: `backend/tests/test_exemplos_geometria.py`, com os ajudantes de geometria no próprio arquivo, como funções do teste.

**Interfaces:**
- Consome: tudo das Tarefas 2–5, pelo endpoint, com pedidos no formato da tela (900 partículas, passos da tela, seed 13).
- Produz: os critérios da spec §8.1, no último quadro, usando o maior cluster e os eixos principais pelo SVD das posições.

- [ ] **Passo 1: escrever os testes.**
  - `test_esfera_sds_cabecas_para_fora`: ≥ 70 %.
  - `test_cilindro_ctab_cabecas_longe_do_eixo_e_alongado`: ≥ 70 %. A razão entre o maior e o menor eixo é maior que a da esfera do SDS no mesmo protocolo.
  - `test_bicamada_dppc_duas_faixas_de_cabecas`: as cabeças projetadas na normal formam dois grupos de sinais opostos em relação ao plano médio, cada um com ≥ 30 % das cabeças, e a mediana das caudas fica entre os dois.
  - `test_vesicula_dppc_duas_populacoes_radiais`: as distâncias radiais das cabeças se separam em duas populações (interna < externa, pela mediana de cada metade após ordenar), e a mediana radial das caudas fica entre elas.
  - `test_inversa_aot_cabecas_para_dentro_agua_no_centro`: ≥ 70 % das moléculas com a cabeça mais perto do centro que a cauda, e a água dentro (repete o critério da Tarefa 5, agora pelo endpoint).
  - `test_duas_caudas_mesmo_lado_dppc_e_aot`: ≥ 70 %.
  - `test_exemplos_passam_nos_limites_de_producao`: os 5 exemplos em `create_app(Settings(app_env="production"))` dão 200 (Foco 3).
  - `test_tempo_por_trecho`: registra o tempo de cada exemplo e exige ≤ 15 s.
- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_exemplos_geometria.py`. Esperado: PASS. Se um critério falhar, a correção fica dentro do exemplo (Tarefa 5 ou `apply_documented_plan`), sem mexer nas forças gerais. A decisão vai para o ledger.
- [ ] **Passo 3: commit.** `test(micelium): geometria por tendência e tempo dos cinco exemplos`.

### Tarefa 7: Lógica do frontend (catálogo, w0, id no pedido)

**Arquivos:**
- Criar: `frontend/src/pages/2dto3d/documentedExamples.ts`
- Criar: `frontend/src/pages/2dto3d/documentedExamples.test.ts`
- Modificar: `frontend/src/pages/3dpage/type/3dpage.types.ts`:
  - `MoleculeTransferMetadata.documentedExampleId?: string | null`;
  - `MiceliumSimulationRequest3D.documented_example_id?: string | null`;
  - `MiceliumAnalysis3D.morphology_source?` e `documented_example?`, espelhando a Tarefa 4.
- Modificar: `frontend/src/pages/3dpage/3dpage.tsx` (`buildMiceliumRequest`).
- Modificar: `frontend/src/pages/3dpage/3dpage.micelium.test.ts`.

**Interfaces:**
- Consome: a rota da Tarefa 3, pelo `API_BASE_URL` de `src/config/apiBaseUrl.ts`.
- Produz:
  - `type DocumentedExampleDto`, espelho de `DocumentedExampleOut`;
  - `fetchDocumentedExamples(signal?: AbortSignal): Promise<DocumentedExampleDto[]>`;
  - `exampleToMixture(example: DocumentedExampleDto): { items: ExampleMixtureItem[]; environment: Record<string, string>; state: LoadedExampleState }`. As chaves de `environment` são as de `StableEnvironmentSettings` (`temperatureK`, `ionicStrengthMolL`, `dielectricConstant`, `solventName`, `volumeMl` …);
  - `type ExampleMixtureItem = { key: string; name: string; smiles: string; formula: string; molarMass: string; role: "reagent" | "solvent"; amountMmol: number | null; derivedFromW0: boolean }`;
  - `type LoadedExampleState = { id: string; w0: number | null; aotKey: string | null; waterKey: string | null }`;
  - `deriveCoreWaterMmol(w0: number, aotMmol: number): number` (= w0 × aotMmol);
  - `buildMiceliumRequest` define `documented_example_id` quando todos os transfers trazem o mesmo `transferMetadata.documentedExampleId`; senão, `null`.

- [ ] **Passo 1: escrever os testes que devem falhar.**
  - `exampleToMixture` do AOT dá a água com `derivedFromW0` e `amountMmol` 100, e `state.w0` 10.
  - `deriveCoreWaterMmol(15, 10) === 150`.
  - O ambiente carregado da vesícula tem `temperatureK` "328.15".
  - `buildMiceliumRequest` com transfers marcados envia o id; com marcações diferentes ou ausentes, envia `null`.
  - `fetchDocumentedExamples` usa `${API_BASE_URL}/micelium/documented-examples` (fetch simulado no teste).
- [ ] **Passo 2: rodar.** `bash scripts/testar_frontend.sh`. Esperado: FAIL nos novos testes.
- [ ] **Passo 3: implementar.**
- [ ] **Passo 4: rodar.** Esperado: Vitest todo verde e build ok.
- [ ] **Passo 5: commit.** `feat(frontend): lógica dos exemplos documentados e id no pedido 3D`.

### Tarefa 8: Interface (painel 2D→3D e card "Previsto")

**Arquivos:**
- Modificar: `frontend/src/pages/2dto3d/transfer.tsx`:
  - seção "Exemplos documentados" com 5 cartões e "Carregar exemplo";
  - campo w0 no exemplo AOT carregado;
  - linha da água marcada "derivada de w0";
  - `documentedExampleId` em `buildStoredSolutionItems`.
- Modificar: `frontend/src/pages/2dto3d/transfer.css` (só classes novas).
- Modificar: `frontend/src/pages/3dpage/3dpage.tsx`: nova `buildDocumentedExampleRows(analysis)` e renderização no card "Previsto".
- Modificar: `frontend/src/pages/3dpage/3dpage.labels.test.ts`.

**Interfaces:**
- Consome: Tarefa 7.
- Produz: `buildDocumentedExampleRows(analysis: MiceliumAnalysis3D | null): { label: string; value: string }[]`, com as linhas:
  - "Origem da forma": "calculada" ou "exemplo documentado";
  - "Exemplo";
  - "Condições": uma linha por condição, "<label> — experimental | protocolo | limite técnico";
  - "Protocolo";
  - "Referências";
  - "Fora das condições documentadas", só quando `within_range` é falso;
  - "w0", só no AOT.

- [ ] **Passo 1: preparar a UI.** Rodar `ui-consistency:adjusting` para as duas regiões (seção do painel e linhas do card), gravando o checklist no workspace do plano.
- [ ] **Passo 2: escrever os testes de rótulos que devem falhar.**
  - Origem "exemplo documentado" na vesícula; "calculada" no SDS.
  - Uma condição técnica aparece como "limite técnico".
  - Fora das condições, a linha de aviso aparece.
  - w0 só no AOT.
- [ ] **Passo 3: rodar.** Esperado: FAIL.
- [ ] **Passo 4: implementar**, seguindo o checklist (`ui-consistency:implementing`). Editar a mistura carregada mantém o id; "Limpar" e trocar de exemplo apagam o id e o estado do w0. Mudar w0 ou o AOT recalcula a água por `deriveCoreWaterMmol`.
- [ ] **Passo 5: rodar.** `bash scripts/testar_frontend.sh`. Esperado: todo verde e build ok.
- [ ] **Passo 6: verificação de UI por um agente separado** (`ui-consistency:verifying`), com uma calibração plantada. No máximo duas rodadas de correção.
- [ ] **Passo 7: commit.** `feat(frontend): exemplos documentados no painel 2D→3D e origem da forma no 3D`.

### Tarefa 9: Conferência visual, documentação e suítes completas

**Arquivos:**
- Modificar: `documentacao/validacao/WEB_LITE_V1.md` (nova seção: exemplos, condições com natureza, referências, resultados, tempos e pendência do sal no SDS).
- Modificar: `backend/app/modules/micelium/GUIA_MOLECULAS_TESTE_MORFOLOGIAS.md` (nota no topo; nada apagado).
- Criar: `documentacao/validacao/exemplos_documentados/` com 5 capturas PNG.

- [ ] **Passo 1: avisar o autor e reiniciar a pilha.** Esta é uma ação manual: o autor precisa rodar `bash iniciar_linux.sh`, ou eu rodo com autorização. A pilha de desenvolvimento precisa subir com o código novo.
- [ ] **Passo 2: capturas.** Um script em `.runtime/capturas/`, fora do repositório, usa `puppeteer-core` instalado só nessa pasta, apontando para `/usr/bin/google-chrome`. Para cada exemplo:
  - abrir http://localhost:5173;
  - clicar em "Carregar exemplo" e enviar ao 3D pelo botão já existente do painel;
  - aguardar 3 trechos;
  - capturar a tela.

  Se o WebGL não renderizar sem janela, repetir com janela. Se ainda falhar, registrar o motivo e deixar a conferência visual para o autor (spec §9).
- [ ] **Passo 3: avaliação das capturas por um agente separado**, contra a spec §1 e §8.3: forma, duas caudas, orientação cabeça/cauda, água no centro do AOT, salicilato na interface e selos.
- [ ] **Passo 4: suítes completas.**
  - backend: `bash scripts/testar_backend.sh`;
  - frontend: `bash scripts/testar_frontend.sh`;
  - host: `python3 -m unittest backend/tests/test_no_secrets.py backend/tests/test_garantir_env.py backend/tests/test_producao_compose.py`.

  Esperado: tudo verde.
- [ ] **Passo 5: escrever a documentação**, com os números copiados das execuções.
- [ ] **Passo 6: commit.** `docs: exemplos documentados — resultados, capturas e pendência do SDS com sal`.

### Revisão final

Depois da Tarefa 9, um agente revisor separado, no modelo mais capaz, revisa o branch inteiro: pacote de revisão, spec, plano, este "Foco da revisão" e as linhas `Ruling:` do ledger. Os achados críticos e importantes são corrigidos em uma única rodada, cada um com teste RED→GREEN. Os menores vão para o ledger e para a mensagem final.
