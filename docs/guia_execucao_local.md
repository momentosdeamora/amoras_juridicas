# Guia de execução local — Amoras Jurídicas

POC local de acompanhamento processual e pesquisa assistida, com ambiente Poetry e configuração de containers. Os processos, identidades, documentos e publicações são sintéticos. Nenhum portal judicial é consultado e nenhum serviço pago é contratado.

## Executar com Poetry

```bash
python3 run.py --prepare-dev
python3 run.py --serve-dev --secure
```

Abra **http://localhost:5000**, clique em **Criar minha conta** e informe login, senha e perfil. Cadastro livre, sem e-mail ou aprovação, somente para demonstração. Senhas usam scrypt; sessões expiram em 8 horas e são revogadas ao sair. Somente gestor/CEO e TI têm visão completa. O login com contas é obrigatório também sem `--secure`; essa opção mantém a preparação de segredos legados do ambiente. Poetry usa a `.venv` local.

Para quem já tem Poetry instalado:

```bash
poetry install
poetry run python run.py --secure
```

Requer Python 3.12 a 3.14. A importação do PDF usa pdftotext/Poppler. Ollama e os pesos locais são independentes da venv. O banco persiste em `data/poc.sqlite3`.

## Containers

```bash
python3 run.py --init-security
docker compose build
docker compose --profile setup run --rm model-import
docker compose up -d app
```

A importação reaproveita os pesos já baixados em `.runtime/models`. Em outro host, use `model-download` no lugar de `model-import` para baixar explicitamente o modelo. A inferência continua local, sem cloud.

**Neste ambiente não há engine Docker disponível.** Os Dockerfiles, o Compose e as imagens por digest foram preparados; a configuração foi validada, mas o build e a execução dos containers permanecem pendentes. O painel em funcionamento usa Poetry e Ollama locais.

Veja [segurança e containers](seguranca_e_containers.md) para redes, permissões, volumes, login, comandos e limites da validação.

## Primeiro percurso

1. Clique em **Iniciar demonstração** na visão geral. São recebidos seis snapshots de metadados e seis publicações, em transações independentes. O trabalhador processa a fila automaticamente.
2. Abra **Processos e dossiês**. CASO-001 mostra um fluxo completo; CASO-002 mostra contradição temporal; CASO-003 explicita ausência de histórico; CASO-004 exige pesquisa de tutela; CASO-005 não gera alerta; CASO-006 exige revisão por ilegibilidade.
3. Expanda o dossiê, as evidências e o rastro de ferramentas. As referências editoriais apontam para fontes oficiais, abertas somente se você clicar.
4. Registre uma revisão e exporte o JSON do dossiê.
5. Em **Laboratório de eventos**, provoque duplicidade, retificação, indisponibilidade e interrupção de tarefa. Retome as tarefas com falha.
6. Retire o histórico de CASO-002. O dossiê é recalculado com uma pendência; as execuções anteriores permanecem em `runs`.
7. Execute **Avaliação**. Os resultados são calculados no momento, não números de demonstração fixados no painel.
8. Saia e entre com uma conta de advogado vinculada à carteira Ana ou Bruno para validar a restrição. Use uma conta Gestor/CEO ou TI para operações globais. A carteira aparece no cadastro somente ao escolher Advogado.
9. Consulte arquitetura, viabilidade econômica e segurança no próprio painel.

Enquanto houver tarefas, visão geral, processos e laboratório recarregam a cada quatro segundos. A revisão deve ser preenchida após a conclusão da fila para evitar perder um formulário em andamento. Uma falha simulada exige retomada manual; indisponibilidade da fonte exige restaurar e repetir a coleta.

## Implementação

| Arquivo | Responsabilidade |
| --- | --- |
| `run.py` | HTTP local, formulários, validações, exportação e inicialização. |
| `poc/fixtures.py` | Seis casos, documentos sintéticos, referências editoriais e exemplos de classificação. |
| `poc/store.py` | SQLite, esquema, ingestão, auditoria, deduplicação e fontes. |
| `poc/engine.py` | Triagem, busca textual, pesquisa adaptativa, fila e avaliação. |
| `poc/local_agent.py` | Tool calling nativo, validação de argumentos e métricas do modelo. |
| `poc/local_runtime.py` | Instalação portátil, launcher sem cloud e diagnóstico local. |
| `poc/corpus.py` | Importação e busca de teses com páginas e proveniência. |
| `poc/ui.py` | Estrutura do painel e tema `#19414a` / `#efeee9`, sem JavaScript. |
| `poc/dashboard.py` | Painéis visuais, métricas e detalhes expansíveis. |
| `poc/charts.py` | Gráficos SVG gerados localmente com dados do banco. |
| `poc/chat.py` | Conversas do gestor, contexto, fontes e fila de respostas locais. |
| `tests/` | Testes funcionais e HTTP em memória. |
| `docs/arquitetura_e_validacao.md` | Decisões, segurança, hipóteses, evolução e critérios do piloto. |
| `docs/roteiro_apresentacao.md` | Roteiro de 18 minutos para apresentar o case. |

