# Correção e validação dos cálculos moleculares 2D/3D

> **Registro histórico (04/11/2026).** A correção descrita aqui já está aplicada no código; o aplicador e o pacote de evidências foram removidos do repositório (continuam no histórico do Git). Parte do texto foi superada depois, como a CMC automática, que hoje é calculada por família (ver `WEB_LITE_V1.md`, seção 4). O resumo atual dos métodos está em `documentacao/CALCULOS.md`.

Data: 04/11/2026. Base: projeto completo enviado, com as correções anteriores dos atalhos e da geometria CG. Foram preparados **27 arquivos atualizados/criados**, sem migração de banco nem substituição da aplicação.

**Resultado: 1.262 testes funcionais aprovados, sem falhas ou testes ignorados.** Mais 14 testes do aplicador foram aprovados. O frontend compilou com sucesso. Os testes comprovam as propriedades verificadas do código e sua consistência; não certificam a precisão experimental de toda predição.

## O que foi corrigido

| Problema encontrado | Comportamento após a correção |
| --- | --- |
| CMC e HLB distintos entre painel 2D e predição/ambiente 3D | Identidade, domínio de aplicação, CMC, HLB e CPP usam cálculos compartilhados. Diferenças residuais de apresentação ficam limitadas ao arredondamento do painel. |
| Hexano e outros não surfactantes recebiam CMC | CMC indisponível quando a estrutura ou o meio estão fora do domínio suportado. |
| HLB iônico reescalado ou truncado em 20 | HLB de Davies mantém sua escala, com método explícito. SDS retorna 40, sem converter esse resultado para a escala de Griffin. |
| HLB de Griffin calculado só com a massa de heteroátomos | Para álcoois etoxilados lineares compatíveis, usa-se E/5, com a fração mássica das unidades de óxido de etileno. Outros domínios não recebem essa fórmula automaticamente. |
| CMC corrigida novamente pelo motor CG | CMC já fornecida para o ambiente é usada uma única vez. Valores manuais não recebem um segundo fator de solvente/sal. |
| Agitação alterava a CMC de equilíbrio | Agitação, volume, velocidade visual e contagem de partículas não entram na CMC de equilíbrio. Podem afetar a visualização/organização CG. |
| Ácidos neutros tratados como ânions; amidas recebendo pKa de amina | Classe respeita as cargas formais da estrutura. Pares de carga por ressonância em nitro/N-óxidos não criam uma classe zwitteriônica. pKa por família só aparece nos sítios monopróticos suportados. Betaínas e íons permanentes não recebem um pKa genérico. |
| LogD de ácidos/bases com limites artificiais | Henderson–Hasselbalch usa o logP da forma neutra e não aplica o corte arbitrário anterior. pKa continua sendo aproximação por família. |
| ESOL usava número de anéis aromáticos | Usa fração de átomos pesados aromáticos. A versão com descritores RDKit é identificada e não recebe o bônus arbitrário de solubilidade para íons. |
| Fragmento ativo escolhido pelo tamanho do texto SMILES | Seleção por grafo/cauda; contraíons orgânicos são separados. Fórmula e massa referem-se à entrada completa; descritores indicam explicitamente o fragmento ativo. |
| Tamanho de componente ramificado confundido com comprimento da cauda | Conta o caminho de carbono; carbonila e carbonos em anel não entram na cauda linear. Número de caudas e domínios complexos são tratados separadamente. |
| Orbitais, dipolo e propriedades físicas calculados por fórmulas arbitrárias | HOMO, LUMO, gap, IP/EA, dipolo, densidade, temperaturas de mudança de fase, viscosidade, energias e outros campos sem cálculo correspondente ficam indisponíveis, com justificativa. |
| Massa atômica média chamada de massa exata | Massa isotópica/monoisotópica correta; massa média fica em campo separado. |
| Cada ligação aromática contada como meia ligação π | Contagem formal de ligações π pela representação de Kekulé. Pirrol, por exemplo, possui 2 ligações π formais; isso não é contagem dos elétrons π do anel. |
| Comprimento de ligação igual para ordens diferentes | Sem conformação otimizada, não se apresenta a soma de raios covalentes como comprimento da ligação calculado. |
| CMC da mistura e propriedades ponderadas pelos desenhos | Clint usa frações molares reais. LogP, pKa, orbitais e geometria não recebem médias pela quantidade visual. Uma mistura com dados necessários ausentes não é reduzida silenciosamente ao subconjunto conhecido. |
| Unidades ignoradas no painel da solução | Conversões explícitas nm↔Å, kJ/mol↔kcal/mol e mol/L↔mmol/L; unidades desconhecidas não são simplesmente trocadas no rótulo. |
| Snapshots antigos duplicados; valores antigos substituindo indisponibilidade atual | Usa um único snapshot da composição atual; resultado atual indisponível prevalece. Limpar a mistura não recupera registros antigos. |
| Quantidade e concentração contraditórias | Entrada do backend é rejeitada. No frontend, quantidade em mmol é preservada e concentração é recalculada quando o volume muda. Concentração zero permanece zero. |
| NaN/Infinity e modelos inválidos | Entradas não finitas são rejeitadas; previsões de CMC não finitas/não positivas e arquivos de modelo corrompidos não são aceitos como resultados válidos. |
| Validação física sempre marcada como aprovada | Resposta declara ausência de validação experimental. Índice micelar deixa de ser apresentado como porcentagem de probabilidade calibrada. |

