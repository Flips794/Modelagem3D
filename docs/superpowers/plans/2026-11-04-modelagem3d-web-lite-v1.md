# Modelagem3D Web Lite v1 — Plano de implementação

> **Para agentes executores:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa por tarefa. Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** estabilizar e completar os cálculos leves (RDKit), identificar as cinco classes de surfactante por regras e pH, fazer a visualização 3D convergir para o que os cálculos preveem e preparar a publicação web.

**Arquitetura:** pacote aditivo `backend/app/modules/chemistry/properties/` com provedores pequenos. A saída deles é mesclada no `make_response` existente e só preenche campos hoje indisponíveis. As regras de classe ficam no núcleo compartilhado `validated_calculations.py`, usado pelo painel, pela IA e pelo motor 3D. O motor Micelium e o frontend recebem só ajustes pontuais. A hospedagem é feita por variáveis de ambiente, mais um `docker-compose.prod.yml` com Caddy.

**Tecnologias:** Python 3.12, FastAPI, RDKit 2026.09, Pydantic 2, pytest; React 19, TypeScript, Vite 8, Vitest, Three.js; PostgreSQL 16; Docker Compose; Caddy 2.

**Spec:** `docs/superpowers/specs/2026-11-04-modelagem3d-web-lite-v1-design.md`, que deve ser lida junto com este plano.

## Restrições globais

- Não excluir funcionalidades, módulos nem arquivos. `calculation_page.py`, `miriam21_engine.py`, `*_example.py`, `simulation/openmm_*` e os módulos de IA permanecem.
- Não alterar a arquitetura sem necessidade. Nada de refatoração fora do que a tarefa pede.
- Preservar o PostgreSQL, o volume `modelagem3d_pgdata` e as migrações Alembic. Nenhuma migração nova nesta etapa.
- Sem OpenMM, Martini, xTB, DFT, MOPAC ou Joback; sem treinamento de IA.
- Nunca inventar valores. Sem método válido, o campo fica `available: false` com `note` não vazia: `não se aplica: <motivo>` ou `indisponível: <motivo>`.
- Todo valor estimado leva `source`, `confidence` e `note`, com o método e o limite de validade.
- A CMC só é ampliada com correlação fundamentada em dados experimentais rastreáveis. Nunca se força uma CMC para fazer micelas aparecerem.
- O 3D é sempre rotulado: "Visualização representativa — não é simulação física".
- Os nomes dos 137 campos atuais do painel não mudam. Campos novos são adicionados.
- Metas de desempenho: p95 de `/chemistry/parameters/analyze` ≤ 300 ms (até 100 átomos pesados); `/micelium/simulate` com 2.500 partículas ≤ 10 s.
- Textos voltados ao usuário em português. Identificadores de código seguem o estilo do arquivo editado.
- Cada tarefa termina com a suíte completa passando: `bash scripts/testar_backend.sh` (e `bash scripts/testar_frontend.sh` quando a tarefa toca o frontend).
- Os testes existentes só podem ser alterados quando afirmam explicitamente o comportamento que a spec manda corrigir. Cada teste alterado é citado na mensagem do commit, com o motivo.
- O executor não reconstrói nem reinicia a pilha que o usuário está rodando (`backend-backend-1`, `backend-frontend-1`, `modelagem3d_postgres`). Pedidos de reinício e de teste manual vão para a seção "Ações do usuário".

## Foco de revisão

Situações que a spec implica, mas que nenhum teste óbvio cobre. Cada uma ganhou um teste na tarefa dona do código:

1. **A geração 3D falha ou estoura o tempo** (sal metálico `[Fe+2].[Cl-].[Cl-]`, macrociclo grande, cadeia de 160 C): o painel continua respondendo 200, os campos 3D vêm `indisponível` com motivo, e o restante do painel não muda. Testado na tarefa 3.
2. **Entrada com vários fragmentos** (surfactante + contraíon orgânico; dois anfifílicos num SMILES): os valores por átomo caem no índice RDKit certo da entrada completa, e os descritores 3D da molécula se referem ao fragmento ativo. Testado na tarefa 3.
3. **pH nos extremos 0 e 14 em moléculas anfotéricas e polipróticas:** sem exceção, carga líquida finita e LogD finito ou `indisponível`. Testado na tarefa 5.
4. **Mistura em que nenhum componente tem CMC, ou só anfifílicos de cabeça fraca:** resposta 200, nenhuma micela forçada, mensagem nomeando os componentes. Testado na tarefa 9.
5. **Edição rápida no editor 2D:** uma resposta antiga do `/analyze` não sobrescreve a mais nova. Testado na tarefa 10.

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `scripts/testar_backend.sh` | criar | Roda o pytest no container com o código montado |
| `scripts/testar_frontend.sh` | criar | Roda `npm ci`, Vitest e build no container `node:24-bookworm-slim` |
| `backend/tests/test_no_secrets.py` | criar | Impede segredos em arquivos versionados |
| `backend/tests/test_api_stability.py` | criar | Bateria HTTP de regressão |
| `backend/app/modules/chemistry/properties/__init__.py` | criar | Pacote |
| `backend/app/modules/chemistry/properties/base.py` | criar | `ParamDict`, `PropertyBundle`, `PropertyContext`, construtores |
| `backend/app/modules/chemistry/properties/electronic_basic.py` | criar | Gasteiger, pares livres, VSEPR, R/S |
| `backend/app/modules/chemistry/properties/conformer3d.py` | criar | ETKDGv3 + MMFF94/UFF e descritores 3D |
| `backend/app/modules/chemistry/properties/resonance.py` | criar | Estruturas de ressonância |
| `backend/app/modules/chemistry/properties/ionization.py` | criar | Sítios ionizáveis, pKa, carga no pH, LogD |
| `backend/app/modules/chemistry/properties/cmc_correlations.py` | criar | CMC por família, com constantes ajustadas a dados rastreáveis |
| `backend/app/modules/chemistry/properties/data/cmc_homologs.json` | criar | Dados experimentais de CMC com fonte e página |
| `backend/app/modules/chemistry/properties/data/micelle_reference.json` | criar | β e espessura de cabeça por família (só valores com fonte) |
| `backend/app/modules/chemistry/properties/micelle_theory.py` | criar | Tanford, ΔG, N_agg, raios, carga |
| `backend/app/modules/chemistry/properties/orchestrator.py` | criar | Chama os provedores, aplica cache e faz a mescla |
| `backend/app/modules/chemistry/parameters/router.py` | modificar (~L1293–1310) | Ponto de chamada do orquestrador |
| `backend/app/modules/chemistry/parameters/validated_calculations.py` | modificar | Regras das 5 classes, `amphiphile_role`, chamada à CMC por família |
| `backend/app/modules/micelium/IA/molecular_identity_ai.py` | modificar | `rules_fired`, `species_at_ph`, `amphiphile_role` |
| `backend/app/modules/micelium/IA/amphoteric_ai.py` | criar | IA especializada (linha de base, sem treino) |
| `backend/app/modules/micelium/IA/surfactant_router.py`, `chemistry_rules.py` (`route_for_class`), `prediction_service.py` | modificar | Rotear `amphoteric` → `amphoteric_ai` |
| `backend/app/modules/micelium/engine.py` | modificar | Clint parcial, `ignored_components`, convergência |
| `backend/app/modules/micelium/test_organization_geometry.py` | modificar | Novos cenários de convergência |
| `frontend/src/pages/leftpage/components/chemistryParameters.types.ts`, `ChemistryParametersPanel.tsx` | modificar | Exibir ressonância e ionização |
| `frontend/src/pages/3dpage/3dpage.tsx`, `type/3dpage.types.ts`, `components/render/SimulationViewer3D.tsx` | modificar | Selo, Previsto/Observado, componentes ignorados |
| `backend/app/main.py`, `backend/app/core/config.py` | modificar | Configuração por ambiente, GZip, rotas de demonstração |
| `backend/docker-compose.yml`, `backend/.env.example`, `backend/alembic.ini`, `iniciar_linux.sh` | modificar | Segredos fora do git |
| `backend/docker-compose.prod.yml`, `deploy/Caddyfile`, `frontend/Dockerfile` (estágio `prod`) | criar/modificar | Publicação |
| `scripts/backup_producao.sh`, `documentacao/publicacao/PUBLICAR.md` | criar | Operação |

---

### Tarefa 0: Executores de teste e segredos fora do git

**Arquivos:**
- Criar: `scripts/testar_backend.sh`, `scripts/testar_frontend.sh`, `backend/tests/test_no_secrets.py`
- Modificar: `backend/docker-compose.yml`, `backend/.env.example`, `backend/alembic.ini`, `iniciar_linux.sh`, `documentacao/recuperacao/CORRECOES_EXISTENTES.patch` (só a senha), `.gitignore`

