# Código e evidências da correção

Leia `relatorio_validacao_calculos.md`. O aplicador contém todos os 27 arquivos, incluindo testes e catálogo de referência.

- `arquivos_alterados/`: versões finais para revisão; aplique pelo script para obter verificação e cópia de segurança.
- `evidencias/`: relatórios aprovados e versões/hashes. Os 24 casos de geometria foram extraídos, sem alterar seus resultados, da rodada completa das regressões CG.
- `antes_correcao_calculos/`: somente os arquivos originais necessários aos testes do aplicador; não copie esta pasta sobre seu projeto.
- `tests_instalador/`: testes do aplicador; execute `python -m pytest tests_instalador -q` nesta pasta, com pytest instalado.

Para repetir cálculos/API/geometria e frontend, aplique a correção em uma cópia do projeto e siga os comandos do relatório. O pacote não inclui suas dependências nem seu banco de dados.
