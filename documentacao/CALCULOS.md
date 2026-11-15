# Como os cálculos são feitos

Resumo de **todos os cálculos ativos** do Modelagem3D (Web Lite v1): de onde vem cada número, qual fórmula é usada, em que faixa ela vale e quando o campo fica indisponível. Conferido contra o código em 14/11/2026.

Documentos de apoio:
- [validacao/WEB_LITE_V1.md](validacao/WEB_LITE_V1.md): relatório de validação, com testes, desempenho e limitações.
- [validacao/cmc_familias.md](validacao/cmc_familias.md): constantes e validação da CMC por família.
- [validacao/relatorio_validacao_calculos.md](validacao/relatorio_validacao_calculos.md): registro histórico da correção de 04/11/2026.

## Princípio geral

O painel nunca inventa um número. Todo campo vem marcado com **origem** e **confiança**:

| Confiança | Significado |
|---|---|
| `experimental` | Valor medido, tirado de tabela de referência (NIST) |
| `high` | Cálculo exato a partir do grafo molecular (contagens, CIP, Lewis) |
| `medium` | Cálculo com aproximação conhecida (ex.: 1 confórmero MMFF) |
| `estimated` | Correlação empírica ou modelo teórico simples dentro do domínio |
| `low` | Estimativa grosseira (ex.: carga de Gasteiger) |
| indisponível | Não há método fundamentado para a molécula ou a condição; a nota explica o motivo |

Fora da faixa de validade, o valor fica **indisponível**. Não há extrapolação.

## Fluxo

```
Desenho 2D ──► SMILES ──► RDKit (Mol) ──► perfil estrutural ──► propriedades ──► painel químico
                                                │
                                                └─► CMC + CPP ──► ambiente 3D (c/CMC, morfologia, motor CG)
```

- **Painel químico:** `POST /api/v1/chemistry/parameters/analyze` → [router.py](../backend/app/modules/chemistry/parameters/router.py). Esse arquivo monta a resposta e chama os provedores de [properties/](../backend/app/modules/chemistry/properties/) pelo [orchestrator.py](../backend/app/modules/chemistry/properties/orchestrator.py).
- **Cálculos compartilhados entre 2D e 3D:** [validated_calculations.py](../backend/app/modules/chemistry/parameters/validated_calculations.py). O painel e o ambiente 3D usam a mesma CMC, o mesmo HLB e o mesmo CPP.
- **Ambiente 3D:** [micelium/engine.py](../backend/app/modules/micelium/engine.py).

---

## 1. Perfil estrutural (base de tudo)

`validated_calculations.profile(mol)`

| Item | Como é obtido |
|---|---|
| **Fragmento ativo** | Entre os fragmentos do SMILES (ex.: `CCCC…OS(=O)(=O)[O-].[Na+]`), escolhe o de maior cauda de carbono; depois, o de mais carbonos e mais átomos pesados. Os demais viram contraíons. Fórmula e massa referem-se à entrada completa; os descritores, ao fragmento ativo. |
| **Cauda** | Maior caminho entre carbonos fora de anel e sem ligação dupla com heteroátomo (carbonila não conta). Calculado por duas buscas em largura (diâmetro exato da floresta). |
| **Linear** | Uma cauda ≥ 4 C, sem ramificação, sem anel, sem C=C e só com átomos H, C, N, O, S. |
| **Cabeça** | Primeiro padrão SMARTS que casar, nesta ordem: óxido de amina, zwitteriônica, sulfato, sulfonato, carboxilato, ácido carboxílico, fosfato, amônio quaternário, amina protonada, amina, amida, álcool/éter; senão, "polar" (TPSA ≥ 20 Å²) ou nenhuma. |
| **É surfactante?** | Cabeça polar (ou carga) **e** cauda ≥ 8 C (≥ 7 C para carboxilatos). Também conta um esqueleto rígido (≥ 3 anéis, ≥ 12 C) com TPSA ≥ 40. |
| **Mistura ambígua** | Se outro fragmento também tem cauda ≥ 6 C, trata-se de uma mistura, não de um sal. Nesse caso CMC, HLB e CPP ficam bloqueados. |
| **Classe** | [surfactant_class.py](../backend/app/modules/chemistry/properties/surfactant_class.py), por regras sobre os sítios ionizáveis (sem IA). Somente ácidos → aniônico. Carga + permanente → catiônico. Cátion permanente + ácido → zwitteriônico (e também anfotérico). Base + ácido → anfotérico. Cabeça polar sem grupo ionizável → não iônico. Uma cabeça fraca (um –OH, –COOH neutro ou amina neutra) recebe o papel "surfactante ou cossurfactante" e fica sem CMC. Pares + / − de ressonância (nitro, N-óxido) não contam como zwitteriônicos. |

