# Auditoria dos 151 atalhos moleculares

Data: 4 de novembro de 2026.

## Resultado

Foram revisados os 151 registros do catálogo de moléculas rápidas. Todos os SMILES originais eram interpretáveis pelo RDKit e as fórmulas eram compatíveis com esses próprios desenhos. Isso não comprovava que o desenho representasse a identidade química sugerida pelo nome.

A revisão alterou 10 conectividades e suas fórmulas, definiu a estereoquímica em 10 outras estruturas e refinou nomes, descrições ou categorias em mais 40 entradas. As outras 91 entradas foram mantidas. Todos os 151 IDs e sua ordem foram preservados.

O principal problema de valência estava na entrada cocoamphoacetate-simplified: [NH+] com dois substituintes e apenas um hidrogênio produzia um radical nitrogenado. O substituto de referência adota a cadeia aberta N-acilada C12 descrita abaixo, com amina terciária não protonada, carboxilato e sódio.

## Validação executada

| Verificação | Resultado |
| --- | --- |
| SMILES sanitizados | 151 aprovados |
| Fórmulas comparadas por contagem elementar | 151 aprovados |
| Ausência de radicais não intencionais | 151 aprovados |
| Cargas totais conforme espécie nomeada | 151 aprovados |
| Importação pelo serviço 2D e geração de SVG | 151 aprovados |
| Série de sais aniônicos | 21 aprovados |
| Homólogos de álcool etoxilado | 24 aprovados |
| Glicosídeos β-D com cinco centros definidos | 6 aprovados |
| Modelos completos de sorbitano EO20 | 2 aprovados |
| Identidades verificadas por InChIKey de referência | 10 aprovados |

Também foi conferida a surfactina com sete ligações amida e macrociclo de 25 átomos. A compilação de produção da interface passou. A busca por Triton, Tween 80 e surfactina, a seleção dos cartões, o filtro de seis cotensoativos e o de três biossurfactantes foram exercitados em DOM.

A correspondência de nome foi revisada pela conectividade, grupos funcionais e séries homólogas. Dez identidades complexas ou estereoquimicamente específicas foram comparadas por InChIKey com registros públicos. Não foram obtidas certificações analíticas ou números CAS individuais para todos os homólogos sintéticos.

## Substituições de estruturas

| Atalho anterior | Estrutura adotada | Fórmula anterior → atual | Motivo |
| --- | --- | --- | --- |
| Triton X-100 — modelo reduzido de alquilfenol etoxilado EO3 | 4-terc-octilfenol EO10 — homólogo de referência | C16H26O4 → C34H62O11 | Substitui o tert-butilfenol EO3 por tert-octilfenol EO10, com a ramificação C8 correta. |
| Nonoxinol-9 — modelo reduzido de nonilfenol etoxilado EO4 | 4-n-nonilfenol EO9 — referência de nonoxinol-9 | C23H40O5 → C33H60O10 | Corrige EO4 para EO9; mantém o isômero com cadeia n-nonil explicitamente definido. |
| Span 20 — fragmento linear tipo sorbitan monolaurato | Monolaurato de 1,4-sorbitano — referência do Span 20 | C17H34O6 → C18H34O6 | Substitui o éster de pentitol C17 pelo monoéster cíclico de sorbitano C18. |
| Span 80 — fragmento linear tipo sorbitan monooleato | Monooleato de 1,4-sorbitano (9Z) — referência do Span 80 | C23H44O6 → C24H44O6 | Substitui o éster linear C23 pelo monooleato cíclico C24, com dupla 9Z. |
| Tween 20 — fragmento laurato-PEG4 simplificado | Polissorbato 20 — modelo molecular EO20 (5/5/5/5) | C20H40O6 → C58H114O26 | Substitui o simples éster de PEG4 por sorbitano completo com vinte EO em quatro braços 5/5/5/5, distribuição explicitamente assumida. |
| Tween 80 — fragmento oleato-PEG4 simplificado | Polissorbato 80 — modelo molecular EO20 (5/5/5/5) | C26H50O6 → C64H124O26 | Substitui o simples éster de PEG4 por sorbitano completo com vinte EO em quatro braços 5/5/5/5, distribuição explicitamente assumida. |
| Lauroamfoacetato — representação zwitteriônica simplificada | Lauroamfoacetato de sódio — homólogo C12 de cadeia aberta | C16H31N2O3 → C18H35N2NaO4 | Remove o radical nitrogenado não intencional e substitui o fragmento por um homólogo C12 de cadeia aberta, com hidroxietil, carboxilato e sódio. |
| Ramnolipídeo mono — modelo simplificado | Monorramnolipídeo Rha-C10-C10 — forma ácida de referência | C25H46O9 → C26H48O9 | Substitui o fragmento C25 pela conectividade completa Rha-C10-C10 C26, mantendo apenas a estereoquímica explicitada pelo registro de referência. |
| Soforolipídeo — fragmento glicolipídico simplificado | Soforolipídeo ácido diacetilado — referência 9E | C23H42O7 → C34H58O15 | Substitui o monoglicosídeo C23 pelo soforolipídeo completo C34, com dois açúcares, duas acetilações e isomeria 9E explicitada. |
| Surfactina — fragmento lipopeptídico simplificado | Surfactina C — lipo-heptapeptídeo cíclico completo | C16H30N2O4 → C53H93N7O13 | Substitui o pequeno dipeptídeo C16 pelo lipo-heptapeptídeo cíclico completo de surfactina C, C53H93N7O13. |