**Interfaces:**
- Produz: `bash scripts/testar_backend.sh [args do pytest]` e `bash scripts/testar_frontend.sh`, usados por todas as tarefas.

- [ ] **Passo 1: criar `scripts/testar_backend.sh`.** Ele roda a partir da raiz do projeto:
  `docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONPATH=/deps -e DATABASE_URL=postgresql+psycopg://validation:validation@127.0.0.1/validation -v "$PWD/backend:/app" -v "$PWD/backend/.testdeps:/deps" -w /app backend-backend:latest sh -c 'test -f /deps/.ok || (pip install -q --target /deps pytest httpx && touch /deps/.ok); python -m pytest -p no:cacheprovider -q "$@"' _ ${@:-tests app/modules/micelium/test_organization_geometry.py}`.
  Acrescentar `backend/.testdeps/` ao `.gitignore`.
- [ ] **Passo 2: verificar a linha de base.**
  Rodar: `bash scripts/testar_backend.sh`. Esperado: `1217 passed`.
- [ ] **Passo 3: criar `scripts/testar_frontend.sh`.** Ele roda `docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/frontend:/app" -w /app node:24-bookworm-slim sh -c 'npm ci --no-audit --no-fund && npx vitest run --environment jsdom && npm run build'`.
  Rodar o script. Esperado: Vitest com 45 testes aprovados e o build concluído. Registrar o tamanho dos chunks impresso pelo Vite no commit; a tarefa 12 usa esse número.
- [ ] **Passo 4: escrever o teste que falha, `backend/tests/test_no_secrets.py`.**

```python
def test_no_real_env_tracked():
    tracked = git_ls_files()  # subprocess "git ls-files" na raiz (pular com pytest.skip se não houver git)
    assert not [p for p in tracked if p.split("/")[-1] in {".env", ".env.local", ".env.production"}]

def test_no_known_dev_password_in_tracked_files():
    assert grep_tracked("REMOVIDO:") == [] and grep_tracked("POSTGRES_PASSWORD: REMOVIDO") == []

def test_no_literal_password_in_database_urls():
    # regex postgresql\+psycopg://[^:/\s]+:([^@\s$]+)@ ; senhas aceitas: CHANGE_ME, validation, ${...}
    assert offending_urls() == []
```

  O container não enxerga a raiz do repositório, então este teste roda no host: `python3 -m pytest backend/tests/test_no_secrets.py -p no:cacheprovider` (o pytest do host vem de `pip install --user pytest`, ou o teste é escrito com `unittest` para dispensar o pytest; preferir `unittest`). Esperado: FALHA nos dois últimos testes.
- [ ] **Passo 5: tirar a senha dos arquivos versionados.**
  - `docker-compose.yml`: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?defina POSTGRES_PASSWORD em backend/.env}` e `DATABASE_URL: postgresql+psycopg://modelagem3d:${POSTGRES_PASSWORD}@postgres:5432/modelagem3d_db`.
  - `.env.example` e `alembic.ini`: senha `CHANGE_ME`.
  - Patch histórico: `REMOVIDO` → `<redacted>`.
  - `iniciar_linux.sh`: se `backend/.env` não existir, cria o arquivo com `POSTGRES_PASSWORD=REMOVIDO` e um comentário explicando que esse é o valor atual do banco local e que trocar o valor não troca a senha do banco (`ALTER USER`). Permissão `600`.
  - O Compose lê `backend/.env` automaticamente, porque está na mesma pasta do `docker-compose.yml`. Conferir com `docker compose -f backend/docker-compose.yml config | grep -c REMOVIDO`: esperado `2` com o `.env` criado; com o `.env` ausente, o comando falha com a mensagem do `:?`.
- [ ] **Passo 6: rodar os testes.** `test_no_secrets.py` deve PASSAR, e `bash scripts/testar_backend.sh` deve dar `1217 passed`.
- [ ] **Passo 7: commit.** `git add -A && git commit -m "chore: executores de teste e segredos fora dos arquivos versionados"`. Antes, conferir `git status` e confirmar que nenhum `.env` aparece.

### Tarefa 1: Bateria de estabilidade HTTP

**Arquivos:**
- Criar: `backend/tests/test_api_stability.py`
- Modificar: só os arquivos em que uma falha for encontrada (correção mínima)

**Interfaces:**
- Consome: `tests/fixtures/molecular_catalog.json` (151 itens `{id, name, smiles, formula, formal_charge}`).
- Produz: as constantes `EDGE_CASES: list[tuple[str, str]]` e `MIXTURE_CASES`, que as tarefas 3 e 9 reaproveitam via import.

- [ ] **Passo 1: escrever os testes.** O app de teste segue o mesmo padrão de `tests/test_calculation_http.py`: um `FastAPI()` com os routers `chemistry`, `micelium`, `micelium IA` e `molecules`. Para `molecules`, usar um banco SQLite em memória só se o router permitir sobrescrever a dependência de sessão; se não permitir, pular essas rotas com `pytest.skip("rota exige PostgreSQL")` e registrar isso no relatório final.
  - `test_analyze_by_smiles[case]`: os 151 atalhos + `EDGE_CASES` = `[("radical","[CH3]"), ("metal","[Fe+2].[Cl-].[Cl-]"), ("isotopo","[13CH4]"), ("estereo","C[C@H](N)C(=O)O"), ("cadeia160","C"*160), ("peptideo","CC(C)C[C@H](NC(=O)[C@@H](N)Cc1ccccc1)C(=O)O"), ("etoxilado","CCCCCCCCC=CCCCCCCCC(=O)OCCOCCOCCOCCOCCO"), ("multi_sal","CCCCCCCCCCCC[N+](C)(C)C.[Br-].[Na+].[Cl-]"), ("macrociclo","C1CCCCCCCCCCCCCCCCCCCCCCCCCCCCC1"), ("contraion_organico","CCCCCCCCCCCCOS(=O)(=O)[O-].CC[NH+](CC)CC")]`. Afirmações: status 200; `"NaN" not in r.text and "Infinity" not in r.text`; todo dict com `available is False` em `molecule`, `atoms[*]` e `bonds[*]` tem `note` não vazia.
  - `test_analyze_invalid_inputs`: `""` e `"C1CC"` → 400 com `detail` em texto.
  - `test_analyze_by_internal_molecule[case]`: para 20 atalhos, primeiro `POST /chemistry/rdkit/parse-2d {"identifier": smiles}`, depois `POST /parameters/analyze {"internal_molecule": resposta["internal_molecule"]}` → 200 com a mesma `formula_molecular`.
  - `test_ai_routes[case]`: `/micelium-ai/analyze` e `/micelium-ai/predict` nos 151 atalhos → 200.
  - `test_simulate[case]`: `MIXTURE_CASES` = SDS 3 mmol e SDS 0,1 mmol em 100 mL; SDS + C12E5; SDS + hexano; só hexano; SDS em solvente `hexane`. Cada um com `count` 40 e `steps` 120 → 200, coordenadas finitas em todos os quadros.
- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_api_stability.py -x`. Esperado: passa, ou falha mostrando o primeiro caso quebrado.
- [ ] **Passo 3: corrigir cada falha com a mudança mínima,** usando superpowers:systematic-debugging. Se não houver falha, nada a corrigir. O relatório final registra que os 500 relatados não se reproduziram.
- [ ] **Passo 4: suíte completa.** `bash scripts/testar_backend.sh`. Esperado: tudo passa.
- [ ] **Passo 5: commit.** `test: bateria de estabilidade HTTP` (mais `fix: …` por correção, se houver).

### Tarefa 2: Contrato dos provedores e propriedades eletrônicas básicas

**Arquivos:**
- Criar: `properties/__init__.py`, `properties/base.py`, `properties/electronic_basic.py`, `properties/orchestrator.py`, `backend/tests/test_properties_electronic.py`
- Modificar: `chemistry/parameters/router.py` (ponto de chamada, logo após o laço `for key in ["area_cabeca_micela", ...]` e depois de `atoms = build_atoms(mol)` / `bonds = build_bonds(mol)`)

**Interfaces (produz):**

```python
ParamDict = dict[str, Any]  # mesmo formato de router.param(): value, unit, source, available, confidence, note

def value(v: Any, source: str, unit: str | None = None, confidence: str = "estimated", note: str | None = None) -> ParamDict
def not_applicable(reason: str, source: str, unit: str | None = None) -> ParamDict   # note = "não se aplica: " + reason
def unavailable(reason: str, source: str, unit: str | None = None) -> ParamDict      # note = "indisponível: " + reason