## 2. Descritores diretos do RDKit (fragmento ativo)

São cálculos exatos ou descritores padronizados, sem ajuste:

- Massa molar, massa monoisotópica, fórmula, InChI/InChIKey (o PubChem é consultado como opcional, com timeout)
- **logP**: Crippen (`MolLogP`)
- TPSA, HBD/HBA (Lipinski), ligações rotacionáveis, anéis, anéis aromáticos, fração Csp³, QED, complexidade de Bertz, refratividade molar (Crippen MR), índices de Wiener e Randić
- Contagens de átomos, hidrogênios e ligações σ/π. As ligações π são contadas na forma de Kekulé: o pirrol tem 2 ligações π formais.

## 3. Ionização: pKa, carga no pH e LogD

[ionization.py](../backend/app/modules/chemistry/properties/ionization.py). Método: **tabela SMARTS de pKa de compostos-modelo + Henderson–Hasselbalch por sítio.**

| Grupo | pKa usado | Composto-modelo (CRC, 25 °C) |
|---|---|---|
| Ácido carboxílico | 4,76 | ácido acético |
| Fenol | 9,99 | fenol |
| Amina primária / secundária / terciária | 10,66 / 10,73 / 9,80 | metil-, dimetil-, trimetilamina |
| Anilina | 4,60 | anilina |
| Piridina / imidazol | 5,23 / 6,95 | — |
| N-óxido de amina | 4,65 | N-óxido de trimetilamina |
| Fosfato diéster | 1,29 | dimetil fosfato |
| Sulfônico / sulfato | só limite superior (pKa < 0) | ácido forte, sem valor numérico |
| Amônio quaternário, piridínio, fosfônio | — | carga permanente |

**Pares acoplados validados**, com os dois pKa medidos no mesmo composto:
- glicina: 2,34 / 9,60
- sarcosina: 2,21 / 10,1
- betaína: 1,83
- fosfato monoéster: forte / 6,3

Quando há outros sítios tituláveis a ≤ 7 ligações um do outro, a molécula é marcada como **acoplada**. Nesse caso carga, espécie e LogD ficam indisponíveis, porque presumir sítios independentes daria um resultado errado.

- **Fração protonada:** f = 1 / (1 + 10^(pH − pKa))
- **Carga líquida no pH:** soma das contribuições de cada sítio
- **LogD:** logP(forma neutra, Crippen) + log10(fração neutra). Fica indisponível para íons permanentes, ácidos fortes e anfotéricos (a forma neutra é ambígua).
- **Limites:** erro típico de ±1 unidade de pKa. O modelo não considera tautomeria, atividade iônica nem temperatura.

Para moléculas sem sítio ionizável, LogD = logP.

## 4. Solubilidade aquosa (LogS, ESOL)

`validated_calculations.esol_estimate`, equação de Delaney (2004):

```
LogS = 0,16 − 0,63·logP − 0,0062·MW + 0,066·RB − 0,74·AP
```

- RB = ligações rotacionáveis; AP = fração de átomos pesados aromáticos.
- O logP é o do Crippen/RDKit, não o CLOGP do artigo original, e não houve recalibração.
- Bloqueado para íons, radicais e MW > 1000.

## 5. HLB

`validated_calculations.hlb_values`

- **Davies (contribuição de grupos):** HLB = 7 + Σ(grupos hidrofílicos) − 0,475 × (nº de CH/CH₂/CH₃).
  - Grupos: sulfato 38,7; carboxilato Na 19,1 (K 21,1); COOH 2,1; –OH 1,9; éter 1,3.
  - Só vale para cauda linear com cabeça sulfato, carboxilato, COOH ou álcool/éter, com contraíon Na⁺/K⁺ conferido.
  - Exemplo: SDS → **40**.
- **Griffin E/5:** HLB = 20 × (massa das unidades de óxido de etileno / massa da molécula). Vale só para álcool etoxilado linear CnEm. Exemplo: C12E6 → 11,7.
- Quando as duas se aplicam, prevalece Griffin. Não há conversão entre as escalas.
- Amônio quaternário e zwitteriônicos ficam sem HLB, porque não há valor de grupo verificado.

## 6. CMC

### 6.1 Âncoras SDS/CTAB (homólogos de Klevens)

`validated_calculations.cmc_estimate`, para alquilsulfato de sódio e brometo de alquiltrimetilamônio lineares, C8–C18:

```
CMC_ref = CMC_âncora · 10^(inclinação · (n_âncora − n))       [mmol/L]
CMC     = CMC_ref / (1 + k_sal · I)
```