## Definições de estereoquímica

- Oleato de sódio: dupla 9Z; linoleato de sódio: duplas 9Z,12Z.
- Seis alquil glicosídeos: representantes β-D-glucopiranosídeos, com cinco centros definidos.
- DPPC: configuração sn do glicerol explicitada a partir do CID 452110.
- Ramnose: α-L-ramnopiranose, classificada como açúcar orgânico de referência.

## Misturas, homólogos e modelos declarados

Produtos comerciais podem reunir comprimentos de cadeia, graus de etoxilação e isômeros diferentes. A fórmula exibida no atalho refere-se à espécie ou ao modelo molecular declarado.

- Triton X-100: representante de terc-octilfenol EO10, com a cadeia C8 ramificada correta; o produto comercial tem distribuição de EO.
- Nonoxinol-9: isômero para com cadeia n-nonil e nove EO, conforme o registro de referência.
- Polissorbatos 20 e 80: modelos completos de monoéster de sorbitano com vinte EO. A distribuição de cinco EO em cada um dos quatro braços foi escolhida para o modelo, a partir da descrição nominal da JECFA; não é uma composição comercial medida nem um SMILES único do produto.
- Span 20 e Span 80: monoésteres cíclicos completos de 1,4-sorbitano, com o isômero de referência identificado.
- Álcoois etoxilados: homólogos discretos CnEOm. Um nome INCI pode representar uma distribuição comercial.
- Cocamidas e cocamidopropil betaína: os homólogos lauroil C12 são identificados como tais.
- Cocoamfoacetato: homólogo lauroil C12 de cadeia aberta, derivado da definição estrutural N-acilada do Health Canada; foi declarada a forma de sal com amina não protonada.
- Poloxâmero: oligômero de blocos EO2–PO2–EO1; configuração R/S dos centros de PO não especificada.
- Octametiltrissiloxano: composto MDM discreto, usado como referência siloxânica.
- Silicone-poliéter: modelo de dissiloxano com éter de dietilenoglicol; preserva a ligação Si–O–C efetivamente desenhada.

## Estereoquímica parcial preservada e declarada

O monorramnolipídeo corresponde ao registro CID 162246: α-L-ramnose definida e dois centros β das caudas sem configuração R/S especificada. O soforolipídeo corresponde ao registro CID 11856871: forma ácida diacetilada com dupla 9E e configuração de C17 não especificada. A escolha do registro 9E foi explicitada no título; outras variantes, incluindo 9Z e formas lactônicas, são compostos diferentes.

AOT continua sem atribuição R/S, compatível com um nome sem estereodescritores e com misturas de estereoisômeros. Não foi acrescentada uma configuração absoluta sem fonte.

## Catálogo completo após a revisão

Coerente significa compatibilidade de nome, espécie e desenho dentro da definição declarada. Homólogos e modelos não recebem validação experimental de propriedades ou CMC nesta auditoria.

### Comuns

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 1 | Água | H2O | Coerente; mantido |
| 2 | Amônia | NH3 | Coerente; mantido |
| 3 | Íon amônio | NH4+ | Coerente; mantido |