@dataclass(frozen=True)
class PropertyContext:
    mol: Chem.Mol                    # entrada completa, sanitizada (a mesma de make_response)
    structure: StructuralProfile     # validated.profile(mol)
    env: dict[str, Any]              # env_from(payload)
    active_atom_indices: tuple[int, ...]  # índices em `mol` dos átomos do fragmento ativo

@dataclass
class PropertyBundle:
    molecule: dict[str, ParamDict] = field(default_factory=dict)
    atoms: dict[int, dict[str, ParamDict]] = field(default_factory=dict)   # chave: rdkit_idx em `mol`
    bonds: dict[int, dict[str, ParamDict]] = field(default_factory=dict)   # chave: bond idx em `mol`
    def update(self, other: "PropertyBundle") -> None

# electronic_basic.py
def compute(ctx: PropertyContext) -> PropertyBundle
# orchestrator.py
def build_context(mol, structure, env) -> PropertyContext   # active_atom_indices pelo casamento do SMILES canônico do fragmento em Chem.GetMolFrags(mol, asMols=False)
def compute_all(ctx: PropertyContext) -> PropertyBundle
def merge_into(molecule: dict, atoms: list[dict], bonds: list[dict], bundle: PropertyBundle) -> None
```

**Regra do `merge_into`:** um campo do bundle substitui o atual só se o atual estiver ausente ou com `available is False`. Exceção: `configuracao_absoluta` pode ser trocada de `unavailable` por `not_applicable`. Chaves novas são sempre adicionadas.

- [ ] **Passo 1: escrever os testes que falham** em `tests/test_properties_electronic.py`, chamando o endpoint pelo app de teste:

```python
def test_lone_pairs_and_vsepr():
    w = atoms_of("O")[0];  assert w["pares_livres"]["value"] == 2 and w["geometria_eletronica"]["value"] == "tetraédrica"
    assert atoms_of("C")[0]["geometria_eletronica"]["value"] == "tetraédrica" and atoms_of("C")[0]["pares_livres"]["value"] == 0
    assert atoms_of("C=C")[0]["geometria_eletronica"]["value"] == "trigonal plana"
    assert atoms_of("O=C=O")[1]["geometria_eletronica"]["value"] == "linear"
    assert atoms_of("N")[0]["pares_livres"]["value"] == 1

def test_gasteiger_present_and_finite():
    for a in atoms_of("CCO"):
        g = a["carga_gasteiger"]; assert g["available"] and math.isfinite(g["value"]) and g["confidence"] == "low"

def test_cip_and_not_applicable():
    ala = atoms_of("C[C@H](N)C(=O)O"); assert ala[1]["configuracao_absoluta"]["value"] == "S"
    assert ala[0]["configuracao_absoluta"]["note"].startswith("não se aplica")

def test_merge_never_overwrites_available_value():
    m = {"logp": {"value": 1.0, "available": True}}; b = PropertyBundle(molecule={"logp": value(9.0, "x")})
    merge_into(m, [], [], b); assert m["logp"]["value"] == 1.0
```

- [ ] **Passo 2: rodar.** `bash scripts/testar_backend.sh tests/test_properties_electronic.py`. Esperado: FALHA (`ModuleNotFoundError: app.modules.chemistry.properties`).
- [ ] **Passo 3: implementar.**
  - `base.py` e `electronic_basic.py`: Gasteiger por `AllChem.ComputeGasteigerCharges` numa cópia de `mol`; NaN vira `unavailable("Gasteiger sem parâmetros para este elemento", …)`.
  - Pares livres: `(elétrons de valência − carga formal − soma das ordens de ligação incluindo H − elétrons radicais) // 2`, com elétrons de valência por `Chem.GetPeriodicTable().GetNOuterElecs`. Resultado negativo vira `unavailable`.
  - VSEPR: domínios = vizinhos (incluindo H) + pares livres; 2 → "linear", 3 → "trigonal plana", 4 → "tetraédrica", 5 → "bipirâmide trigonal", 6 → "octaédrica". Átomo aromático ou conjugado com 3 domínios σ → "trigonal plana".
  - Íons monoatômicos: geometria `not_applicable("íon monoatômico")`.
  - `orchestrator.compute_all` chama só `electronic_basic` nesta tarefa.
  - No `router.py`, após `atoms`/`bonds` serem construídos: `ctx = orchestrator.build_context(mol, structure, env); orchestrator.merge_into(molecule, atoms, bonds, orchestrator.compute_all(ctx))`. O snapshot é montado depois da mescla.
- [ ] **Passo 4: rodar o teste da tarefa e a suíte completa.** Esperado: PASSA.
- [ ] **Passo 5: commit.** `feat(propriedades): contrato de provedores e propriedades eletrônicas básicas`.

### Tarefa 3: Conformação 3D (ETKDGv3 + MMFF94) e descritores 3D

**Arquivos:**
- Criar: `properties/conformer3d.py`, `backend/tests/test_properties_conformer3d.py`
- Modificar: `properties/orchestrator.py`

**Interfaces:**
- Consome: `PropertyContext`, `PropertyBundle`, `value`, `unavailable` (tarefa 2).
- Produz: `conformer3d.compute(ctx: PropertyContext, timeout_s: float = 2.0) -> PropertyBundle`, além de `orchestrator.compute_all` com cache LRU de 512 entradas, chave `(Chem.MolToSmiles(mol, isomericSmiles=True), tuple(sorted(env.items())))`.

Campos preenchidos:
- Na molécula: `raio_de_giracao` e `raio_giracao` (nm), `npr1`, `npr2`, `volume_vdw_total` (Å³), `sasa_total` (Å²), `energia_conformacional` (kcal/mol), `vetor_momento_dipolo` (`{x, y, z, magnitude}` em Debye, com cargas de Gasteiger, `confidence: "low"`).
- Por átomo: `posicao_3d` (`{x, y, z}` em Å), `sasa_local` (Å²), `tipo_campo_de_forca` (tipo MMFF94 inteiro, ou `"UFF:<rótulo>"`).
- Por ligação: `comprimento_ideal` (Å, com a nota "comprimento na geometria MMFF94 otimizada (1 confórmero, fase gasosa)").

Descritores da molécula vêm só dos átomos do fragmento ativo. Valores por átomo e por ligação usam a entrada completa.

- [ ] **Passo 1: escrever os testes que falham.**

```python
@pytest.mark.parametrize("smiles,bond,ref", [("CC",(0,1),1.53),("C=C",(0,1),1.34),("c1ccccc1",(0,1),1.39),("CC=O",(1,2),1.22),("CCO",(1,2),1.43)])
def test_mmff_bond_lengths(smiles, bond, ref):
    assert bond_of(smiles, *bond)["comprimento_ideal"]["value"] == pytest.approx(ref, abs=0.03)

def test_shape_descriptors_present_for_sds():
    m = molecule_of(SDS)
    for k in ["raio_de_giracao","npr1","npr2","volume_vdw_total","sasa_total","energia_conformacional"]:
        assert m[k]["available"] and math.isfinite(m[k]["value"])
    assert 0 <= m["npr1"]["value"] <= m["npr2"]["value"] <= 1

def test_salt_descriptors_use_active_fragment():   # Foco de revisão 2
    assert molecule_of(SDS)["raio_de_giracao"]["value"] == pytest.approx(molecule_of("CCCCCCCCCCCCOS(=O)(=O)[O-]")["raio_de_giracao"]["value"], rel=1e-6)
    atoms = atoms_of("CCCCCCCCCCCCOS(=O)(=O)[O-].CC[NH+](CC)CC")
    assert all(a["posicao_3d"]["available"] for a in atoms)

@pytest.mark.parametrize("smiles", ["[Fe+2].[Cl-].[Cl-]", "C"*160, "C1CCCCCCCCCCCCCCCCCCCCCCCCCCCCC1"])
def test_3d_failure_is_explicit(smiles):          # Foco de revisão 1
    r = client.post(ANALYZE, json={"smiles": smiles}); assert r.status_code == 200
    assert r.json()["molecule"]["peso_molecular"] > 0
    for a in r.json()["atoms"]:
        assert a["posicao_3d"]["available"] or a["posicao_3d"]["note"]

def test_deterministic():
    assert molecule_of("CCCCO")["raio_de_giracao"] == molecule_of("CCCCO")["raio_de_giracao"]
```

- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar.**
  - Moléculas com mais de 150 átomos pesados: devolver `unavailable("molécula acima do limite da versão web (150 átomos pesados)")` sem embutir.
  - Geração: `Chem.AddHs(mol)`; `EmbedMolecule` com `ETKDGv3()`, `randomSeed=0xF00D` e `timeout` inteiro de 2 s; `MMFFOptimizeMolecule(maxIters=500)` quando `MMFFHasAllMoleculeParams`, senão `UFFOptimizeMolecule`; se nenhum dos dois tiver parâmetros, `unavailable`.
  - Descritores: `Descriptors3D.RadiusOfGyration` (Å → nm), `NPR1`/`NPR2`, `AllChem.ComputeMolVolume` e `rdFreeSASA` (raios `classifyAtoms`), aplicados ao fragmento ativo extraído com `Chem.GetMolFrags(molH, asMols=True, fragsMolAtomMapping=…)`.
  - Energia: MMFF (ou UFF) da geometria final. Dipolo: Σ qᵢ·rᵢ com as cargas de Gasteiger da tarefa 2, em e·Å × 4,80320427 = D.
  - Índices dos H implícitos não são expostos; os átomos pesados mantêm os índices de `mol`.
  - Toda exceção do RDKit vira `unavailable` com o motivo.
- [ ] **Passo 4: rodar a tarefa e a suíte completa. Medir o p95** com `pytest tests/test_api_stability.py -k analyze_by_smiles --durations=10`. Esperado: tudo passa e nenhum caso de até 100 átomos pesados acima de 300 ms. Se passar disso, reduzir `maxIters` para 200 e repetir.
- [ ] **Passo 5: commit.** `feat(propriedades): conformação MMFF94 e descritores 3D`.

### Tarefa 4: Ressonância

**Arquivos:**
- Criar: `properties/resonance.py`, `backend/tests/test_properties_resonance.py`
- Modificar: `properties/orchestrator.py`

**Interfaces:**
- Produz: `resonance.compute(ctx) -> PropertyBundle`, com campos novos:
  - Na molécula: `ressonancia_numero_estruturas` (int), `ressonancia_atomos_deslocalizados` (`list[int]`), `ressonancia_ligacoes_deslocalizadas` (`list[int]`), `sistemas_conjugados` (int, de `GetNumConjGrps`).
  - Por átomo: `carga_media_ressonancia` (média da carga formal entre as estruturas).
  - Por ligação: `ordem_media_ressonancia` (média de `GetBondTypeAsDouble` entre as estruturas Kekulé).
  - Todos com `source: "RDKit ResonanceMolSupplier"`, `confidence: "high"` e a nota "estruturas de Lewis formais, sem peso de contribuição".

- [ ] **Passo 1: escrever os testes que falham.**

```python
@pytest.mark.parametrize("smiles,n", [("c1ccccc1",2),("CC(=O)[O-]",2),("C[N+](=O)[O-]",2),("CC(N)=O",2),("CC",1)])
def test_resonance_structure_count(smiles, n):
    assert molecule_of(smiles)["ressonancia_numero_estruturas"]["value"] == n

def test_acetate_oxygens_share_charge():
    a = atoms_of("CC(=O)[O-]"); assert a[2]["carga_media_ressonancia"]["value"] == pytest.approx(-0.5) == a[3]["carga_media_ressonancia"]["value"]

def test_benzene_bond_order_average():
    assert all(b["ordem_media_ressonancia"]["value"] == pytest.approx(1.5) for b in bonds_of("c1ccccc1"))
```

  Se o RDKit contar a amida neutra de forma diferente (só as formas com separação de carga habilitadas por flag), usar `ALLOW_CHARGE_SEPARATION` e manter a expectativa 2. Se ainda assim divergir, o teste passa a registrar o valor do RDKit, e a divergência entra no relatório; o valor não é forçado.
- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar** com `Chem.ResonanceMolSupplier(mol, Chem.KEKULE_ALL | Chem.ALLOW_CHARGE_SEPARATION, maxStructs=64)`. Acima de 150 átomos pesados: `unavailable` com o mesmo motivo da tarefa 3. Atingir o limite de 64 vira nota "≥ 64 (limite de enumeração)".
- [ ] **Passo 4: rodar a tarefa e a suíte completa.** Esperado: PASSA.
- [ ] **Passo 5: commit.** `feat(propriedades): ressonância`.

### Tarefa 5: Ionização e espécie no pH

**Arquivos:**
- Criar: `properties/ionization.py`, `backend/tests/test_properties_ionization.py`
- Modificar: `properties/orchestrator.py`

**Interfaces (produz):**

```python
SiteKind = Literal["acid", "base", "permanent_cation", "permanent_anion"]
@dataclass(frozen=True)
class IonizableSite:
    atom_idx: int; group: str; pka: float | None; kind: SiteKind; reference: str

PKA_TABLE: list[tuple[str, str, float, SiteKind, str]]  # (grupo, SMARTS, pKa, tipo, referência)
def ionizable_sites(mol: Chem.Mol) -> list[IonizableSite]
def net_charge_at_ph(sites: list[IonizableSite], ph: float) -> float
def effective_species(sites: list[IonizableSite], ph: float) -> Literal["anionic","cationic","nonionic","zwitterionic"]
def compute(ctx) -> PropertyBundle
```

`compute` preenche na molécula: `sitios_ionizaveis` (lista de dicts), `carga_liquida_ph`, `especie_predominante_ph`, e também `pka` e `logd` quando o campo atual estiver indisponível (a regra do merge preserva os valores que já existem).

- `PKA_TABLE` usa os valores da seção 4.3 da spec: ácido carboxílico 4,8; ácido sulfônico −1,9; monoéster sulfato −3,0; fosfato 2,1 e 7,2; fenol 10,0; amina primária alifática 10,6; secundária 11,0; terciária 9,8; piridina 5,2; anilina 4,6; imidazol 7,0; óxido de amina 4,6 (base: N–O⁻ + H⁺ ⇌ N–OH⁺); N⁺ quaternário = `permanent_cation`. A ordem dos SMARTS vai do mais específico ao mais geral, e cada átomo recebe um único sítio.
- **Referências:** cada linha da tabela registra a fonte. Antes de gravar, o executor confere cada pKa numa referência acessível (por exemplo, a tabela de pKa de Evans/Ripin ou o CRC Handbook). Se um valor não puder ser conferido, a linha fica fora e o grupo não recebe pKa.
- **Carga líquida:** soma, por sítio independente, de −1/(1+10^(pKa−pH)) para ácidos e +1/(1+10^(pH−pKa)) para bases; permanentes valem ±1.
- **Espécie efetiva:** carga positiva e negativa, cada uma ≥ 0,5 no pH → `zwitterionic`. Senão, carga líquida ≤ −0,5 → `anionic`; ≥ 0,5 → `cationic`; caso contrário `nonionic`.
- **LogD:** logP de Crippen da forma neutra (todos os sítios ionizáveis neutralizados) + log10(fração neutra), em que a fração neutra é o produto das frações neutras de cada sítio. Fração neutra < 1e-12 ou presença de sítio permanente → `unavailable("espécie neutra desprezível neste pH")`.

- [ ] **Passo 1: escrever os testes que falham.**

```python
@pytest.mark.parametrize("smiles,ph,charge", [("CC(=O)O",2,0),("CC(=O)O",7,-1),("CC(=O)O",12,-1),("Oc1ccccc1",7,0),("Oc1ccccc1",12,-1),
    ("CN",2,1),("CN",12,0),("c1ccncc1",2,1),("c1ccncc1",7,0),("Nc1ccccc1",2,1),("NCC(=O)O",2,1),("NCC(=O)O",7,0),("NCC(=O)O",12,-1)])
def test_net_charge(smiles, ph, charge):
    assert net_charge_at_ph(ionizable_sites(Chem.MolFromSmiles(smiles)), ph) == pytest.approx(charge, abs=0.1)

def test_glycine_is_zwitterionic_species_at_ph7():
    assert effective_species(ionizable_sites(Chem.MolFromSmiles("NCC(=O)O")), 7.0) == "zwitterionic"

@pytest.mark.parametrize("smiles", ["NCC(=O)O","CCCCCCCCCCCCNCC(=O)O","OC(=O)CC(O)(CC(=O)O)C(=O)O","CCCCCCCCCCCC[N+](C)(C)[O-]"])
@pytest.mark.parametrize("ph", [0.0, 14.0])
def test_extreme_ph_is_finite(smiles, ph):           # Foco de revisão 3
    m = molecule_of(smiles, ph=ph)
    assert math.isfinite(m["carga_liquida_ph"]["value"])
    assert (m["logd"]["available"] and math.isfinite(m["logd"]["value"])) or m["logd"]["note"]

def test_quaternary_is_permanent():
    assert [s.kind for s in ionizable_sites(Chem.MolFromSmiles("C[N+](C)(C)C"))] == ["permanent_cation"]
```

- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar** conforme as interfaces acima. `ctx.env["ph"]` vem de `env_from`.
- [ ] **Passo 4: rodar a tarefa e a suíte completa.** Esperado: PASSA.
- [ ] **Passo 5: commit.** `feat(propriedades): sítios ionizáveis, carga e espécie no pH`.

### Tarefa 6: Identificação das cinco classes, papel de cabeça fraca e `amphoteric_ai`

**Arquivos:**
- Modificar: `chemistry/parameters/validated_calculations.py` (`CLASS_PT`, `StructuralProfile`, `profile`), `micelium/IA/molecular_identity_ai.py`, `micelium/IA/chemistry_rules.py` (`route_for_class`), `micelium/IA/surfactant_router.py`, `micelium/IA/prediction_service.py` (registro das IAs)
- Criar: `micelium/IA/amphoteric_ai.py`, `backend/tests/fixtures/surfactant_classes.json`, `backend/tests/test_surfactant_identification.py`

**Interfaces:**
- Consome: `ionization.ionizable_sites`, `effective_species` (tarefa 5).
- Produz:
  - `CLASS_PT` com `"zwitterionic": "zwitteriônico"` e `"amphoteric": "anfotérico"`.
  - `StructuralProfile` com dois campos novos no fim (com default, para não quebrar construtores existentes): `amphiphile_role: Literal["surfactant", "surfactant_or_cosurfactant", "none"] = "none"` e `rules_fired: tuple[str, ...] = ()`.
  - `surfactant_class` pode passar a valer `"amphoteric"`.
  - `chemical_class`, baseado em carga formal e usado por `packing_estimate`, não muda.

**Regras** (seção 5 da spec), aplicadas aos sítios da cabeça, isto é, aos sítios fora da cauda:
- Cátion permanente (N⁺ quaternário que não é N-óxido, ou P⁺) + sítio ácido ou ânion → `zwitterionic`.
- Óxido de amina, ou sítio básico ionizável + sítio ácido → `amphoteric`.
- Só sítios ácidos → `anionic`. Só sítios básicos ou catiônicos → `cationic`.
- Nenhum sítio com pKa entre 2 e 12, e cabeça polar → `nonionic`.
- **Cabeça fraca:** a cabeça tem um único grupo polar entre –OH, –COOH neutro e amina neutra, sem outro heteroátomo polar. Nesse caso, `amphiphile_role = "surfactant_or_cosurfactant"` e `cmc_estimate` devolve `method="not_available"` com a nota da seção 5.1 da spec. Quando `is_surfactant` é verdadeiro e a cabeça não é fraca, `amphiphile_role = "surfactant"`.
- `rules_fired` lista os nomes das regras e grupos que dispararam, por exemplo `("permanent_cation:quaternary_ammonium", "acid:carboxylate")`.

- [ ] **Passo 1: montar o fixture `tests/fixtures/surfactant_classes.json`.** Cada item tem `{name, smiles, expected_class, expected_role, reference}`. Composição, conforme a seção 8.3 da spec:
  - 8 aniônicos, 8 catiônicos, 8 não iônicos, 6 zwitteriônicos e 6 anfotéricos;
  - 11 não surfactantes (`expected_class: "unknown"`);
  - 3 de cabeça fraca (dodecanol, ácido dodecanoico, dodecilamina).
  - `reference`: a fonte que atesta a classe (ficha PubChem ou livro). O rótulo vem da literatura, não da saída do código.
- [ ] **Passo 2: escrever os testes que falham.**

```python
def test_identification_matches_labels():
    rows = load_fixture(); wrong = [(r["name"], r["expected_class"], classify(r["smiles"])) for r in rows if classify(r["smiles"]) != r["expected_class"]]
    print(confusion_matrix(rows)); assert wrong == []

def test_weak_heads_not_absolute():
    for s in ["CCCCCCCCCCCCO","CCCCCCCCCCCC(=O)O","CCCCCCCCCCCCN"]:
        ident = client.post(AI_ANALYZE, json={"smiles": s}).json()
        assert ident["descriptors"]["raw_descriptors"]["amphiphile_role"] == "surfactant_or_cosurfactant"
        assert molecule_of(s)["cmc_estimada"]["available"] is False

def test_amphoteric_species_by_ph():
    for ph, sp in [(2.0,"cationic"),(12.0,"anionic")]:
        r = client.post(AI_ANALYZE, json={"smiles":"CCCCCCCCCCCCNCC(=O)O", "environment":{"ph":ph}}).json()
        assert r["surfactant_class"] == "amphoteric" and r["provenance"]["species_at_ph"]["species"] == sp

def test_amine_oxide_amphoteric():
    assert classify("CCCCCCCCCCCC[N+](C)(C)[O-]") == "amphoteric"

def test_routes():
    assert route("CCCCCCCCCCCCNCC(=O)O") == "amphoteric_ai" and route("CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]") == "zwitterionic_ai"

def test_panel_labels_split():
    assert molecule_of("CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]")["classe_surfactante"]["value"] == "zwitteriônico"
    assert molecule_of("CCCCCCCCCCCCNCC(=O)O")["classe_surfactante"]["value"] == "anfotérico"
```

  `MolecularIdentityRequest` já tem `environment: MiceliumAIEnvironment`, então o pH vem de `request.environment.ph`.
- [ ] **Passo 3: rodar.** Esperado: FALHA.
- [ ] **Passo 4: implementar.**
  - As regras entram em `profile()`.
  - `molecular_identity_ai.analyze` passa a gravar `provenance["rules_fired"]`, `provenance["species_at_ph"] = {"ph": …, "species": …, "net_charge": …}` e `descriptors.raw_descriptors["amphiphile_role"]`.
  - `amphoteric_ai.py` copia o formato de `zwitterionic_ai.py`, com `route = "amphoteric_ai"`, `surfactant_class = "amphoteric"` e `model_version = "amphoteric_baseline_v0.1.0"`. A linha de base usa `validated.cmc_estimate` sem fórmula própria, e `heuristic_cmc` devolve `None`.
  - As cinco IAs passam a incluir `model_status: "not_trained"` na resposta quando o `model_registry` não encontrar um `.joblib`. É um campo aditivo no schema de resposta.
- [ ] **Passo 5: rodar a tarefa e a suíte completa.** Testes antigos que afirmavam "anfotérico/zwitteriônico", óxido de amina como não iônico ou dodecanol como surfactante não iônico são atualizados e citados no commit. Nenhum outro teste antigo pode mudar.
- [ ] **Passo 6: commit.** `feat(identificacao): cinco classes por estrutura e pH, papel de cabeça fraca e amphoteric_ai`.

### Tarefa 7: CMC por família com correlações fundamentadas

**Arquivos:**
- Criar: `properties/cmc_correlations.py`, `properties/data/cmc_homologs.json`, `backend/tests/test_cmc_correlations.py`
- Modificar: `validated_calculations.py` (`cmc_estimate` chama `cmc_correlations.family_cmc` quando `anchor is None`)

**Interfaces (produz):**

```python
FAMILIES = ("sodium_alkyl_sulfonate", "alkyl_carboxylate_na_k", "alkyltrimethylammonium_chloride",
            "alkylpyridinium_halide", "alkyl_betaine", "alkyl_sulfobetaine", "alkyldimethylamine_oxide", "alcohol_ethoxylate_CnEm")
def detect_family(p: StructuralProfile) -> tuple[str, int, int | None] | None   # (família, n, m), com n = carbonos da cadeia alquílica como na fonte
def fitted_constants() -> dict[str, FamilyFit]   # FamilyFit(A, B, C | None, n_min, n_max, m_min, m_max, points, loo_max_abs_log_error)
def family_cmc(p: StructuralProfile, env: dict) -> dict   # mesmo formato de validated.cmc_estimate
```

**Decisão sobre a fonte.** A spec cita Rosen e Kunjappu, que o executor não consegue consultar. A fonte primária passa a ser a compilação pública **Mukerjee e Mysels, NSRDS-NBS 36 (1971)**, disponível no site do NIST:
- `cmc_homologs.json` registra, por ponto, `{family, n, m, cmc_mmol_l, temperature_c, method, source: "NSRDS-NBS 36", page}`, só em água, sem sal adicionado e entre 20 e 30 °C.
- As constantes A, B (e C para CnEm) saem de mínimos quadrados em `log10(CMC/mol·L⁻¹)` sobre esses pontos.
- A validação é por *leave-one-out*: cada ponto é previsto pela regressão feita sem ele. Isso troca o requisito da spec 8.2 ("fonte diferente") por uma validação cruzada na mesma compilação, registrada no relatório.
- Se o autor fornecer as páginas do Rosen, elas viram o conjunto de teste independente.

