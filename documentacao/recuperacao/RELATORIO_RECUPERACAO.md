# Relatório de recuperação — 04/11/2026

## Resultado

Foram reconstruídos 220 arquivos dos dois TXT, incluindo um PNG que estava concatenado ao texto. A aplicação importou, o frontend compilou e o fluxo de importação, análise, salvamento na sessão, mistura, cancelamento e limpeza passou em DOM virtual, com chamadas reais ao backend.

O pacote inclui inicialização local com Docker. A construção das imagens e a renderização WebGL precisam ser confirmadas no Ubuntu do usuário. Não há acesso remoto a esse computador nesta conversa.

## Correções realizadas

| Conjunto | Problema encontrado | Correção |
| --- | --- | --- |
| Dependências | RDKit, NumPy, OpenMM e suporte a modelos não declarados | Dependências científicas declaradas; versões Python fixadas e lock do npm gerado |
| Configuração | Ausência de configuração local e CORS | Exemplos de ambiente; Compose fornece URL do banco e origens locais |
| Configuração | `.env` dependia da pasta de execução | Caminho vinculado ao diretório real do backend |
| Migrações | `ElementModel` e `FunctionalGroupModel` inexistentes no import do Alembic | Import compatível com o modelo atual |
| Migrações | Duas raízes independentes | Nova migração de junção, mantendo os IDs antigos |
| Banco | Tabela `elements` não possuía colunas consultadas pelo repositório | Colunas adicionais e cadastro dos 118 elementos |
| Banco | Tabela de treino dependia de execução manual | Criação incorporada à migração; sem carregar novos dados experimentais |
| Codificação | SQL de treino continha BOM | Leitura com `utf-8-sig` na migração |
| TypeScript | Valores nulos incompatíveis e retorno recursivo sem tipo | Ajustes de tipos, mantendo as verificações do compilador |
| TypeScript | Funções antigas sem chamadas impediam build | Remoção de código sem uso; normalizador de bibliotecas ligado à resposta |
| Classificação | Betaína era sobrescrita pela classificação catiônica | Preservada a classe zwitteriônica |
| Classificação | Padrão genérico confundia éster com ácido/carboxilato | SMARTS distingue oxigênio de ácido e éster neutro |
| Classificação | Gemini 16-2-16 capturado como CTAB ou cátion de cauda única | Perfil CTAB restrito; rota Gemini tem precedência sobre regra genérica |
| Compatibilidade | Campo legado `cpp` era ignorado silenciosamente | Alias para `packing_parameter`, preservando o campo atual como prioritário |
| Execução | Banco, API e interface iniciados separadamente | Script inicia serviços, faz backup antes de migrar e verifica saúde |

Os algoritmos numéricos de formação de micelas não foram recalibrados para fazer testes científicos passarem.

## Verificação executada

| Verificação | Resultado e alcance |
| --- | --- |
| `npm run build` | Passou: TypeScript e Vite; aviso de bundle grande mantido |
| `npm ci --dry-run` | Passou; avisos de peer dependency React 18 de dependência transitiva do Ketcher |
| Sintaxe Python | Módulos do aplicativo analisados sem erro |
| Dependências Python | `pip check` sem incompatibilidades |
| Migração de banco vazio | Passou em PostgreSQL via PGlite/WASM, pelo protocolo PostgreSQL e driver psycopg |
| Segunda execução das migrações | Passou, sem novas alterações |
| Persistência | Criar/listar/consultar molécula; criar/consultar pacote e hash; salvar previsão IA |
| Dados de referência | 118 elementos vindos do banco, quatro grupos funcionais; 12 tabelas incluindo controle Alembic |
| Entrada inválida | SMILES inválido rejeitado com HTTP 422 |
| Testes existentes por pytest | Três testes passaram |
| Aceitação MIRIAM-2.1 | Oito cenários passaram após corrigir a precedência Gemini |
| Compatibilidade CPP | Campo antigo, campo atual e prioridade quando ambos existem verificados |
| Diagnóstico HTTP/WebSocket | 18/18 verificações passaram, incluindo frame OpenMM com coordenadas finitas |
| Interface em DOM virtual | Sem erro de renderização React; importação e cálculo de etanol passaram |
| Fluxo 2D → 3D | Etanol salvo na sessão, selecionado e transferido com identidade preservada; simulação HTTP 200; cancelar e apagar funcionaram |
| Quantidade no fluxo | 10 mmol em 100 mL transferidos como 100 mmol/L; contagem visual separada |
| Arquivo PNG | Integridade validada após extração |
| Scripts e Compose | Sintaxe Bash e estrutura YAML verificadas |