| Família | Âncora | Inclinação por C | k_sal |
|---|---|---|---|
| Alquilsulfato de sódio | SDS, n = 12, 8,2 mM | 0,31 | 5,8 |
| Brometo de alquiltrimetilamônio | CTAB, n = 16, 0,92 mM | 0,30 | 4,4 |

- **Domínio:** água, 20–25 °C, força iônica I ≤ 0,1 mol/L.
- A correção salina é empírica e não foi calibrada.
- SDS a I = 0,01 mol/L → 7,75 mmol/L.
- Em relação ao NIST, o erro é de no máximo 0,05 em log10.

### 6.2 CMC por família (NSRDS-NBS 36, NIST)

[cmc_correlations.py](../backend/app/modules/chemistry/properties/cmc_correlations.py). Ajuste por mínimos quadrados aos dados medidos em água pura a 20–30 °C ([dados](../backend/app/modules/chemistry/properties/data/cmc_homologs.json)):

```
log10(CMC / mol·L⁻¹) = a + b·n   (+ c·m para etoxilados CnEm)
```

| Família | a | b | c | Faixa |
|---|---|---|---|---|
| Alcanossulfonato de sódio | 1,6049 | −0,2998 | — | n 8–12 |
| Cloreto de alquiltrimetilamônio | 1,6551 | −0,2839 | — | n 10–14 |
| Cloreto de alquilpiridínio | 1,7462 | −0,2986 | — | n 12–18 |
| Alquil β-D-glicosídeo | 2,6377 | −0,5298 | — | n 8–12 |
| Álcool etoxilado CnEm | 1,6246 | −0,4805 | 0,0340 | n 6–16, m 3–21 |

- A família é reconhecida por **igualdade exata de SMILES** com o modelo da família. No glicosídeo, a estereoquímica importa.
- **Validação:** cada ponto é deixado de fora uma vez e previsto pelos demais (leave-one-out). Erro máximo ≤ 0,3 em log10 → `estimated`; entre 0,3 e 0,5 → `low`; acima de 0,5 → família excluída.
- **Domínio:** água, 20–30 °C, dentro da faixa de n/m da família. Famílias iônicas: I ≤ 0,01 mol/L. Não iônicas: I ≤ 0,1 mol/L, com o efeito do sal desprezado.
- **Sem CMC:** carboxilatos, óxidos de amina, alquilbenzenossulfonatos, brometos de piridínio, betaínas e sulfobetaínas, porque não há dados suficientes. Por isso a betaína não forma micela no 3D.

### 6.3 CMC experimental

Quando o composto exato está na tabela do NIST, o painel mostra também o valor medido (`cmc_experimental`), com temperatura, método, referência e página. O campo `cmc_origem` informa de onde veio o número: medido (experimental), correlação ajustada a dados (calculada) ou âncora com correção empírica (estimada).

## 7. Teoria micelar

[micelle_theory.py](../backend/app/modules/chemistry/properties/micelle_theory.py) e `validated_calculations.packing_estimate`. Vale só para surfactantes com **uma cauda hidrocarbonada linear**.

| Grandeza | Fórmula | Observação |
|---|---|---|
| Comprimento da cauda (Tanford) | l_max = 1,5 + 1,265·n Å | cadeia estendida, ~25 °C |
| Volume da cauda (Tanford) | v = 27,4 + 26,9·n Å³ | — |
| Área da cabeça a₀ | 72 Å² (iônico), 56 (zwitteriônico), 60 (não iônico) | **valor fixo por classe, não medido** |
| **CPP** | v / (a₀ · l_max) | < 1/3 esfera; 1/3–1/2 cilindro; 1/2–1 bicamada; ≥ 1 inversa |
| N_agg máximo da esfera | (4/3)·π·l_max³ / v | limite geométrico, **não** é o número de agregação |
| Raio do núcleo / do cilindro | = l_max, escolhido pelo CPP | só para iônicos; não iônicos e zwitteriônicos ficam indisponíveis |
| ΔG de micelização | RT·ln X_cmc, X = c / (55,5 + c) | só para não iônicos (iônicos precisariam de β) |
| Comprimento de Debye | κ⁻¹ = √(ε·ε₀·k_B·T / (2·N_A·e²·1000·I)) | só para 0 < I ≤ 0,1 mol/L |

Ficam indisponíveis, porque não há referência verificada: N_agg real, β (contraíons ligados), espessura da cabeça e raio total.

## 8. Geometria 3D e propriedades eletrônicas (sob demanda)

