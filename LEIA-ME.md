# Modelagem3D — recuperação para Linux

Esta cópia foi reconstruída dos arquivos `codigo_backend.txt` e `codigo_frontend.txt` enviados em 04/11/2026. Mantém React/TypeScript, FastAPI, PostgreSQL, RDKit, Micelium e o runner OpenMM. As correções e os limites da validação estão em `documentacao/recuperacao/RELATORIO_RECUPERACAO.md`.

A instalação no seu Ubuntu ainda precisa ser executada. O pacote não foi instalado remotamente no seu computador.

## Iniciar

1. Extraia o ZIP em uma pasta separada, preservando sua pasta anterior.
2. Abra o terminal dentro da pasta `Modelagem3D` extraída.
3. Execute:

```bash
bash iniciar_linux.sh
```

O computador precisa ter Docker Engine e o plugin `docker compose` funcionando para seu usuário. A primeira execução baixa imagens e dependências; precisa de internet. Para esse caminho, não é necessário instalar Node, Python ou RDKit diretamente no Ubuntu.

O script inicia PostgreSQL, salva um backup do banco configurado no Compose, constrói a API e a interface e aplica as migrações. A pasta `backups` recebe o arquivo `.dump` antes da migração. Se esse backup falhar, o script para.

Após a mensagem de sucesso:

| Serviço | Endereço |
| --- | --- |
| Interface | http://localhost:5173 |
| API e documentação | http://127.0.0.1:8000/docs |
| Saúde do banco | http://127.0.0.1:8000/api/v1/health/database |
| PostgreSQL no host | 127.0.0.1:5433 |

Para conferir a instalação:

```bash
bash diagnosticar_linux.sh
```

O diagnóstico verifica 18 operações da API e do streaming. Se aparecer erro, copie a saída do terminal, incluindo a primeira mensagem de falha.

Para parar a interface e a API:

```bash
bash parar_linux.sh
```

O banco e os dados permanecem disponíveis. Os scripts não removem volumes, não executam reset e não apagam seu projeto anterior.

## Banco anterior e dados pessoais

O Compose preserva o serviço, o nome do container, a porta 5433 e a declaração de volume enviados no código. O volume efetivamente utilizado depende do nome do projeto Compose da instalação anterior. Um banco que estava em outro volume, em outro servidor ou no Windows exige o backup correspondente.

Nenhum dump do banco antigo veio nos anexos. Este pacote consegue criar o esquema e os dados de referência; não consegue reconstruir seu histórico de moléculas, experimentos ou previsões a partir do código. Os 118 elementos e quatro grupos funcionais são dados de referência.

Se já existir um container `modelagem3d_postgres` e houver conflito de nome ou porta, preserve-o e envie o erro. Não é necessário excluir um banco para investigar esse conflito.

## Modelos de IA

Nenhum arquivo `.joblib` veio nos anexos. As quatro rotas de previsão funcionam com as heurísticas existentes. Não foram treinados ou inventados novos modelos.

Para recuperar seus modelos, copie os arquivos próprios para:

```text
backend/app/modules/micelium/IA/trained_models/<rota>/<alvo>.joblib
```

Rotas: `anionic_ai`, `cationic_ai`, `nonionic_ai` e `zwitterionic_ai`.
Alvos usados pelo código: `cmc_mmol_l`, `effective_hlb` e `hlb`.
É necessário manter a compatibilidade entre as versões de scikit-learn usadas no treinamento e na execução.

## Conferência visual no Ubuntu

1. Abra a interface, digite `CCO` e clique em **Gerar 2D**.
2. Confira a fórmula `C2H6O` e os parâmetros no painel esquerdo.
3. Clique em **Salvar atual**, selecione a molécula como reagente e defina a quantidade em mmol.
4. Clique em **Misturar** e confira o carregamento do ambiente 3D.
5. Teste **Cancelar execução 3D** e **Apagar ambiente 3D**.

O fluxo de dados passou em DOM virtual, mas a imagem Three.js/WebGL precisa ser verificada no navegador do seu computador. Se houver aviso de WebGL indisponível, envie esse aviso junto com o diagnóstico.

## Desenvolvimento sem containers para a aplicação

Os arquivos `backend/.env.example` e `frontend/.env.example` fornecem a configuração local. Para esse caminho, o backend requer Python 3.12 e o frontend foi validado com Node 24. Não inicie as duas formas simultaneamente nas mesmas portas.

No backend, crie `.env` a partir do exemplo, crie um ambiente virtual, instale `requirements.txt`, inicie somente o serviço PostgreSQL do Compose e rode `python -m alembic upgrade head`. Depois inicie `python -m uvicorn app.main:app --reload`.

No frontend, crie `.env.local` a partir do exemplo, execute `npm ci` e depois `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`.

A inicialização com Docker executa a interface compilada. Após editar o código, execute novamente `bash iniciar_linux.sh` para reconstruir os serviços.

## Limites atuais

Há duas divergências substanciais nos cenários antigos de morfologia: DDAB vesicular e SDS em etanol. Elas estão descritas no relatório; a precisão científica desses modelos não foi declarada validada. Os botões **Salvar Projeto** e **Modo Predição** do cabeçalho vieram sem ação implementada. A biblioteca de moléculas do editor continua sendo estado da sessão, como no código enviado.

Consulte `documentacao/recuperacao/CORRECOES_EXISTENTES.patch` para revisar alterações nos arquivos originais. `documentacao/recuperacao/manifesto_recuperacao.json` registra os hashes dos arquivos extraídos antes das correções.


## Organização após a unificação

A versão ativa está em `backend` e `frontend`. Backups ficam em `backups`; documentos em `documentacao`; configurações antigas em `configuracoes/recuperadas`; dados e modelos antigos em `dados/recuperados`. Versões diferentes de código e ambientes antigos ficam em `arquivo`. Consulte `documentacao/unificacao/RELATORIO.md`. Modelos e configurações recuperados não foram ativados automaticamente.

## Autoria e licença

Autor: **Felipe Silva Miranda** — GitHub [@Flips794](https://github.com/Flips794) · Currículo Lattes: <https://lattes.cnpq.br/9167949811810354>

Distribuído sob a licença MIT; veja [LICENSE](LICENSE). Os dados experimentais de CMC vêm do NSRDS-NBS 36 (NIST) e os valores de pKa do CRC Handbook, com a referência indicada em cada campo; as fontes estão em [documentacao/CALCULOS.md](documentacao/CALCULOS.md).