### Ácidos e bases

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 4 | Íon hidróxido | OH- | Coerente; mantido |
| 5 | Íon acetato | C2H3O2- | Coerente; mantido |
| 6 | Ácido acético | C2H4O2 | Coerente; mantido |

### Solventes

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 7 | Etanol | C2H6O | Coerente; mantido |
| 8 | Acetona | C3H6O | Coerente; mantido |

### Orgânicos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 9 | Benzeno | C6H6 | Coerente; mantido |
| 10 | Fenol | C6H6O | Coerente; mantido |
| 11 | Anilina | C6H7N | Coerente; mantido |
| 143 | α-L-ramnopiranose | C6H12O5 | Estereoquímica definida |

### Surfactantes aniônicos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 12 | Hexil sulfato de sódio | C6H13NaO4S | Coerente; mantido |
| 13 | Hexano-1-sulfonato de sódio | C6H13NaO3S | Coerente; mantido |
| 14 | Hexanoato de sódio | C6H11NaO2 | Coerente; mantido |
| 15 | Octil sulfato de sódio | C8H17NaO4S | Coerente; mantido |
| 16 | Octano-1-sulfonato de sódio | C8H17NaO3S | Coerente; mantido |
| 17 | Octanoato de sódio | C8H15NaO2 | Coerente; mantido |
| 18 | Decil sulfato de sódio | C10H21NaO4S | Coerente; mantido |
| 19 | Decano-1-sulfonato de sódio | C10H21NaO3S | Coerente; mantido |
| 20 | Decanoato de sódio | C10H19NaO2 | Coerente; mantido |
| 21 | Dodecil sulfato de sódio | C12H25NaO4S | Coerente; mantido |
| 22 | Dodecano-1-sulfonato de sódio | C12H25NaO3S | Coerente; mantido |
| 23 | Dodecanoato de sódio / laurato de sódio | C12H23NaO2 | Coerente; mantido |
| 24 | Tetradecil sulfato de sódio | C14H29NaO4S | Coerente; mantido |
| 25 | Tetradecano-1-sulfonato de sódio | C14H29NaO3S | Coerente; mantido |
| 26 | Tetradecanoato de sódio / miristato de sódio | C14H27NaO2 | Coerente; mantido |
| 27 | Hexadecil sulfato de sódio | C16H33NaO4S | Coerente; mantido |
| 28 | Hexadecano-1-sulfonato de sódio | C16H33NaO3S | Coerente; mantido |
| 29 | Hexadecanoato de sódio / palmitato de sódio | C16H31NaO2 | Coerente; mantido |
| 30 | Octadecil sulfato de sódio | C18H37NaO4S | Coerente; mantido |
| 31 | Octadecano-1-sulfonato de sódio | C18H37NaO3S | Coerente; mantido |
| 32 | Octadecanoato de sódio / estearato de sódio | C18H35NaO2 | Coerente; mantido |
| 33 | SDS / SLS — dodecil sulfato de sódio | C12H25NaO4S | Coerente; mantido |
| 34 | SLES EO1 — lauril éter sulfato de sódio | C14H29NaO5S | Coerente; mantido |
| 35 | SLES EO2 — lauril éter sulfato de sódio | C16H33NaO6S | Coerente; mantido |
| 36 | 4-n-dodecilbenzenossulfonato de sódio — isômero de referência | C18H29NaO3S | Identificação refinada |
| 39 | Lauroil isetionato de sódio — homólogo C12 | C14H27NaO5S | Identificação refinada |
| 40 | Lauroil sarcosinato de sódio | C15H28NNaO3 | Coerente; mantido |
| 41 | Metil lauroil taurato de sódio | C15H30NNaO4S | Coerente; mantido |
| 42 | Lauril sulfoacetato de sódio | C14H27NaO5S | Coerente; mantido |
| 43 | Lauril fosfato de sódio | C12H26NaO4P | Coerente; mantido |
| 44 | AOT / docusato de sódio — bis(2-etilhexil) sulfosuccinato de sódio | C20H37NaO7S | Coerente; mantido |
| 45 | Oleato de sódio — 9Z (cis) | C18H33NaO2 | Estereoquímica definida |
| 46 | Linoleato de sódio — 9Z,12Z (cis,cis) | C18H31NaO2 | Estereoquímica definida |