## Exemplos verificáveis

Condições padrão do aplicativo: 298,15 K, água e força iônica de 0,01 mol/L. A correção salina abaixo é uma estimativa empírica, não uma nova medição.

| Caso | Antes, 2D / IA do 3D | Depois, 2D / IA do 3D |
| --- | --- | --- |
| SDS — CMC, mmol/L | 8,40073 / 7,75047, com fator adicional no motor | 7,75047 / 7,75047; sem segunda correção no motor |
| SDS — HLB | 16,8 / 20 | 40 / 40, método de Davies |
| CTAB — CMC, mmol/L | 0,44088 / 0,87357 | 0,88123 / 0,88123 |
| C12E6 — HLB | 4,97021 / 13,23756 | 11,73034 / 11,73034, E/5 |
| Hexano — CMC, mmol/L | 190,54607 / indisponível | Indisponível em ambos |
| Acetamida — pKa | 9,8 | Indisponível: não é uma amina comum |
| Anilina — pKa | 9,8 | 4,6 como estimativa por família, não como valor experimental validado |
| Água — ebulição | 74,9914 °C, por proxy | Indisponível nesse cálculo; não se inventa um valor a partir de descritores |
| SDS — CPP | Métodos/áreas diferentes | Aproximadamente 0,29160 em ambos; área CG não calibrada |

## Testes executados

Cada linha parametrizada conta como um caso de teste. Não são 1262 moléculas diferentes nem 1262 experimentos.

| Grupo | Casos aprovados |
| --- | ---: |
| 151 atalhos: composição, carga, hidrogênios e inventário de ligações | 151 |
| 151 atalhos: identidade, descritores, CMC/HLB/CPP entre 2D e IA | 151 |
| 151 atalhos: JSON finito, indisponibilidade e ausência de aprovação física falsa | 151 |
| 151 atalhos: caminho de compatibilidade RDKit 2D e painel | 151 |
| 151 atalhos: gerador 2D ativo, SVG e grafo interno | 151 |
| Outros cálculos: fórmulas contadas manualmente, massas, isótopos, π, caudas, unidades, pH, modelos, limites e mistura | 421 |
| Rotas HTTP reais de desenho 2D, parâmetros, IA e simulação CG | 17 |
| Regressões das coordenadas CG e geometria | 24 |
| Interface: quantidades, unidades, Clint e armazenamento da mistura | 45 |
| **Total funcional** | **1262** |
| Aplicador: simulação sem escrita, instalação, cópia de segurança, idempotência, conflitos, CRLF, permissões, links e restauração após falha | **14 adicionais** |