**Regras de exclusão:** a família entra só se tiver ≥ 3 homólogos (≥ 5 pontos para CnEm, cobrindo ≥ 2 valores de m) e erro LOO máximo ≤ 0,3 em log10. Família reprovada fica fora de `fitted_constants()`, e `family_cmc` devolve `note="família sem correlação verificada"`. Não há extrapolação fora de [n_min, n_max] nem de [m_min, m_max].

**Ambiente:** a mesma janela de `cmc_estimate` (água, 20–25 °C), ampliada para 15–40 °C só se a fonte trouxer pontos nessas temperaturas para a família. A correção salina existente vale só para iônicos e só se a fonte trouxer pontos com sal para estimar o coeficiente; caso contrário, CMC só para força iônica ≤ 0,01 mol/L.

- [ ] **Passo 1: obter os dados.** Baixar o PDF do NSRDS-NBS 36 do NIST para `backups/fontes/`, que é ignorado pelo git, e transcrever os pontos para `cmc_homologs.json` com a página de cada um.
  - **Se o download falhar:** parar e pedir ao usuário, na seção "Ações do usuário", o PDF ou as páginas do Rosen. As tarefas 8 a 13 podem continuar com as famílias atuais (SDS/CTAB) enquanto isso.
- [ ] **Passo 2: escrever os testes que falham.**

```python
def test_each_family_meets_loo_gate():
    for fam, fit in fitted_constants().items(): assert fit.points >= 3 and fit.loo_max_abs_log_error <= 0.3

def test_out_of_domain_is_unavailable():
    assert family_cmc(profile_of("C"*30 + "S(=O)(=O)[O-].[Na+]"), WATER)["value"] is None

def test_no_cmc_for_non_surfactants():
    for s in ["CCCCCC","Oc1ccccc1","OCC1OC(O)C(O)C(O)C1O","CCCCCCCCCCCCO"]: assert molecule_of(s)["cmc_estimada"]["available"] is False

def test_sds_ctab_unchanged():
    assert molecule_of(SDS)["cmc_estimada"]["value"] == pytest.approx(7.75047, rel=1e-4)
    assert molecule_of(CTAB)["cmc_estimada"]["value"] == pytest.approx(0.88123, rel=1e-4)

def test_note_names_family_and_range():
    for fam in fitted_constants(): n = family_example_note(fam); assert fam in n and "faixa" in n
```

- [ ] **Passo 3: rodar.** Esperado: FALHA.
- [ ] **Passo 4: implementar.** `detect_family` usa igualdade de SMILES canônico com o modelo do homólogo, como `cmc_estimate` já faz. Para carboxilatos, n = `tail_c + 1`, porque a fonte conta o carbono carboxílico. `confidence: "estimated"`.
- [ ] **Passo 5: gerar o relatório** `documentacao/validacao/cmc_familias.md`, com A, B, C, domínio, número de pontos, erro LOO por família e famílias excluídas com o motivo. Gerado por `python -m app.modules.chemistry.properties.cmc_correlations --relatorio` rodando no container com `--user`.
- [ ] **Passo 6: rodar a suíte completa.** Esperado: PASSA.
- [ ] **Passo 7: commit.** `feat(cmc): correlações por família ajustadas a NSRDS-NBS 36 com validação LOO`.

### Tarefa 8: Teoria micelar leve

**Arquivos:**
- Criar: `properties/micelle_theory.py`, `properties/data/micelle_reference.json`, `backend/tests/test_micelle_theory.py`
- Modificar: `properties/orchestrator.py`

**Interfaces (produz):**

```python
def tanford(n: int) -> tuple[float, float]           # (l_max_nm, v_nm3): 0.154 + 0.1265 n ; 0.0274 + 0.0269 n
def nagg_upper_sphere(n: int) -> float               # (4/3)·π·l_max³ / v
def delta_g_mic_kj_mol(cmc_mmol_l: float, temperature_k: float, beta: float | None, ionic: bool) -> float | None
def compute(ctx, cmc_mmol_l: float | None) -> PropertyBundle
```

`compute` preenche `numero_agregacao_estimado`, `raio_nucleo_hidrofobico`, `raio_micela_cilindrica`, `delta_g_micelizacao`, `parametros_micela` (atualizado) e, só com entradas de `micelle_reference.json`, `raio_micela_esferica`/`raio_aparente_micela`/`faixa_raio_micela` (espessura de cabeça) e `carga_residual_micela`/`contraions_ligados_micela`/`densidade_carga_superficial` (β).

- `micelle_reference.json` começa **vazio**. Uma entrada (`{family, beta | head_thickness_nm, source, page}`) só é adicionada com a fonte conferida.
- Sem entrada para a família, os campos de β e de espessura ficam `unavailable("sem valor de referência verificado para <família>")`.
- `delta_g_micelizacao` para não iônicos é sempre calculado quando há CMC, e substitui o valor atual (`dg_mic`, que já é RT·ln X). A regra "não sobrescrever" vale: o valor atual já é o mesmo, então só a nota muda, via chave nova `delta_g_micelizacao_metodo`. Para iônicos, precisa de β.
- O orquestrador lê a CMC de `validated.cmc_estimate(structure, env)["value"]`, sem recalcular. Sem CMC, sem cauda linear ou com `amphiphile_role != "surfactant"`: `not_applicable`.

- [ ] **Passo 1: escrever os testes que falham.**

```python
def test_tanford_c12():
    l, v = tanford(12); assert l == pytest.approx(1.672) and v == pytest.approx(0.3502)
def test_nagg_c12():
    assert nagg_upper_sphere(12) == pytest.approx(4/3*math.pi*1.672**3/0.3502, rel=1e-9)
def test_delta_g_formula():
    x = 8.2e-3/55.5; assert delta_g_mic_kj_mol(8.2, 298.15, 0.6, True) == pytest.approx((1.6)*8.31446261815324*298.15*math.log(x)/1000, rel=1e-6)
    assert delta_g_mic_kj_mol(8.2, 298.15, None, True) is None
def test_not_applicable_for_non_surfactant():
    assert molecule_of("CCCCCC")["numero_agregacao_estimado"]["note"].startswith("não se aplica")
def test_ionic_without_beta_reference_is_unavailable():
    assert molecule_of(SDS)["carga_residual_micela"]["available"] is False   # enquanto micelle_reference.json não tiver SDS

NOT_IN_V1 = ["densidade","ponto_fusao","ponto_ebulicao","pressao_vapor","tensao_superficial","viscosidade","energia_livre_gibbs_solvacao",
             "calor_de_formacao","energia_homo","energia_lumo","gap_homo_lumo","potencial_ionizacao","afinidade_eletronica","hld","nac"]
@pytest.mark.parametrize("smiles", ["O","CCO",SDS,CTAB,"c1ccccc1O"])
def test_values_not_invented(smiles):            # spec 8.2 "valores não inventados"
    m = molecule_of(smiles); assert all(m[k]["available"] is False and m[k]["note"] for k in NOT_IN_V1)
    assert all(a["carga_quantica_ou_proxy"]["available"] is False and a["fukui_aproximado"]["available"] is False for a in atoms_of(smiles))
```

  A convenção de X_cmc segue a spec (`CMC/55,5`). O painel atual usa `CMC/(55,5 + CMC)`; a diferença é menor que 1e-3 relativo na faixa de mmol/L, e o campo `x_cmc` existente não muda.
- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar** conforme as interfaces.
- [ ] **Passo 4: rodar a tarefa e a suíte completa.** Esperado: PASSA.
- [ ] **Passo 5: commit.** `feat(propriedades): teoria micelar leve (Tanford, ΔG, N_agg)`.

### Tarefa 9: Motor 3D — mistura parcial e convergência para a morfologia prevista

**Arquivos:**
- Modificar: `micelium/engine.py` (`MicellizationMetrics`, `calculate_micellization_metrics`, montagem de `analysis`, parâmetros de formação), `micelium/schemas.py` (campos aditivos de análise, se a análise for tipada), `micelium/test_organization_geometry.py`

**Interfaces (produz):**
- `MicellizationMetrics.ignored_components: list[str]`, com nome ou SMILES, default `[]`.
- `analysis["ignored_components"]`, `analysis["prediction_note"]` (str ou `None`) e `analysis["representation_label"] = "Visualização representativa — não é simulação física"`.

- [ ] **Passo 1: escrever os testes que falham** em `test_organization_geometry.py`, chamando `MiceliumService`/rota real (que passam pela IA e pela CMC das tarefas 6 e 7):