### Hidrótropos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 37 | p-toluenossulfonato de sódio | C7H7NaO3S | Identificação refinada |
| 38 | 2,4-dimetilbenzenossulfonato de sódio — isômero de xilenossulfonato | C8H9NaO3S | Identificação refinada |

### Surfactantes catiônicos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 47 | OTAB — brometo de octiltrimetilamônio | C11H26BrN | Coerente; mantido |
| 48 | OTAC — cloreto de octiltrimetilamônio | C11H26ClN | Coerente; mantido |
| 49 | Cloreto de octilamônio | C8H20ClN | Coerente; mantido |
| 50 | DeTAB — brometo de deciltrimetilamônio | C13H30BrN | Coerente; mantido |
| 51 | DeTAC — cloreto de deciltrimetilamônio | C13H30ClN | Coerente; mantido |
| 52 | Cloreto de decilamônio | C10H24ClN | Coerente; mantido |
| 53 | DTAB — brometo de dodeciltrimetilamônio | C15H34BrN | Coerente; mantido |
| 54 | DTAC — cloreto de dodeciltrimetilamônio | C15H34ClN | Coerente; mantido |
| 55 | Cloreto de dodecilamônio | C12H28ClN | Coerente; mantido |
| 56 | TTAB — brometo de tetradeciltrimetilamônio | C17H38BrN | Coerente; mantido |
| 57 | TTAC — cloreto de tetradeciltrimetilamônio | C17H38ClN | Coerente; mantido |
| 58 | Cloreto de tetradecilamônio | C14H32ClN | Coerente; mantido |
| 59 | CTAB — brometo de cetiltrimetilamônio | C19H42BrN | Coerente; mantido |
| 60 | CTAC — cloreto de cetiltrimetilamônio | C19H42ClN | Coerente; mantido |
| 61 | Cloreto de hexadecilamônio | C16H36ClN | Coerente; mantido |
| 62 | STAB — brometo de esteariltrimetilamônio | C21H46BrN | Coerente; mantido |
| 63 | STAC — cloreto de esteariltrimetilamônio | C21H46ClN | Coerente; mantido |
| 64 | Cloreto de octadecilamônio | C18H40ClN | Coerente; mantido |
| 65 | Cloreto de benzalcônio C12 — homólogo dodecil | C21H38ClN | Coerente; mantido |
| 66 | Cloreto de benzalcônio C14 — homólogo tetradecil | C23H42ClN | Coerente; mantido |
| 67 | Cloreto de cetilpiridínio | C21H38ClN | Coerente; mantido |
| 68 | Cloreto de didecildimetilamônio | C22H48ClN | Coerente; mantido |
| 69 | Brometo de dioctildimetilamônio | C18H40BrN | Coerente; mantido |

### Cotensoativos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 70 | 1-octanol / álcool octílico | C8H18O | Identificação refinada |
| 76 | 1-decanol / álcool decílico | C10H22O | Identificação refinada |
| 82 | 1-dodecanol / álcool laurílico | C12H26O | Identificação refinada |
| 88 | 1-tetradecanol / álcool miristílico | C14H30O | Identificação refinada |
| 94 | 1-hexadecanol / álcool cetílico | C16H34O | Identificação refinada |
| 100 | 1-octadecanol / álcool estearílico | C18H38O | Identificação refinada |