As regressões de geometria verificam organização nas coordenadas, restrição de ligações, discriminação de agregados aleatórios, regimes abaixo da CMC e cenários de micela esférica, cilíndrica, bicamada e micela inversa. Isso não confirma que toda molécula real formará a fase exibida.

A comparação usa tolerância numérica compatível com o arredondamento de cinco casas do painel; não exige igualdade binária entre, por exemplo, 350,2 e 350,19999999999993.

## Limitações que permanecem

- **CMC automática:** correlação de homólogos lineares de alquilsulfatos de sódio e brometos de alquiltrimetilamônio, com C8–C18, em água entre 20–25 °C e força iônica até 0,1 mol/L. As âncoras são SDS e CTAB; a inclinação de homólogos e a correção salina são hipóteses empíricas, não calibração nova com dados independentes. A faixa aceita pelo código não comprova a mesma precisão em todos os pontos; transições de Krafft e fases cristalinas não foram modeladas. Outros solventes/famílias exigem dados ou modelos adequados.
- **HLB:** a escala depende do método. Não existe conversão universal de Davies para Griffin. Misturas comerciais como Tween e biossurfactantes complexos não devem receber uma fórmula de estrutura simples como se fossem substâncias monodispersas.
- **pH:** a classe descreve as cargas formais do SMILES recebido. O pKa por família e o LogD monoprótico não representam um cálculo completo de especiação, tautomeria ou atividade iônica.
- **ESOL/logP:** são descritores/estimativas com domínio e erro próprios. A equação ESOL original foi ajustada com CLOGP; substituir por Crippen/RDKit sem recalibrar não equivale a reproduzir a precisão experimental do artigo. Sais, radicais e estruturas com massa acima de 1000 g/mol são bloqueados para ESOL nesta implementação.
- **CPP e 3D:** Tanford usa uma cauda hidrocarbonada linear. A área de cabeça é um parâmetro não calibrado do modelo CG. Forças, tempo, índices, raios e tendências de agregação não são uma validação atomística/experimental. Caudas múltiplas, ramificações, fluorados e arquiteturas complexas não herdam automaticamente o cálculo de uma cauda linear.
- **IA treinada:** o material recebido não trouxe pesos `.joblib` utilizáveis. Os testes de estimadores simulados verificam carregamento, rejeição de resultados inválidos e identificação de origem; não avaliam a acurácia de um modelo treinado real. Os índices de confiança não são probabilidades estatisticamente calibradas.
- **Escopo executado:** rotas ativas do painel químico, desenho 2D, IA e ambiente CG. Não houve validação de força de campo do runner OpenMM opcional, comparação com DFT/xTB, ensaio experimental, banco PostgreSQL real ou disponibilidade da consulta externa ao PubChem. A consulta externa passou a ser opcional e não troca silenciosamente o método dos descritores locais.
- As faixas de SDS/CTAB usadas nos testes são **âncoras de referência**, não um conjunto independente de validação preditiva. Nenhuma métrica de RMSE, MAE ou precisão experimental global foi inventada.

## Como repetir os testes

Com o ambiente Python do backend ativado e as dependências do projeto instaladas:

```bash
cd backend
python -m pip install pytest httpx
python -m pytest tests app/modules/micelium/test_organization_geometry.py -q
```

Na pasta `frontend`, com as dependências de desenvolvimento instaladas:

```bash
npx vitest run --environment jsdom
npm run build
```

A duração observada das regressões geométricas foi de alguns minutos; pode variar conforme o computador.