Nenhuma biblioteca externa é necessária. SQLite FTS5 é usado se disponível; caso contrário, existe busca lexical de fallback. Não há embeddings, OCR ou busca semântica nesta versão. O ambiente de produção proposto no documento é uma evolução, não algo provisionado pela POC.

## Agente local com Ollama

O ambiente atual já tem Ollama portátil em `.runtime/ollama/` e **Qwen3 1.7B** em `.runtime/models/`. O launcher desativa cloud e escuta somente em 127.0.0.1. A instalação e o download são ações explícitas; a aplicação não baixa modelos automaticamente.

Para reproduzir em outro ambiente, o instalador portátil requer Linux x86_64 e Python 3.14 para extração segura de zstd:

```bash
python3 run.py --install-ollama
python3 run.py --serve-ollama
```

Com o Ollama rodando, em outro terminal:

```bash
python3 run.py --pull-model
python3 run.py
```

O download inicial usa a distribuição oficial do Ollama e o modelo público (~1,4 GB). Não há inferência remota nem conta de nuvem. O launcher define `OLLAMA_NO_CLOUD=1`. Não se deve habilitar nomes de modelos cloud.

Na inicialização, o painel detecta o modelo local fixado `qwen3:1.7b`. O agente usa tool calling nativo para consultar documentos do processo autorizado, formular consultas ao acervo e encerrar a pesquisa. O controlador valida argumentos, oferece somente ferramentas permitidas e exige consulta documental e pesquisa antes de disponibilizar encerramento. Há até seis chamadas em quatro rodadas, contexto de 4096 e timeout por requisição. O dossiê mantém resultado extrativo e exibe modelo, versão de prompt, tokens, duração e ferramentas.

Para testar uma execução real ou desativar o modelo:

```bash
python3 run.py --ollama-status
python3 run.py --test-agent --case CASO-002
python3 run.py --no-llm
```

A execução de teste salva `data/agent_validation.json`. O teste real completou consulta, pesquisa e encerramento e recuperou teses 7 e 8 relacionadas à Súmula 385. A latência observada com modelo carregado foi aproximadamente 1,8 segundo, sem constituir benchmark de produção. Respostas inválidas ou indisponibilidade geram contingência explícita; não são contadas como sucesso do agente.

A política baseada em regras continua disponível como preparação e contingência. Ela não é apresentada como inferência LLM. O texto livre do modelo não é aceito como fundamento jurídico e erros de ferramenta não autorizam acesso adicional.

## Acervo real importado

O arquivo `Cadastro de Inadimplentes.pdf` foi importado: **20 teses em 8 páginas**, com **12 candidatas ao recorte**. A aba **Acervo jurídico real** oferece busca e acesso à página do PDF original. Os processos continuam fictícios.

É a edição 59 de Jurisprudência em Teses, de 08/06/2016. Trata-se de compilação histórica, não inteiro teor de acórdãos nem prova de entendimento atual. O texto, precedentes citados, páginas, hash e limites são preservados. Consulte `docs/avaliacao_pdf_cadastro.md` para a avaliação e inconsistência de data encontrada.

Cada dossiê novo ou reprocessado inclui teses recuperadas, separadas das paráfrases editoriais. Use **Refazer pesquisa com configuração atual** para atualizar um dossiê antigo. O PDF é servido por uma rota fixa no localhost; não há download judicial nem busca externa durante a pesquisa.

## Conversar com a IA

Entre com uma conta **Gestor/CEO ou TI** e abra **Conversar com a IA**. O formulário começa em **Escolha o assunto**: selecione **Sobre o acervo**, **Sobre um ou mais processos** ou **Sobre o acervo e os processos**. Nos dois últimos, marque os processos desejados e clique em **Nova conversa**. Escreva a pergunta e envie.

O histórico fica no SQLite e permanece após reinícios. Para excluir uma conversa, selecione-a, clique em **Excluir conversa** e confirme na tela seguinte. A conversa e as mensagens serão removidas; uma resposta em andamento não recria o histórico. Cada conversa tem contexto fixo; o histórico de outra conversa não é enviado ao modelo. As mensagens entram em fila e a página acompanha automaticamente a resposta. Uma falha fica visível e permite tentar novamente; o sistema não inventa uma resposta quando o Ollama está indisponível.