| Campo | Método | Confiança |
|---|---|---|
| Coordenadas, raio de giração, NPR, volume, SASA, superfície vdW, energia | ETKDGv3 + MMFF94, um confórmero por fragmento, em fase gasosa ([conformer3d.py](../backend/app/modules/chemistry/properties/conformer3d.py)). Sem parâmetros MMFF, o campo fica indisponível (não há troca automática para UFF). | medium |
| Momento dipolar | cargas MMFF94 × coordenadas; indisponível para íons | low |
| Carga de Gasteiger | equalização empírica de eletronegatividade | low |
| Pares livres, VSEPR, R/S | contagem de Lewis, número estérico, regras CIP ([electronic_basic.py](../backend/app/modules/chemistry/properties/electronic_basic.py)) | high |
| Ressonância | `ResonanceMolSupplier` (≤ 64 estruturas), carga por átomo como faixa mín./máx. ([resonance.py](../backend/app/modules/chemistry/properties/resonance.py)) | high |

## 9. Ambiente 3D (micelização)

### 9.1 c/CMC da mistura (Clint, mistura ideal)

`engine.calculate_micellization_metrics`

```
c/CMC = Σ cᵢ / CMCᵢ
quantidade crítica = quantidade total / (c/CMC)
excesso = quantidade total − quantidade crítica
```

- Usa a CMC já avaliada para o ambiente, aplicada uma única vez.
- Agitação, volume desenhado, velocidade visual e número de partículas **não** entram na CMC.
- Se algum surfactante não tem CMC, o total fica indisponível. O c/CMC parcial serve só para a visualização e é rotulado como aproximação.

### 9.2 Escolha da morfologia

`engine.choose_formation_plan`

1. **CPP base:** média dos CPP dos surfactantes com CMC válida, ponderada pela concentração.
2. **CPP efetivo**, corrigido pelo meio. Estes ajustes são heurísticas visuais, não calibradas:
   - sal: até +0,10, proporcional à fração de surfactantes iônicos;
   - meio pouco polar: até +0,12;
   - constante dielétrica baixa (< 25): até +0,08.
3. **Fase**, pelo c/CMC:

| c/CMC | Fase |
|---|---|
| < 1 | monômeros dispersos / contatos transitórios |
| 1–1,2 | pré-agregados |
| 1,2–1,6 | nucleação |
| 1,6–2,5 | autoagregação crescente |
| 2,5–4 | micelização estabelecida |
| > 4 | domínio agregado estável |

4. **Forma**, pelos limiares de Israelachvili–Mitchell–Ninham sobre o CPP efetivo:
   - < 0,33: micela esférica;
   - < 0,50: micela cilíndrica / wormlike;
   - < 0,85: cilindro curto, bicamada ou vesícula, conforme a concentração e o número de moléculas;
   - < 1: bicamada / lamelar;
   - ≥ 1, ou meio apolar: micela inversa.
   - Sem CPP conhecido, o agregado aparece **sem forma prevista**.

### 9.3 Motor CG (visualização)

O movimento das partículas usa forças mesoscópicas qualitativas:
- molas de ligação;
- atração entre caudas;
- Coulomb blindado com κ⁻¹ ≈ 0,304 / √I nm, limitado a 8 nm;
- ruído browniano proporcional a √(T / 298 K);
- campo de organização dos clusters ([organization.py](../backend/app/modules/micelium/organization.py)).

**Não é dinâmica molecular:** tempo, forças e raios estão em unidades CG e não são calibrados.

### 9.4 Exemplos documentados

[documented_examples.py](../backend/app/modules/micelium/documented_examples.py) traz cinco cenários com condições tiradas da literatura:
- SDS esférica;
- CTAB + salicilato vermiforme;
- DPPC bicamada;
- DPPC vesícula;
- AOT inversa em isooctano.

Só o **SDS** é previsão do motor. Nos outros quatro a forma vem do catálogo, e as forças extras de [documented_example_forces.py](../backend/app/modules/micelium/documented_example_forces.py) são apenas guias visuais.

## 10. O que fica indisponível de propósito

Estes campos não têm método fundamentado na v1 e aparecem como indisponíveis, com justificativa:
- HOMO, LUMO, gap, IP/EA;
- calor de formação;
- densidade, pontos de fusão e de ebulição, pressão de vapor, tensão superficial, viscosidade;
- energia de solvatação, HLD, NAC;
- N_agg real e β.

A etapa 2 prevê xTB, MOPAC e Joback validado.

## 11. Código legado removido

`calculation_page.py`, `miriam21_engine.py` e `miriam21_acceptance_check.py` guardavam as fórmulas antigas (densidade, ponto de ebulição e orbitais por proxy), desativadas na correção de 04/11/2026. Como não eram importados pelo painel ativo, foram removidos em 14/11/2026 e continuam no histórico do Git. A rota `/status` ainda os lista como `installed: false`.
