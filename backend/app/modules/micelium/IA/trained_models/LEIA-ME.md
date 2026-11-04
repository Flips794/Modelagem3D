# Modelos treinados

Os arquivos enviados não continham modelos `.joblib`.
Sem esses arquivos, o programa usa as heurísticas já existentes.
Para recuperar modelos próprios, copie as pastas das quatro classes para este diretório,
mantendo os nomes originais definidos em `model_registry.py`.
Copie apenas modelos da sua própria origem: joblib desserializa código Python.

Estrutura esperada: `<rota>/<alvo>.joblib`, por exemplo `anionic_ai/cmc_mmol_l.joblib`.
Consulte `specialized_base.py` para os nomes dos alvos usados pelo programa.