### Surfactantes não iônicos

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 71 | Octeth-2 — álcool octílico etoxilado EO2 | C12H26O3 | Identificação refinada |
| 72 | Octeth-3 — álcool octílico etoxilado EO3 | C14H30O4 | Identificação refinada |
| 73 | Octeth-4 — álcool octílico etoxilado EO4 | C16H34O5 | Identificação refinada |
| 74 | Octeth-6 — álcool octílico etoxilado EO6 | C20H42O7 | Identificação refinada |
| 75 | Octil β-D-glucopiranosídeo | C14H28O6 | Estereoquímica definida |
| 77 | Deceth-2 — álcool decílico etoxilado EO2 | C14H30O3 | Identificação refinada |
| 78 | Deceth-3 — álcool decílico etoxilado EO3 | C16H34O4 | Identificação refinada |
| 79 | Deceth-4 — álcool decílico etoxilado EO4 | C18H38O5 | Identificação refinada |
| 80 | Deceth-6 — álcool decílico etoxilado EO6 | C22H46O7 | Identificação refinada |
| 81 | Decil β-D-glucopiranosídeo | C16H32O6 | Estereoquímica definida |
| 83 | Laureth-2 — álcool laurílico etoxilado EO2 | C16H34O3 | Identificação refinada |
| 84 | Laureth-3 — álcool laurílico etoxilado EO3 | C18H38O4 | Identificação refinada |
| 85 | Laureth-4 — álcool laurílico etoxilado EO4 | C20H42O5 | Identificação refinada |
| 86 | Laureth-6 — álcool laurílico etoxilado EO6 | C24H50O7 | Identificação refinada |
| 87 | Dodecil β-D-glucopiranosídeo | C18H36O6 | Estereoquímica definida |
| 89 | Myreth-2 — álcool miristílico etoxilado EO2 | C18H38O3 | Identificação refinada |
| 90 | Myreth-3 — álcool miristílico etoxilado EO3 | C20H42O4 | Identificação refinada |
| 91 | Myreth-4 — álcool miristílico etoxilado EO4 | C22H46O5 | Identificação refinada |
| 92 | Myreth-6 — álcool miristílico etoxilado EO6 | C26H54O7 | Identificação refinada |
| 93 | Tetradecil β-D-glucopiranosídeo | C20H40O6 | Estereoquímica definida |
| 95 | Ceteth-2 — álcool cetílico etoxilado EO2 | C20H42O3 | Identificação refinada |
| 96 | Ceteth-3 — álcool cetílico etoxilado EO3 | C22H46O4 | Identificação refinada |
| 97 | Ceteth-4 — álcool cetílico etoxilado EO4 | C24H50O5 | Identificação refinada |
| 98 | Ceteth-6 — álcool cetílico etoxilado EO6 | C28H58O7 | Identificação refinada |
| 99 | Hexadecil β-D-glucopiranosídeo | C22H44O6 | Estereoquímica definida |
| 101 | Steareth-2 — álcool estearílico etoxilado EO2 | C22H46O3 | Identificação refinada |
| 102 | Steareth-3 — álcool estearílico etoxilado EO3 | C24H50O4 | Identificação refinada |
| 103 | Steareth-4 — álcool estearílico etoxilado EO4 | C26H54O5 | Identificação refinada |
| 104 | Steareth-6 — álcool estearílico etoxilado EO6 | C30H62O7 | Identificação refinada |
| 105 | Octadecil β-D-glucopiranosídeo | C24H48O6 | Estereoquímica definida |
| 106 | 4-terc-octilfenol EO10 — homólogo de referência | C34H62O11 | Conectividade e fórmula corrigidas |
| 107 | 4-n-nonilfenol EO9 — referência de nonoxinol-9 | C33H60O10 | Conectividade e fórmula corrigidas |
| 108 | Monolaurato de 1,4-sorbitano — referência do Span 20 | C18H34O6 | Conectividade e fórmula corrigidas |
| 109 | Monooleato de 1,4-sorbitano (9Z) — referência do Span 80 | C24H44O6 | Conectividade e fórmula corrigidas |
| 110 | Polissorbato 20 — modelo molecular EO20 (5/5/5/5) | C58H114O26 | Conectividade e fórmula corrigidas |
| 111 | Polissorbato 80 — modelo molecular EO20 (5/5/5/5) | C64H124O26 | Conectividade e fórmula corrigidas |
| 112 | Lauramida MEA — homólogo C12 da cocamida MEA | C14H29NO2 | Identificação refinada |
| 113 | Lauramida DEA — homólogo C12 da cocamida DEA | C16H33NO3 | Identificação refinada |
| 114 | Oligômero EO2–PO2–EO1 — modelo tipo poloxâmero | C12H26O6 | Identificação refinada |
| 115 | Monolaurato de trietilenoglicol — PEG3 definido | C18H36O5 | Identificação refinada |