O teste do banco não foi executado em Docker nem em PostgreSQL nativo 16. PGlite testa a execução SQL e a persistência, mas não cobre instalação de Docker, permissões de volumes ou particularidades do host. O Chromium necessário ao teste gráfico não pôde ser obtido neste ambiente; a interface foi exercitada em DOM virtual com WebGL indisponível.

## Regressão de morfologia

O teste legado `dynamic_morphology_smoke_test.py` não passou integralmente. A auditoria inicial executou seus sete cenários e identificou que o parâmetro `cpp` era descartado pelo schema. Depois da correção do alias, o planejador de morfologia foi conferido novamente com os mesmos sete cenários:

| Cenário | CPP agora recebido | Resultado do planejador | Situação |
| --- | ---: | --- | --- |
| SDS abaixo da CMC | 0,24 | Monômeros/pré-agregados; fração 0,03 | Compatível com condição abaixo da CMC; texto esperado pelo teste estava desatualizado |
| SDS esférica | 0,24 | Micela esférica; fração 0,62 | Morfologia esperada recuperada |
| CTAB cilíndrica | 0,42 | Micela cilíndrica/wormlike; fração 0,78 | Morfologia esperada recuperada |
| DDAB bicamada plana | 0,88 | Bicamada plana/lamelar; fração 0,78 | Morfologia esperada recuperada |
| DDAB vesícula | 0,92 | Bicamada plana/lamelar; fração 0,78 | Diverge da vesícula esperada pelo teste |
| AOT inversa | 1,10 | Lamelar compacta/inversa; fração 0,22 | Inclui a classificação inversa esperada |
| SDS em etanol | 0,24 | Micela esférica; fração 0,42 | Diverge de pré-agregados e da fração máxima 0,35 do teste |

Essa última conferência avaliou o planejador, sem repetir todas as trajetórias longas. O teste legado continua com suas expectativas originais. Não foram reduzidas exigências nem modificados os resultados esperados para ocultar as divergências. Elas exigem uma decisão sobre o modelo físico e validação própria, separada da reinstalação.

## Funcionalidades incompletas já presentes nos arquivos

- `HeaderPage.tsx`: **Salvar Projeto** e **Modo Predição** não possuem `onClick` ou fluxo associado.
- `Page2D`: **Salvar atual** acrescenta moléculas ao estado React da sessão. Não grava essa biblioteca no PostgreSQL nem garante sua recuperação após atualizar a página.
- O painel rápido de parâmetros informa no próprio código que HOMO/LUMO e várias propriedades avançadas são proxies/heurísticas. A instalação de OpenMM não transforma esses campos em resultados de DFT ou xTB.
- A biblioteca contém representantes estruturais simplificados de produtos comerciais, incluindo derivados de Tween. Não devem ser tratados como a distribuição molecular completa do produto comercial.
- PubChem é uma consulta externa opcional com timeout; houve indisponibilidade na validação, e o aplicativo continuou com dados locais.

## O que não veio nos anexos

Não foram fornecidos dump do banco, modelos `.joblib`, arquivo de configuração local anterior nem histórico Git. A cópia do código não permite recuperar esses dados ou garantir equivalência com algum commit anterior não identificado.

## Referências técnicas consultadas

- RDKit, instalação: https://www.rdkit.org/docs/Install.html
- Vite, requisitos e execução: https://vite.dev/guide/
- Alembic, ramificações e junção de migrações: https://alembic.sqlalchemy.org/en/latest/branches.html
- PGlite Socket, limitações e protocolo: https://github.com/electric-sql/pglite/blob/main/packages/pglite-socket/README.md

As evidências de funcionamento deste relatório vêm da execução dos arquivos recuperados, não dessas páginas de documentação.