As conversas gerais antigas permanecem no histórico por compatibilidade, mas não são mais oferecidas no formulário. O modo processo consulta somente documentos dos casos selecionados; o acervo consulta somente o PDF local; o combinado recupera ambos. Nesses três modos, o modelo seleciona trechos e o Python confere sua correspondência com as fontes antes de publicá-los. Paráfrases jurídicas livres não são publicadas nesses modos: o teste do modelo pequeno mostrou risco de inversão do sentido de uma tese. Perguntas sobre a presença de histórico de inscrições são respondidas diretamente pelo inventário do banco.

O modelo recebe até seis interações recentes, sujeitas ao orçamento de contexto. Perguntas têm limite de 2.000 caracteres. O histórico completo continua visível na conversa. Citações verificadas comprovam a existência do trecho, não a relevância ou a aplicabilidade jurídica. As teses são de 2016 e continuam exigindo revisão.

O chat não possui ferramentas para modificar processos, aprovar revisões, acessar a internet ou executar comandos. O acesso é restrito às contas de gestor/CEO e TI; os papéis são vinculados à sessão no servidor. A escolha de cargo no cadastro ainda é livre para demonstração.

Smoke test local, incluindo compatibilidade com conversas antigas, sem alterar o histórico em uso:

```bash
python3 run.py --test-chat
```

O teste usa base temporária e salva o relatório em `docs/validacao_chat_local.json`.

Se uma aba antiga mostrar token inválido, reabra a página do chat. Um conflito entre `Referrer-Policy: no-referrer` e a checagem de origem dos formulários também foi corrigido: a página agora usa `same-origin`, mantendo a rejeição de origens externas/nulas e a validação CSRF. O diagnóstico HTTP considera essa política ao simular o envio dos formulários. O token local agora persiste no banco entre reinícios, sem desativar as verificações de CSRF e origem. Para verificar os formulários reais e o trabalhador em execução:

```bash
python3 run.py --check-chat-http
```

Esse comando cria uma conversa identificada como teste de conexão no histórico local e aguarda a resposta do modelo; não altera processos.


## Testar

```bash
python3 run.py --dev-check
```

Com o servidor rodando, verificar todas as páginas por HTTP:

```bash
python3 run.py --check-http
```

Os testes usam bases temporárias e não alteram a carteira em uso. A avaliação do painel usa dados conhecidos, não mede generalização nem qualidade jurídica. Não existem medições de produtividade humana; os valores econômicos são hipóteses editáveis.

## Segurança e limites

A entrada usa login/senha no banco e sessão opaca. O segredo legado preparado por `--secure`/Compose não é mais a credencial de login. Os papéis são ligados à conta, mas a escolha livre no cadastro é exclusivamente demonstrativa. A verificação por carteira existe no servidor e nas ferramentas, mas esta aplicação não deve receber dados pessoais reais ou ser publicada em rede.

Há token CSRF, validação de Host/Origin, escape de conteúdo, consultas SQL parametrizadas, limite de formulários e ausência de dependências externas no frontend. O SQLite usa secure_delete, mas não é criptografado; a auditoria é modificável por quem tem acesso ao arquivo e não há alta disponibilidade. O servidor HTTP da biblioteca padrão é destinado a esta demonstração local.

Os contratos normalizados não reproduzem payloads oficiais. Integração, paginação, credenciais, limites e cobertura de DataJud/DJEN continuam pendentes de validação real. Referências editoriais são paráfrases com links oficiais; as teses importadas são trechos reais da compilação histórica, não acórdãos em inteiro teor. Não há jurisprudência inventada apresentada como real.

As mitigações de prompt injection, o isolamento de contexto e os testes adversariais estão descritos em [segurança e containers](seguranca_e_containers.md). Não há garantia de imunidade a ataques desconhecidos.


## Demonstração atual: contas, coleta e comparação

- **Perfis:** gestor/CEO e TI acessam todas as áreas; advogado acessa processos da carteira fictícia Ana ou Bruno e acervo; comercial vê somente funil fictício; financeiro vê cenário financeiro e viabilidade econômica. As verificações acontecem no servidor, inclusive exportação e ações. Cadastro livre de cargo não constitui concessão segura de privilégios para produção.
- **Coleta:** a cada 60 segundos o trabalhador consulta os 6 processos fictícios nas 2 fontes locais. Repetições são deduplicadas por fonte, identidade e versão. O laboratório permite pausar a coleta, interromper fontes e gerar retificações. Não há navegação nem API judicial.
- **Triagem:** eventos mostram possível manifestação/atuação, conferência de documento ou acompanhamento, com responsável e checklist. Não se decide recurso nem prazo.
- **Avaliação:** “Comparar fluxo fixo e agente” enfileira dois percursos sobre o mesmo documento. Exibe chamadas, tempo, referências, teses, lacunas e rastros. Usa Ollama quando configurado; a contingência determinística aparece explicitamente e não conta como agente LLM validado. Não é benchmark jurídico.
- **Dados:** contas persistem no SQLite. Chats ainda são compartilhados entre gestores/TI, sem conversas privadas por usuário. Advogados não acessam o chat nesta versão. Comercial/financeiro usam valores fixos identificados como fictícios.
- **Melhorias futuras:** concessão administrativa de cargos, MFA/SSO, recuperação de senha, confirmação de e-mail, TLS, trilhas com identidade individual, segregação por escritório, privacidade de chat, proteção contra abuso de cadastro, retenção, backups testados e carga.
- **Material de preparação:** `mapa_arquitetura_apresentacao.txt`, na raiz e no `.gitignore`, contém proposta ideal, alternativas AWS/Google Cloud/Azure e roteiros. Nenhum desses serviços foi provisionado.