### Surfactantes anfóteros

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 116 | Octil dimetil betaína | C12H25NO2 | Coerente; mantido |
| 117 | Octil dimetil sulfopropil betaína | C13H29NO3S | Coerente; mantido |
| 118 | Óxido de N,N-dimetiloctilamina | C10H23NO | Coerente; mantido |
| 119 | Caprilamidopropil betaína | C15H30N2O3 | Coerente; mantido |
| 120 | Decil dimetil betaína | C14H29NO2 | Coerente; mantido |
| 121 | Decil dimetil sulfopropil betaína | C15H33NO3S | Coerente; mantido |
| 122 | Óxido de N,N-dimetildecilamina | C12H27NO | Coerente; mantido |
| 123 | Capramidopropil betaína | C17H34N2O3 | Coerente; mantido |
| 124 | Lauril dimetil betaína | C16H33NO2 | Coerente; mantido |
| 125 | Lauril dimetil sulfopropil betaína | C17H37NO3S | Coerente; mantido |
| 126 | Óxido de N,N-dimetildodecilamina / lauramina óxido | C14H31NO | Coerente; mantido |
| 127 | Lauroamidopropil betaína | C19H38N2O3 | Coerente; mantido |
| 128 | Miristil dimetil betaína | C18H37NO2 | Coerente; mantido |
| 129 | Miristil dimetil sulfopropil betaína | C19H41NO3S | Coerente; mantido |
| 130 | Óxido de N,N-dimetiltetradecilamina | C16H35NO | Coerente; mantido |
| 131 | Miristamidopropil betaína | C21H42N2O3 | Coerente; mantido |
| 132 | Cetil dimetil betaína | C20H41NO2 | Coerente; mantido |
| 133 | Cetil dimetil sulfopropil betaína | C21H45NO3S | Coerente; mantido |
| 134 | Óxido de N,N-dimetilhexadecilamina | C18H39NO | Coerente; mantido |
| 135 | Palmitamidopropil betaína | C23H46N2O3 | Coerente; mantido |
| 136 | Estearil dimetil betaína | C22H45NO2 | Coerente; mantido |
| 137 | Estearil dimetil sulfopropil betaína | C23H49NO3S | Coerente; mantido |
| 138 | Óxido de N,N-dimetiloctadecilamina | C20H43NO | Coerente; mantido |
| 139 | Estearamidopropil betaína | C25H50N2O3 | Coerente; mantido |
| 140 | Cocamidopropil betaína — modelo lauroamidopropil C12 | C19H38N2O3 | Coerente; mantido |
| 141 | Lauroamfoacetato de sódio — homólogo C12 de cadeia aberta | C18H35N2NaO4 | Conectividade e fórmula corrigidas |
| 142 | DPPC — 1,2-dipalmitoil-sn-glicero-3-fosfocolina | C40H80NO8P | Estereoquímica definida |

### Biossurfactantes

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 144 | Monorramnolipídeo Rha-C10-C10 — forma ácida de referência | C26H48O9 | Conectividade e fórmula corrigidas |
| 145 | Soforolipídeo ácido diacetilado — referência 9E | C34H58O15 | Conectividade e fórmula corrigidas |
| 146 | Surfactina C — lipo-heptapeptídeo cíclico completo | C53H93N7O13 | Conectividade e fórmula corrigidas |

### Surfactantes fluorados

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 147 | PFOA-Na — perfluorooctanoato de sódio | C8F15NaO2 | Coerente; mantido |
| 148 | PFOS-K — perfluorooctanossulfonato de potássio | C8F17KO3S | Coerente; mantido |
| 149 | 4:2 fluorotelômero sulfonato de sódio — modelo simplificado | C6H4F9NaO3S | Coerente; mantido |

### Siloxanos de referência

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 150 | Octametiltrissiloxano (MDM) | C8H24O2Si3 | Identificação refinada |

### Surfactantes siliconados

| Nº | Nome | Fórmula | Situação |
| --- | --- | --- | --- |
| 151 | Dissiloxano com éter de dietilenoglicol — modelo definido | C9H24O4Si2 | Identificação refinada |

## Alias estruturais mantidos

- sodium-c12-sulfate e sds representam o mesmo dodecil sulfato de sódio.
- c12-amidopropyl-betaine e cocamidopropyl-betaine-simplified representam o mesmo homólogo lauroamidopropil C12.

## SMILES dos vinte itens com estrutura atualizada

### Oleato de sódio — 9Z (cis)

ID preservado: `sodium-oleate`. Fórmula: `C18H33NaO2`.

```text
CCCCCCCC/C=C\CCCCCCCC(=O)[O-].[Na+]
```

### Linoleato de sódio — 9Z,12Z (cis,cis)