Ambiente testado: Python 3.12.14, RDKit 2026.9.1, NumPy 2.5.4, Pydantic 2.14.2, FastAPI 0.162.0, pytest 9.2.0. O build apresentou somente o aviso de tamanho de bundle; os testes HTTP apresentaram um aviso de depreciação do TestClient/httpx. Não houve falha de teste ou compilação nas rodadas finais.

## Fontes técnicas consultadas

1. [RDKit — documentação oficial](https://www.rdkit.org/docs/GettingStartedInPython.html) e [Crippen](https://www.rdkit.org/docs/source/rdkit.Chem.Crippen.html): descritores e escopo de cálculo.
2. [Delaney, 2004 — ESOL, DOI 10.1021/ci034243x](https://doi.org/10.1021/ci034243x). Equação e definição da proporção aromática; [cópia do artigo](https://www.moreisdifferent.com/assets/DIY_drug_discovery/Delaney_paper.pdf).
3. [Davies, 1957 — artigo original e tabela de grupos HLB](https://es.firp-ula.org/wp-content/uploads/2019/07/57_Chap_Davies.pdf). A tabela não fornece uma conversão universal para a escala de Griffin.
4. [Sigma-Aldrich 71729 — SDS](https://b2b.sigmaaldrich.com/US/en/product/sigma/71729): CMC de 7–10 mM a 20–25 °C e HLB 40.
5. [Sigma-Aldrich H6269 — CTAB](https://b2b.sigmaaldrich.com/US/en/product/sigma/h6269): CMC de 0,92–1 mM a 20–25 °C. O HLB 10 listado na ficha é uma referência comercial cujo método não foi atribuído automaticamente à fórmula de Davies.

## Arquivos do pacote de correção

| Caminho relativo ao projeto | Ação |
| --- | --- |
| `backend/app/modules/chemistry/parameters/calculation_page.py` | Atualizado |
| `backend/app/modules/chemistry/parameters/router.py` | Atualizado |
| `backend/app/modules/chemistry/parameters/schemas.py` | Atualizado |
| `backend/app/modules/chemistry/parameters/service.py` | Atualizado |
| `backend/app/modules/chemistry/parameters/validated_calculations.py` | Criado |
| `backend/app/modules/chemistry/rdkit_service.py` | Atualizado |
| `backend/app/modules/micelium/IA/constants.py` | Atualizado |
| `backend/app/modules/micelium/IA/feature_builder.py` | Atualizado |
| `backend/app/modules/micelium/IA/model_registry.py` | Atualizado |
| `backend/app/modules/micelium/IA/molecular_identity_ai.py` | Atualizado |
| `backend/app/modules/micelium/IA/prediction_service.py` | Atualizado |
| `backend/app/modules/micelium/IA/routes.py` | Atualizado |
| `backend/app/modules/micelium/IA/schemas.py` | Atualizado |
| `backend/app/modules/micelium/IA/specialized_base.py` | Atualizado |
| `backend/app/modules/micelium/ai_bridge.py` | Atualizado |
| `backend/app/modules/micelium/engine.py` | Atualizado |
| `backend/app/modules/micelium/schemas.py` | Atualizado |
| `backend/tests/fixtures/molecular_catalog.json` | Criado |
| `backend/tests/test_calculation_consistency.py` | Criado |
| `backend/tests/test_calculation_http.py` | Criado |
| `frontend/src/pages/2dpage/components/interaction/MoleculePropertiesPanel.tsx` | Atualizado |
| `frontend/src/pages/3dpage/3dpage.micelium.test.ts` | Atualizado |
| `frontend/src/pages/3dpage/3dpage.tsx` | Atualizado |
| `frontend/src/pages/3dpage/realQuantities.test.ts` | Criado |
| `frontend/src/pages/3dpage/realQuantities.ts` | Criado |
| `frontend/src/pages/3leftpage/3Leftpage.calculations.test.ts` | Criado |
| `frontend/src/pages/3leftpage/3Leftpage.tsx` | Atualizado |