```python
@pytest.mark.parametrize("name,smiles", [("SDS",SDS),("CTAB",CTAB)] + FAMILY_CASES)   # FAMILY_CASES: C12E5/betaína/laurato só se a tarefa 7 aprovou a família
def test_final_frame_matches_prediction_above_cmc(name, smiles):
    a = simulate_at(smiles, c_over_cmc=3.0)["analysis"]
    assert a["dominant_morphology"] == a["predicted_morphology"] != "monômeros/pré-agregados"

def test_below_cmc_no_stable_aggregate():
    a = simulate_at(SDS, c_over_cmc=0.1)["analysis"]; assert a["largest_cluster_size"] < 4 and a["predicted_morphology"] == "monômeros/pré-agregados"

def test_mixture_with_unknown_component_names_it():      # Foco de revisão 4
    a = simulate([(SDS, 3.0), ("CCCCCCCCCCCCCCCC(=O)OCC(O)CO", 1.0)])["analysis"]
    assert a["c_over_cmc_proxy"] is not None and "CCCCCCCCCCCCCCCC(=O)OCC(O)CO" in " ".join(a["ignored_components"])

def test_mixture_all_unknown_no_forced_micelle():        # Foco de revisão 4
    a = simulate([("CCCCCCCCCCCCO", 3.0), ("CCCCCC", 3.0)])["analysis"]
    assert a["c_over_cmc_proxy"] is None and a["predicted_morphology"] == "monômeros/pré-agregados" and a["ignored_components"]

def test_representation_label():
    assert simulate_at(SDS, 3.0)["analysis"]["representation_label"] == "Visualização representativa — não é simulação física"

def test_2500_particles_under_10s():
    assert timed_simulate(SDS, count=625, c_over_cmc=3.0) < 10.0
```

  `simulate_at` calcula a quantidade em mmol a partir da CMC do painel × `c_over_cmc` × volume e usa `count = 40`.
- [ ] **Passo 2: rodar.** Esperado: FALHA (hoje a observação dá "agregado em reorganização" e a mistura zera c/CMC).
- [ ] **Passo 3: mistura parcial.** Em `calculate_micellization_metrics`, componentes sem CMC (incluindo `amphiphile_role == "surfactant_or_cosurfactant"`) vão para `ignored_components` em vez de marcar `incomplete`. Se sobrar ao menos um candidato, aplicar Clint nos conhecidos e `prediction_note = "visualização aproximada: ignora <lista> por falta de CMC"`. Sem candidatos, o comportamento atual continua (`None`).
- [ ] **Passo 4: convergência** (usar superpowers:systematic-debugging).
  - Primeiro medir por que SDS a 3×CMC termina em clusters de 4 a 8: tamanho alvo, número de núcleos (`nucleation_count`), passos efetivos e os limiares de `detect_supramolecular_clusters` / classificação de morfologia.
  - Mudanças permitidas: parâmetros de `choose_formation_plan` (o número de núcleos passa a ser `ceil(n_surfactantes_visuais × micellized_fraction / N_agg_visual)`, com `N_agg_visual = min(N_agg de Tanford, n_surfactantes_visuais)`, em que N_agg vem de `micelle_theory.nagg_upper_sphere`), número de subpassos internos por quadro e limiares de detecção e classificação.
  - Proibido: remover funções ou módulos, ou reescrever o integrador.
  - Registrar a causa raiz no commit.
- [ ] **Passo 5: rodar a tarefa e a suíte completa.** Esperado: PASSA, incluindo os 24 testes de geometria existentes.
- [ ] **Passo 6: commit.** `fix(micelium): Clint parcial com componentes ignorados e convergência para a morfologia prevista`.

### Tarefa 10: Frontend — painel químico (ressonância, ionização, classes)

**Arquivos:**
- Modificar: `frontend/src/pages/leftpage/components/chemistryParameters.types.ts`, `ChemistryParametersPanel.tsx`
- Teste: `frontend/src/pages/leftpage/components/ChemistryParametersPanel.test.tsx` (criar)

**Interfaces:**
- Consome: as chaves novas das tarefas 4 e 5 (`ressonancia_*`, `sistemas_conjugados`, `sitios_ionizaveis`, `carga_liquida_ph`, `especie_predominante_ph`, `carga_media_ressonancia`, `ordem_media_ressonancia`).
- Produz: os tipos opcionais correspondentes em `MoleculeParameterData`, `AtomParameterData` e `BondParameterData`.

- [ ] **Passo 1: escrever os testes Vitest que falham.**
  - Com uma resposta simulada do acetato, o painel exibe "Estruturas de ressonância: 2" e "Espécie no pH 7,0: aniônica".
  - Um `ParameterValue` com `available: false` exibe o texto da `note`, nunca uma célula vazia.
  - **Foco de revisão 5:** duas chamadas seguidas, a primeira resolvendo depois da segunda. O painel mostra o resultado da segunda (o `AbortController` já existente em `ChemistryParametersPanel.tsx:592` cancela a primeira).
- [ ] **Passo 2: rodar.** `bash scripts/testar_frontend.sh`. Esperado: FALHA nos testes novos.
- [ ] **Passo 3: implementar.**
  - Linhas novas no grupo de molécula: seção "Ressonância" e seção "Ionização (pH do ambiente)".
  - Linhas novas no modo átomo e no modo ligação.
  - Os textos de classe chegam prontos do backend ("zwitteriônico" e "anfotérico").
  - Exibir `note` sempre que `available` for falso, se o painel ainda não fizer isso.
- [ ] **Passo 4: rodar.** Esperado: PASSA, com os 45 testes antigos e o build.
- [ ] **Passo 5: commit.** `feat(frontend): ressonância e ionização no painel químico`.

### Tarefa 11: Frontend — selo de visualização e Previsto/Observado no 3D

**Arquivos:**
- Modificar: `frontend/src/pages/3dpage/3dpage.tsx` (bloco ~L1525–1540), `type/3dpage.types.ts`, `components/render/SimulationViewer3D.tsx`
- Teste: `frontend/src/pages/3dpage/3dpage.labels.test.tsx` (criar)

**Interfaces:**
- Consome: `analysis.representation_label`, `analysis.ignored_components`, `analysis.prediction_note` (tarefa 9).

- [ ] **Passo 1: escrever os testes que falham.**
  - O visualizador renderiza o texto exato "Visualização representativa — não é simulação física".
  - O painel tem os títulos "Previsto pelos cálculos" (CMC, c/CMC, CPP, morfologia prevista, N_agg, com fonte e confiança quando houver) e "Observado na visualização" (morfologia observada, clusters, tamanho médio, fração organizada).
  - Com `ignored_components = ["X"]`, aparece a `prediction_note`.
- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar.** O selo fica fixo sobre o canvas em `SimulationViewer3D.tsx`, e só usa `analysis.representation_label` se ele vier preenchido. Os grupos ficam em `3dpage.tsx`, reutilizando os elementos `<strong>` já existentes. Nenhuma mudança no renderizador `InstancedMesh`.
- [ ] **Passo 4: rodar.** Esperado: PASSA, com o build.
- [ ] **Passo 5: commit.** `feat(frontend): selo de visualização representativa e separação Previsto/Observado`.

### Tarefa 12: Otimizações de backend e frontend para web

**Arquivos:**
- Modificar: `backend/app/core/config.py`, `backend/app/main.py`, `backend/Dockerfile` (CMD), os arquivos do frontend que definem `API_BASE_URL` (achar com `grep -rn "VITE_API_URL" frontend/src`), `frontend/Dockerfile`, `backend/docker-compose.yml` (`target: dev` no frontend)
- Teste: `backend/tests/test_web_config.py` (criar)

**Interfaces (produz):**
- `Settings` ganha `app_env: Literal["development", "production"]` (default `"development"`, como hoje) e `max_request_bytes: int = 2_000_000`.
- `main.py` adiciona `GZipMiddleware(minimum_size=1024)` e um middleware de limite de corpo que responde 413.
- O CMD do backend passa a ser `sh -c 'exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2} --proxy-headers --forwarded-allow-ips="*"'`.
- O frontend usa `import.meta.env.VITE_API_URL ?? "/api/v1"` em todas as bases de URL. Hoje o default é `http://127.0.0.1:8000/api/v1`; o `.env.example` do frontend mantém essa URL para desenvolvimento local.
- `frontend/Dockerfile` ganha estágios: `build` (o atual), `dev` (o CMD atual com `vite preview`, alvo usado pelo `docker-compose.yml` existente através de `target: dev`) e `prod` (`caddy:2` servindo `dist/` com `deploy/Caddyfile`).

- [ ] **Passo 1: escrever os testes que falham.**