ID preservado: `sodium-linoleate`. Fórmula: `C18H31NaO2`.

```text
CCCCC/C=C\C/C=C\CCCCCCCC(=O)[O-].[Na+]
```

### Octil β-D-glucopiranosídeo

ID preservado: `c8-glucoside`. Fórmula: `C14H28O6`.

```text
CCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### Decil β-D-glucopiranosídeo

ID preservado: `c10-glucoside`. Fórmula: `C16H32O6`.

```text
CCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### Dodecil β-D-glucopiranosídeo

ID preservado: `c12-glucoside`. Fórmula: `C18H36O6`.

```text
CCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### Tetradecil β-D-glucopiranosídeo

ID preservado: `c14-glucoside`. Fórmula: `C20H40O6`.

```text
CCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### Hexadecil β-D-glucopiranosídeo

ID preservado: `c16-glucoside`. Fórmula: `C22H44O6`.

```text
CCCCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### Octadecil β-D-glucopiranosídeo

ID preservado: `c18-glucoside`. Fórmula: `C24H48O6`.

```text
CCCCCCCCCCCCCCCCCCO[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)CO)O)O)O
```

### 4-terc-octilfenol EO10 — homólogo de referência

ID preservado: `triton-x100-simplified`. Fórmula: `C34H62O11`.

```text
CC(C)(C)CC(C)(C)c1ccc(OCCOCCOCCOCCOCCOCCOCCOCCOCCOCCO)cc1
```

### 4-n-nonilfenol EO9 — referência de nonoxinol-9

ID preservado: `nonoxynol-9-simplified`. Fórmula: `C33H60O10`.

```text
CCCCCCCCCc1ccc(OCCOCCOCCOCCOCCOCCOCCOCCOCCO)cc1
```

### Monolaurato de 1,4-sorbitano — referência do Span 20

ID preservado: `span-20-simplified`. Fórmula: `C18H34O6`.

```text
CCCCCCCCCCCC(=O)OC[C@H]([C@@H]1[C@@H]([C@H](CO1)O)O)O
```

### Monooleato de 1,4-sorbitano (9Z) — referência do Span 80

ID preservado: `span-80-simplified`. Fórmula: `C24H44O6`.

```text
CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H]([C@@H]1[C@@H]([C@H](CO1)O)O)O
```

### Polissorbato 20 — modelo molecular EO20 (5/5/5/5)

ID preservado: `tween-20-simplified`. Fórmula: `C58H114O26`.

```text
CCCCCCCCCCCC(=O)OCCOCCOCCOCCOCCOC[C@H]([C@@H]1[C@@H]([C@H](CO1)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO
```

### Polissorbato 80 — modelo molecular EO20 (5/5/5/5)

ID preservado: `tween-80-simplified`. Fórmula: `C64H124O26`.

```text
CCCCCCCC/C=C\CCCCCCCC(=O)OCCOCCOCCOCCOCCOC[C@H]([C@@H]1[C@@H]([C@H](CO1)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO)OCCOCCOCCOCCOCCO
```

### Lauroamfoacetato de sódio — homólogo C12 de cadeia aberta

ID preservado: `cocoamphoacetate-simplified`. Fórmula: `C18H35N2NaO4`.

```text
CCCCCCCCCCCC(=O)NCCN(CCO)CC(=O)[O-].[Na+]
```

### DPPC — 1,2-dipalmitoil-sn-glicero-3-fosfocolina

ID preservado: `lecithin-fragment`. Fórmula: `C40H80NO8P`.

```text
CCCCCCCCCCCCCCCC(=O)OC[C@H](COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCCCCCC
```

### α-L-ramnopiranose

ID preservado: `rhamnose`. Fórmula: `C6H12O5`.

```text
C[C@H]1[C@@H]([C@H]([C@H]([C@@H](O1)O)O)O)O
```

### Monorramnolipídeo Rha-C10-C10 — forma ácida de referência

ID preservado: `mono-rhamnolipid-simplified`. Fórmula: `C26H48O9`.

```text
CCCCCCCC(CC(=O)O)OC(=O)CC(CCCCCCC)O[C@H]1[C@@H]([C@@H]([C@H]([C@@H](O1)C)O)O)O
```

### Soforolipídeo ácido diacetilado — referência 9E

ID preservado: `sophorolipid-simplified`. Fórmula: `C34H58O15`.

```text
CC(CCCCCC/C=C/CCCCCCCC(=O)O)O[C@H]1[C@@H]([C@H]([C@@H]([C@H](O1)COC(=O)C)O)O)O[C@H]2[C@@H]([C@H]([C@@H]([C@H](O2)COC(=O)C)O)O)O
```

### Surfactina C — lipo-heptapeptídeo cíclico completo

ID preservado: `surfactin-fragment`. Fórmula: `C53H93N7O13`.

```text
CC(C)CCCCCCCCC[C@@H]1CC(=O)N[C@H](C(=O)N[C@H](C(=O)N[C@@H](C(=O)N[C@H](C(=O)N[C@H](C(=O)N[C@@H](C(=O)N[C@H](C(=O)O1)CC(C)C)CC(C)C)CC(=O)O)C(C)C)CC(C)C)CC(C)C)CCC(=O)O
```

## Referências usadas nos casos específicos

1. [Fonte estrutural 1](https://www.stepan.com/content/dam/stepan-dot-com/webdam/website-product-documents/literature/household-institutional-industrial-cleaning/StepanHIIProductSelectorGuide.pdf)
2. [Fonte estrutural 2](https://www.stepan.com/content/stepan-dot-com/en/products-markets/product/STEPANATESXS.html)
3. [Fonte estrutural 3](https://precision.fda.gov/ginas/app/ui/substances/M590021Z02)
4. [Fonte estrutural 4](https://pubchem.ncbi.nlm.nih.gov/compound/23665730)
5. [Fonte estrutural 5](https://pubchem.ncbi.nlm.nih.gov/compound/23676150)
6. [Fonte estrutural 6](https://pubchem.ncbi.nlm.nih.gov/compound/62852)
7. [Fonte estrutural 7](https://www.sigmaaldrich.com/deepweb/assets/sigmaaldrich/product/documents/160/855/t8532pis.pdf)
8. [Fonte estrutural 8](https://pubchem.ncbi.nlm.nih.gov/compound/72385)
9. [Fonte estrutural 9](https://pubchem.ncbi.nlm.nih.gov/compound/22833303)
10. [Fonte estrutural 10](https://pubchem.ncbi.nlm.nih.gov/compound/9920342)
11. [Fonte estrutural 11](https://www.fao.org/fileadmin/user_upload/jecfa_additives/docs/Monograph1/Additive-320.pdf)
12. [Fonte estrutural 12](https://www.fao.org/fileadmin/user_upload/jecfa_additives/docs/Monograph1/Additive-321.pdf)
13. [Fonte estrutural 13](https://webprod.hc-sc.gc.ca/nhpid-bdipsn/ingredReq?id=12454&wbdisable=true)
14. [Fonte estrutural 14](https://pubchem.ncbi.nlm.nih.gov/compound/452110)
15. [Fonte estrutural 15](https://pubchem.ncbi.nlm.nih.gov/compound/439710)
16. [Fonte estrutural 16](https://pubchem.ncbi.nlm.nih.gov/compound/162246)
17. [Fonte estrutural 17](https://pubchem.ncbi.nlm.nih.gov/compound/11856871)
18. [Fonte estrutural 18](https://pubchem.ncbi.nlm.nih.gov/compound/443592)
19. [Fonte estrutural 19](https://pubchem.ncbi.nlm.nih.gov/compound/24705)

As séries homólogas foram conferidas por contagem de carbonos, unidades EO, grupos funcionais e cargas. O uso de um esqueleto comum para outros comprimentos de cadeia é uma derivação estrutural da auditoria.

## Aplicação no projeto local

Salve corrigir_atalhos_moleculares.py na pasta principal e execute:

```bash
python3 corrigir_atalhos_moleculares.py
bash iniciar_linux.sh
```

O aplicador atualiza apenas o componente de atalhos e esta auditoria. Guarda a versão anterior em backups/correcao_atalhos. Se o catálogo tiver uma edição local diferente da versão esperada, a aplicação para antes das substituições.

Depois atualize o navegador com Ctrl+F5 e selecione novamente os atalhos desejados. Moléculas salvas anteriormente preservam suas próprias estruturas; devem ser recriadas a partir dos atalhos revisados quando for necessária a estrutura nova.