## Gerenciar conversas e selecionar processos

No chat, selecione o modo **Sobre um ou mais processos** para revelar as caixas de seleção dos processos disponíveis. Marque quantos desejar antes de criar a conversa. A seleção fica fixa nessa conversa. O seletor de processos aparece nos modos processo e combinado; o modo acervo ignora processos. As fontes mostram a origem de cada documento e a consulta de histórico informa a disponibilidade por processo.

Use **Renomear conversa** para salvar um nome de até 100 caracteres. O nome manual não é substituído pela primeira pergunta. Em **Excluir várias conversas**, marque os históricos, confirme a exclusão definitiva e clique em **Excluir selecionadas**. Mensagens pendentes também são removidas; uma resposta em andamento não pode recriar a conversa excluída. O indicador de espera mostra “Pensando em uma resposta…”. Chats permanecem acessíveis somente a gestor/CEO e TI e são compartilhados entre esses perfis nesta demonstração.


## Como usar o site e Minha conta

As duas páginas estão disponíveis a todos os perfis autenticados. **Como usar o site** explica o percurso, a matriz de acesso, os modos do chat, o gerenciamento de conversas e os limites da demonstração.

Em **Minha conta**, edite o nome de exibição. O login de entrada e o cargo são somente leitura. Para mudar a senha, informe a senha atual, a nova e a confirmação. A aplicação confere a credencial, gera novo salt/hash scrypt e revoga todas as sessões anteriores, mantendo uma sessão nova para o navegador que fez a alteração. A conta é obtida da sessão; enviar outro usuário ou cargo no formulário não altera esses campos. Deixe os campos de senha vazios para alterar somente o nome. Não há recuperação de senha nem MFA nesta versão.


## Exemplos estruturados no chat

Entre com uma conta **Gestor/CEO** ou **TI**, abra **Conversar com a IA** e escolha **processos** ou **ambos**. Marque os casos desejados e crie uma conversa. Os quatro botões aparecem em **Exemplos de demonstração**, enquanto a conversa estiver disponível para envio.

| Botão | Casos sugeridos | O que conferir |
| --- | --- | --- |
| **Resumir processo** | CASO-002 e CASO-003 | Alegações, pedidos, defesa, decisão, situação documental e pontos de atenção separados por processo, com referências às fontes. |
| **Preparar uma peça** | CASO-002 | Identificação da sentença existente, esclarecimento do objetivo e estrutura de inicial com campos pendentes. |
| **Conferir possível atuação** | CASO-005 e CASO-006 | Diferença entre movimentação ordinária e documento ilegível, responsável e checklist de revisão. |
| **Conferir documentos** | CASO-002 e CASO-003 | Divergência entre cronologia e fundamento do pronunciamento, além de histórico ausente. |

Também é possível escrever pedidos como “Resuma os processos selecionados”, “Como posso preparar uma petição inicial?”, “Faça a triagem operacional” e “Confira documentos ausentes e contradições”.

As respostas desses exemplos são compostas por roteiros locais com fontes recuperadas do banco atual. A interface identifica **Demonstração estruturada · fontes identificadas**. O percurso aplica as verificações de entrada e a quarentena de fontes suspeitas. As demais consultas mantêm a seleção de trechos pelo modelo local, quando necessária.

A estrutura de peça contém campos a preencher e exige revisão jurídica. Confira a fase processual, o objetivo, os documentos e a fundamentação antes de qualquer uso profissional. Os exemplos não calculam prazos nem determinam cabimento de recurso.

Para demonstrar a consulta ao estado atual, retire o histórico de CASO-002 no laboratório e repita **Conferir documentos**. A nova resposta deve apontar a ausência. Restaure o histórico ao concluir o teste. O conteúdo disponível no banco determina o resultado; as descrições acima pressupõem os documentos originais da demonstração.

A página **Como usar o site** apresenta esse mesmo percurso e os casos sugeridos.