```python
def test_gzip_on_simulate(): assert client.post(SIM, json=CASE, headers={"Accept-Encoding":"gzip"}).headers["content-encoding"] == "gzip"
def test_body_limit(): assert client.post(ANALYZE, content=b"x"*2_100_000, headers={"Content-Type":"application/json"}).status_code == 413
def test_demo_route_not_exposed(): assert "/api/v1/simulation/ws/openmm" not in [r.path for r in create_app().routes]
def test_cors_from_settings():
    app = create_app(Settings(database_url="postgresql+psycopg://v:v@127.0.0.1/v", backend_cors_origins=["https://exemplo.org"]))
    assert any(m.kwargs.get("allow_origins") == ["https://exemplo.org"] for m in app.user_middleware)
```

  `main.py` hoje cria o app no import. Adicionar `def create_app(settings: Settings | None = None) -> FastAPI`, com o corpo atual, e manter `app = create_app()`. É uma mudança aditiva. O `openmm_stream.py` não é incluído por nenhum router hoje, então a spec 7.1 ("rotas de demonstração desativadas") já está cumprida; o teste só garante que continue assim, e não é preciso criar uma flag.
- [ ] **Passo 2: rodar.** Esperado: FALHA.
- [ ] **Passo 3: implementar** conforme as interfaces.
- [ ] **Passo 4: medir o bundle** com `bash scripts/testar_frontend.sh`, lendo a saída do Vite. Se o chunk principal passar de 1 MB gzip, aplicar `React.lazy` + `Suspense` no visualizador 3D e depois no editor 2D, medindo após cada um. Registrar antes e depois no commit.
- [ ] **Passo 5: rodar as duas suítes.** Esperado: PASSA. O `docker compose -f backend/docker-compose.yml config` continua válido.
- [ ] **Passo 6: commit.** `perf/web: configuração por ambiente, gzip, limite de corpo, URL relativa e bundle`.

### Tarefa 13: Publicação (VPS documentada e testada; serviço gerenciado documentado)

**Arquivos:**
- Criar: `backend/docker-compose.prod.yml`, `deploy/Caddyfile`, `scripts/backup_producao.sh`, `scripts/fumaca_producao.sh`, `documentacao/publicacao/PUBLICAR.md`

**Interfaces:**
- `docker-compose.prod.yml` é sobreposto ao atual:
  - `postgres` sem `ports`;
  - `backend` sem `ports`, com `APP_ENV=production`, `BACKEND_CORS_ORIGINS` e `UVICORN_WORKERS` vindos do `.env`;
  - `frontend` com `target: prod`;
  - serviço `caddy` ouvindo `${HTTP_PORT:-80}` e `${HTTPS_PORT:-443}`.
- O `Caddyfile` usa `{$SITE_ADDRESS}` (domínio em produção, `:80` no teste local), `handle /api/* { reverse_proxy backend:8000 }` e arquivos estáticos com fallback para `index.html`.

- [ ] **Passo 1: escrever `scripts/fumaca_producao.sh`.**
  - Sobe a pilha com nome de projeto separado: `docker compose -p m3d_fumaca -f backend/docker-compose.yml -f backend/docker-compose.prod.yml --env-file backend/.env.fumaca up -d --build`, usando `HTTP_PORT=8088`, `SITE_ADDRESS=:80` e um volume próprio (`m3d_fumaca_pgdata`, para não tocar o banco real).
  - Verifica `curl -fsS localhost:8088/` (200, HTML), `curl -fsS localhost:8088/api/v1/health/database` (`"connected"`) e `nc -z 127.0.0.1 5432`/`5433` falhando para o projeto `m3d_fumaca`.
  - No fim, `docker compose -p m3d_fumaca down -v`, que remove só o volume de fumaça.
- [ ] **Passo 2: rodar.** `docker compose ... config` deve ser válido. Rodar `bash scripts/fumaca_producao.sh`. Esperado: as três verificações passam. **Antes de rodar, conferir a RAM livre** (`free -m`); com menos de 1.500 MB livres, pedir ao usuário, na seção "Ações do usuário", que feche programas ou aprove parar a pilha de desenvolvimento.
- [ ] **Passo 3: `scripts/backup_producao.sh`.** Faz `docker compose exec -T postgres pg_dump -Fc` para `backups/producao/modelagem3d_<data>.dump` e mantém os 7 mais recentes. Testar contra a pilha de fumaça antes do `down`; o arquivo `.dump` precisa existir e ter mais de 0 bytes.
- [ ] **Passo 4: `PUBLICAR.md`.**
  - Caminho VPS: requisitos (2 vCPUs, 2 GB, 20 GB, Docker), DNS, `.env` de produção com uma senha nova (`openssl rand -base64 32`), subir a pilha, verificar, backup diário via cron.
  - Caminho gerenciado: variáveis (`DATABASE_URL`, `BACKEND_CORS_ORIGINS`, `APP_ENV`, `PORT`, `UVICORN_WORKERS`, `VITE_API_URL`), imagem do backend, build estático do frontend, Postgres 16 gerenciado.
  - Aviso: o histórico do git ainda contém a senha de desenvolvimento. Reescrever o histórico antes do primeiro `git push` (ver "Ações do usuário").
- [ ] **Passo 5: commit.** `feat(publicacao): compose de produção com Caddy, fumaça, backup e guia`.

### Tarefa 14: Verificação final e relatório

- [ ] **Passo 1:** `bash scripts/testar_backend.sh`, `bash scripts/testar_frontend.sh` e `python3 -m unittest backend/tests/test_no_secrets.py`. Todos passam; anotar as contagens.
- [ ] **Passo 2:** reexecutar a medição de campos indisponíveis feita no diagnóstico (SDS, fenol, acetato, betaína) e registrar quantos campos continuam indisponíveis e com que motivo. Nenhum pode estar sem `note`.
- [ ] **Passo 3:** escrever `documentacao/validacao/WEB_LITE_V1.md` com:
  - testes e contagens;
  - tabela de métodos e limites (seção 4.3 da spec);
  - famílias de CMC aceitas e excluídas;
  - matriz de confusão da identificação;
  - medições de desempenho (p95 e tempo do 3D) e o bundle antes e depois;
  - desvios em relação à spec: fonte de CMC NSRDS com LOO; β e espessura de cabeça vazios sem fonte; X_cmc.
- [ ] **Passo 4: commit.** `docs: relatório de validação Web Lite v1`.

---

## Ações do usuário

O executor avisa no momento certo, com o texto abaixo.

| Quando | O que fazer | Resultado esperado |
|---|---|---|
| Depois da tarefa 0 | `bash iniciar_linux.sh` | O script cria `backend/.env` com a senha atual e termina com a mensagem de sucesso de sempre; os dados continuam lá |
| Se a tarefa 7, passo 1, não conseguir o PDF do NIST | Enviar o PDF do NSRDS-NBS 36 ou fotos das tabelas de CMC do Rosen | O executor transcreve os dados e retoma a tarefa 7 |
| Se a tarefa 13, passo 2, encontrar menos de 1,5 GB livres | Fechar programas, ou responder "pode parar a pilha de desenvolvimento" | A fumaça roda; depois o usuário reinicia com `bash iniciar_linux.sh` |
| Depois da tarefa 14 | `bash iniciar_linux.sh`, depois Ctrl+F5 em http://localhost:5173 e o roteiro visual abaixo | Ver o roteiro |
| Antes do primeiro `git push` | Decidir entre reescrever o histórico local (o executor faz isso com `git filter-repo` ou recriando os commits) ou manter o repositório privado. O executor não faz `push` | Histórico sem a senha de desenvolvimento |
| Antes de publicar | Escolher entre VPS e serviço gerenciado, e o domínio | O executor segue `PUBLICAR.md` com a escolha |

**Roteiro visual depois da tarefa 14:**
1. Gerar SDS (`CCCCCCCCCCCCOS(=O)(=O)[O-].[Na+]`). O painel mostra raio de giração, SASA, comprimentos de ligação, "Estruturas de ressonância: 2" e "Espécie no pH 7,0: aniônica". Campos térmicos mostram o motivo, não ficam em branco.
2. Gerar a betaína (`CCCCCCCCCCCC[N+](C)(C)CC(=O)[O-]`): classe "zwitteriônico". Gerar N-dodecilglicina (`CCCCCCCCCCCCNCC(=O)O`): classe "anfotérico".
3. Salvar o SDS, usar 3 mmol em 100 mL e clicar em **Misturar**. O 3D mostra o selo "Visualização representativa — não é simulação física". "Previsto" e "Observado" indicam "micela esférica".
4. Repetir com 0,1 mmol: sem micela estável, "Previsto: monômeros/pré-agregados".
