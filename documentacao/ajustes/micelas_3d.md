# Correção de organização supramolecular 3D

Data: 4 de novembro de 2026.

## Problemas corrigidos

- Exclusão estérica atuava entre beads covalentes adjacentes e alongava as ligações.
- Molas fracas e forças atrativas permitiam caudas dobradas sobre si mesmas e comprimiam todos os beads no mesmo domínio.
- O motor não conservava o eixo de um agregado entre detecções, prejudicando cilindros e bicamadas.
- Seleção do solvente e forças locais podiam usar polaridades diferentes; álcool de cadeia longa podia ser confundido com alcano.
- A contagem visual e a escrita do SMILES influenciavam indevidamente a classificação de algumas moléculas.
- A análise substituía resultados medidos por rótulos e escores planejados.

## Comportamento da atualização

O motor continua usando beads de cabeça e cauda. Restrições de comprimento preservam as ligações, a rigidez angular é suave e a exclusão de volume atua entre moléculas. Um campo médio local organiza os agregados detectados com tamanho finito, orientação e curvatura conforme a tendência do CPP e do meio. O movimento não depende de um ponto de atração na origem e não recebe slots de uma micela previamente desenhada.

Em meio polar, o domínio hidrofóbico fica protegido e as cabeças se orientam para o solvente. No regime inverso, as cabeças se orientam para o interior e as caudas para o meio apolar. Abaixo da CMC estimada, o motor não força um agregado estável.

O painel apresenta separadamente a tendência prevista e a morfologia reconhecida nas coordenadas. Fração organizada refere-se à amostra visual, e não é uma medição experimental da fração micelizada. A orientação e a segregação também são verificadas nas coordenadas, incluindo os dois lados de uma bicamada.

Quantidades reais em mmol e volume definem a concentração; contagens visuais controlam a amostragem. Para misturas de surfactantes com CMC conhecida, a soma ci/CMCi é uma aproximação de mistura ideal, sem parâmetros de interação não ideal.

## Aplicação no computador

Salve corrigir_micelas_3d.py dentro da pasta principal que contém backend, frontend e iniciar_linux.sh. Execute nessa pasta:

```bash
python3 corrigir_micelas_3d.py
bash iniciar_linux.sh
```

O aplicador confere os arquivos de origem, guarda uma cópia dos arquivos substituídos em backups/correcao_micelas_3d e aplica somente esta atualização. Se detectar uma edição local diferente da versão esperada, para antes de alterar os arquivos. Uma segunda execução reconhece a atualização já aplicada.

Depois abra http://localhost:5173 e pressione Ctrl+F5. Clique em Misturar para gerar novamente as coordenadas. A reconstrução do backend inicia uma nova sessão em memória. O banco e os modelos de IA não são editados por este aplicador.

## Verificação visual sugerida

SDS em água: 3 mmol em 100 mL, a 298,15 K, serve como caso acima da CMC de referência. Observe a aproximação, a separação das regiões e a evolução dos agregados. Reduzir para 0,1 mmol no mesmo volume coloca esse caso abaixo da CMC de referência; não deve aparecer uma micela estável forçada.

Nem todo conjunto de poucas moléculas visuais representa uma micela completa. A organização é progressiva e pode coexistir com monômeros ou pré-agregados. Para examinar um regime inverso, use um surfactante compatível com meio apolar; trocar o solvente, sozinho, não comprova uma micela inversa experimental.

## Validação desta atualização

- 27 testes do backend aprovados, incluindo os quatro regimes geométricos, preservação das ligações, continuidade, concentração abaixo da CMC, perfis de solventes e classificação molecular.
- 4 testes do frontend aprovados para quantidade real, CMC de referência, classificação inconclusiva e solvente.
- Compilação de produção da interface concluída e chamada HTTP à API com resposta 200.
- 6 cenários do aplicador aprovados: conferência sem alterações, aplicação com backup íntegro, reaplicação, proteção de edições locais, restauração após falha de gravação e rejeição de links externos.

Essas verificações foram executadas no ambiente de desenvolvimento. A instalação no SSD ocorre ao executar o aplicador no computador do usuário.

## Alcance científico

Trata-se de visualização mesoscópica orientada por um campo médio heurístico. Os testes verificam coerência geométrica e regressões computacionais. Eles não validam CMC, tamanho de equilíbrio, tempo de formação ou fase experimental de um anfifílico arbitrário. Os tempos de animação não devem ser usados como cinética quantitativa.

A representação linear de uma cabeça e uma cauda não descreve integralmente lipídios de várias caudas, anfifílicos ramificados complexos ou micelas de solventes mistos. Hidratação, protonação, contraíons, composição, temperatura e modelos calibrados continuam necessários para previsão científica de fase. A inferência de comprimento de cauda pelo grafo tem limite de 32 carbonos para esta representação CG.

## Referências de fundamento

- Israelachvili, Mitchell e Ninham (1976). Theory of self-assembly of hydrocarbon amphiphiles into micelles and bilayers. DOI: https://doi.org/10.1039/F29767201525
- Clint (1975). Micellization of mixed nonionic surface active agents. DOI: https://doi.org/10.1039/F19757101327
- Polar Solvents Trigger Formation of Reverse Micelles (2015). DOI: https://doi.org/10.1021/la504658u

Os coeficientes do campo médio desta atualização são escolhas numéricas para a visualização; não foram ajustados a esses artigos e não devem ser apresentados como parâmetros experimentais publicados.
