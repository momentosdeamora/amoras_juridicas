# Arquitetura e plano de validação do Amoras Jurídicas

A POC demonstra uma central que recebe novidades, distingue atos de expediente de decisões candidatas e prepara material rastreável para revisão humana. O recorte é negativação indevida em procedimento comum, em um tribunal fictício. Não calcula prazos, redige recursos nem realiza protocolo.

## Hipóteses

| Premissa de planejamento | Uso |
| --- | --- |
| 10 advogados, 2.000 processos ativos | Cenário econômico e referência de produção; não volume comprovado na POC. |
| 4.000 movimentações e 400 dossiês por mês | Reservar inferência para eventos relevantes. |
| Meta de atualização de até 60 minutos em horário operacional | Depende da fonte; indisponibilidade precisa aparecer no painel. |
| Economia líquida de 45 minutos por advogado por dia | Hipótese para sensibilidade, a medir incluindo revisão. |
| Responsável por cada processo | Alertas têm proprietário e revisão registrada. |
| Acesso autorizado e contexto documental suficiente | Dependências para substituir o simulador por conectores reais. |

## Componentes e consistência

O servidor Python recebe ações e renderiza HTML. Um trabalhador independente de requisições lê tarefas persistidas em SQLite. A gravação de evento e tarefa acontece na mesma transação, evitando o intervalo em que um evento existe mas seu processamento se perde.

A identidade é composta por fonte, identificador externo e versão. O hash preserva integridade do conteúdo recebido; não substitui a chave de identidade. Uma correção cria nova versão e novo alerta; a revisão anterior fica superada e permanece auditável. Outra entrega da mesma versão não cria tarefa adicional.

DataJud simulado entrega um snapshot de metadados da carteira, sem gerar alerta de decisão. DJEN simulado entrega a publicação. Eles se relacionam pelo identificador fictício do processo. Na integração real, o vínculo usaria número CNJ validado e identificadores da fonte; não se deve pressupor correspondência um a um entre movimento e publicação.

A tarefa é reivindicada em transação. Há checkpoint de classificação e conclusão; no reinício, tarefas em execução retornam à fila e o trabalho é repetido com gravações idempotentes. O checkpoint não implementa retomada exata de cada chamada do agente. Falhas terminais ficam visíveis e exigem reprocessamento manual. Há um trabalhador nesta POC; concorrência distribuída, leases e escalabilidade precisam ser projetadas antes de ampliar.

O acervo agora inclui 20 teses reais do PDF fornecido, com 12 candidatas ao recorte. A compilação histórica de 2016 é identificada como tal, sem afirmar atualidade ou substituir acórdãos integrais.

A pesquisa recebe apenas o processo autorizado. Ferramentas leem documentos desse processo e um acervo comum sem dados pessoais. Busca textual e contexto determinam pesquisas adicionais. Cada afirmação extrativa mantém identificador e trecho da evidência. Snapshots permitem inspecionar o que estava disponível no momento da execução, mesmo após remoção de um documento da carteira atual.

A checagem de citações verifica presença do trecho, não verdade, completude ou suporte lógico de uma interpretação. Contradições são encaminhadas para revisão, sem conclusão sobre cabimento de recurso. Correções do advogado são auditadas, mas não alteram automaticamente regras nem treinam o sistema.

## Entidades

- `cases`: carteira, responsável, título e cenário.
- `documents`: conteúdo autoral, origem, versão e hash.
- `refs`: paráfrases editoriais com fonte oficial e termos de recuperação.
- `events`: resposta normalizada e versionada, conteúdo, coleta e classificação.
- `tasks` e `checkpoints`: estado, tentativas, erros e marcos de processamento.
- `alerts`: pendência humana, revisão, responsável e estado.
- `dossiers` e `runs`: resultado atual e histórico de execução com evidências.
- `sources`: disponibilidade e última coleta bem-sucedida.
- `audit`: histórico funcional de ações.
- `evaluations`: resultados da regressão sintética.

## Decisões e alternativas

| Decisão | Justificativa | Quando mudar |
| --- | --- | --- |
| Biblioteca padrão Python | Executa offline, sem instalação e sem custo de serviços. | Produção exige framework, implantação e autenticação adequados. |
| SQLite e FTS5 | Dados pequenos, fila transacional e busca inspecionável. | Concorrência maior e busca semântica justificam PostgreSQL e pgvector. |
| Um servidor e um trabalhador | Reduz operação e torna falhas fáceis de reproduzir. | Volume, isolamento ou SLA justificam mais trabalhadores e fila externa. |
| Política adaptativa com Ollama opcional | Permite testar todo o fluxo sem depender de um modelo instalado. | Qwen3 1.7B foi executado localmente; ampliar avaliação jurídica e de qualidade antes de dependência operacional. |
| Dossiê extrativo | Facilita rastrear fatos e reduz geração de conteúdo sem origem. | Resumos generativos só após avaliação de fidelidade e utilidade. |
| Conectores substituíveis | Permite testar fluxo e falhas sem tráfego judicial. | Acesso real e mapeamento de campos precisam de prova específica. |

Integração própria pode oferecer controle, mas aumenta manutenção, autenticação e dependência de mudanças nos portais. Um agregador pode reduzir esse esforço, com custo e dependência contratual. Antes da escolha, comparar cobertura de documentos, frequência de atualização, tratamento de falhas e preço. Nenhum agregador foi contratado ou definido.

## Mapeamento de produção

Provedor proposto de infraestrutura: AWS. Aplicação em ECS/Fargate; banco PostgreSQL em RDS; documentos em S3 com KMS; coleta periódica via EventBridge Scheduler; fila SQS com mensagens com falha; segredos via Secrets Manager; identidade via Cognito ou identidade corporativa; operação via CloudWatch e CloudTrail, complementados por auditoria funcional.

A produção pode usar LangGraph para persistência de estado e ferramentas do agente. Inferência pode permanecer local ou usar Amazon Bedrock, conforme avaliação e condições de tratamento de dados. Modelos, custos e disponibilidade regional permanecem por selecionar. Não é necessário migrar todos os componentes simultaneamente.

Preferência inicial: região São Paulo, condicionada à disponibilidade dos serviços e ao caminho efetivo dos dados. Esta seleção não equivale a garantia de residência de todos os dados. Provedores de origem previstos: CNJ para DataJud/DJEN; legislação no Planalto e jurisprudência oficial do STJ e tribunal escolhido. Acesso, atualização e licença devem ser verificados antes de integrar.

## Avaliação

Há 12 exemplos autorais de classificação e três cenários de recuperação obrigatória. A regra ingênua encontra palavras soltas, enquanto a triagem contextual distingue o ato atual de menções a outros atos. A pesquisa fixa consulta uma base geral; a adaptativa investiga inscrição anterior e tutela conforme o caso.

A avaliação mede acurácia, recall e precisão de eventos relevantes, recuperação das referências esperadas, ferramentas chamadas, duração e integridade das âncoras. Não compara modelos LLM, não estima qualidade jurídica e não possui teste cego. Os resultados demonstram regressão em exemplos conhecidos e expõem como medir a próxima fase.

Antes de dados reais, reservar conjuntos independentes por processo, definir rótulos com advogado, registrar discordâncias e calibrar encaminhamento para revisão. As metas de recall de 98% e precisão de 90% da proposta inicial são hipóteses de negociação, não resultados atingidos ou patamares suficientes para dependência operacional.

## Segurança

A POC restringe a escuta a loopback e valida Host/Origin, token CSRF, tamanho de formulários e permissões por carteira. HTML escapa conteúdo, SQL usa parâmetros, exportações verificam autorização e ferramentas de pesquisa não acessam processos fora da carteira. Não há mecanismo de shell nem navegação livre pelo modelo opcional. O corpo de documentos não aparece no log HTTP.

Contas individuais usam login e senha no SQLite, hash scrypt e sessões revogáveis. O perfil é escolhido livremente no cadastro demonstrativo; somente gestor/CEO e TI têm acesso completo. Advogados ficam na carteira fictícia atribuída e comercial/financeiro em suas áreas; o banco e a auditoria não são criptografados ou imutáveis. Não inserir processos reais, credenciais ou dados pessoais. Antes de produção: identidade real e MFA, TLS, isolamento de rede, permissões de serviço, criptografia, retenção, descarte, backups testados e revisão contratual do tratamento de dados.

Um ataque escrito em um documento deve permanecer dado não confiável. O controlador limita a seleção do modelo às ferramentas previstas. Isso reduz a superfície; não equivale a prova de resistência a todos os ataques de prompt injection, especialmente sem avaliação do modelo local.

## Viabilidade econômica

Cenário fictício editável no painel: 10 advogados, 22 dias úteis, 45 minutos líquidos por dia e R$ 120/hora de capacidade resultam em 165 horas e R$ 19.800/mês equivalentes. Com operação de R$ 7.300/mês e investimento de R$ 60.000, o saldo equivalente é R$ 12.500/mês e retorno de 4,8 meses após aproveitamento integral.

Com 20 minutos, o saldo cai para R$ 1.500/mês e retorno para 40 meses. O equilíbrio operacional ocorre perto de 16,6 minutos por advogado por dia. A conta não representa dinheiro economizado automaticamente; depende de demanda adicional rentável ou custo efetivamente evitado. Tempo de implantação, adoção e rampa de uso aumentam o retorno contado desde o início.

A POC não contrata cloud, API ou licença comercial. Há uso do equipamento e energia locais. Custos de produção são reservas fictícias, não preços consultados. Antes de investir, medir tokens, páginas OCR, armazenamento, consultas, suporte e tempo de revisão; comparar custo por dossiê com benefício líquido por tarefa.

## Plano de implantação e critérios de decisão

Estimativa de planejamento, não compromisso: uma pessoa de engenharia e um advogado revisor, com apoio pontual de operação e segurança.

1. **Semana 1:** validar fonte real, cobertura e amostra documental autorizada. Avançar se houver acesso repetível e identificadores utilizáveis.
2. **Semanas 2 e 3:** adaptar conectores e preparar conjunto rotulado. Avançar se o fluxo preservar origem, versões e falhas sem perda silenciosa.
3. **Semana 4:** comparar políticas e modelos, com teste separado. Revisar limiares, qualidade das referências e volume de revisão humana.
4. **Semanas 5 e 6:** piloto paralelo à rotina manual. Medir tempo líquido, incidentes, custo e aceitação dos advogados.
5. **Decisão:** ampliar se critérios técnicos e benefício líquido acordados forem atingidos. Corrigir ou interromper se dados forem insuficientes, revisão consumir o ganho ou fonte não permitir operação estável.

Não retirar a rotina existente apenas por métricas em cenários sintéticos. Antes de uma ampliação, selecionar fonte, área, metas e plano de contingência com responsáveis identificados.

## Cobertura do case

| Pedido | Evidência entregue |
| --- | --- |
| Centralizar movimentações | Painel, duas fontes simuladas, linha do tempo, coleta e alertas. |
| Apoiar manifestações | Dossiê, documentos, referências, lacunas e revisão. |
| Subsistema agêntico | Ollama local com Qwen3 1.7B, tool calling nativo e política de contingência. |
| Arquitetura e informação | Componentes, entidades, transações, versões e proposta de produção. |
| Hipóteses | Premissas e limites junto de suas análises. |
| Sistemas e provedores | Tecnologias locais e mapeamento nominal de produção. |
| Economia | Calculadora editável, sensibilidade e condições de retorno. |
| Segurança | Controles testáveis e lacunas de produção declaradas. |
| Apresentação até 20 minutos | Roteiro de 18 minutos com demonstração reproduzível. |

O agente LLM já foi executado com Qwen3 1.7B em Ollama local, usando chamadas nativas de ferramentas e dados reais extraídos do PDF fornecido. O relatório operacional está em data/agent_validation.json. Isso não valida qualidade jurídica, generalização nem compatibilidade com APIs judiciais. A avaliação sintética padrão continua determinística e não deve ser confundida com o teste real do modelo.


## Atualização da demonstração: acesso e operação

Contas e sessões persistidas no SQLite substituem o login por chave compartilhada. Senhas usam scrypt e sessões opacas são revogáveis. A matriz no servidor restringe páginas, ações e exportações: gestor/CEO e TI globais; advogado na carteira fictícia atribuída; comercial e financeiro em painéis separados. O cadastro de cargo é livre apenas para a banca. A concessão administrativa de papéis, MFA, SSO e recuperação de senha são evoluções.

O trabalhador executa coleta simulada a cada 60 segundos, com pausa no laboratório. Consulta snapshots dos seis processos nas duas fontes, deduplicando repetições. Retificações continuam explícitas no laboratório; não há acesso a portais. A triagem exibe responsável, possível atuação e checklist, sem concluir necessidade jurídica de recurso ou prazo.

Avaliação inclui experimento enfileirado sobre o mesmo processo: pesquisa fixa sem LLM e adaptativa com Ollama quando configurado. Os rastros e indicadores de tempo, chamadas e recuperação são observados; contingência determinística é identificada. Essa execução não prova superioridade ou qualidade jurídica.

As áreas comercial e financeira usam números fictícios fixos. Chats ainda são compartilhados por gestor/TI; auditoria funcional mantém personas em parte dos registros. Não há isolamento multiempresa nem produção validada. O material pessoal `mapa_arquitetura_apresentacao.txt`, ignorado pelo Git, detalha o desenho ideal, as alternativas de provedores e os roteiros de slides/demo.


### Gestão do chat

`conversations.case_ids` preserva a lista de processos autorizados selecionados, mantendo `case_id` para compatibilidade com o histórico anterior. A recuperação identifica o processo de origem e verifica cada identificador. `custom_title` preserva renomeações manuais. Exclusão em lote valida os identificadores e remove conversas/mensagens em uma transação; a verificação da mensagem original antes da gravação impede resultados tardios de restaurarem históricos removidos. A seleção de processos aparece somente no modo processo, via CSS local, sem scripts externos.


### Assuntos do chat, ajuda e cadastro pessoal

O formulário oferece acervo, processos e ambos, com escolha explícita. Para manter os históricos e a restrição existente do SQLite, o combinado é persistido como modo processo com `include_acervo=1`. Recuperação do modo processo fica restrita aos documentos; combinado inclui o PDF. Conversas gerais antigas são preservadas por compatibilidade.

Todos os cargos acessam Como usar o site e Minha conta. `users.display_name` separa nome de exibição do login. A conta editada vem da sessão, sem aceitar destino ou cargo do formulário. Alteração de senha exige senha atual e confirmação, atualiza salt/hash scrypt em transação e revoga sessões anteriores, emitindo nova sessão ao próprio navegador. Cargo e login permanecem fixos. A concessão administrativa, recuperação de senha e MFA seguem propostas futuras.


### Exemplos estruturados de apoio ao advogado

O módulo `poc/chat_demonstrations.py` identifica pedidos de resumo, apoio à estrutura de peça, triagem operacional e conferência documental. Recupera o conjunto documental dos processos selecionados, preserva identificação das fontes e passa pela mesma quarentena antes da composição. Instruções suspeitas na pergunta continuam bloqueadas antes desse percurso. O modo processo preserva o limite da carteira selecionada.

A composição usa roteiros determinísticos explicitamente identificados, com trechos dos documentos e campos pendentes. Não é atribuída ao Ollama. Para resumo e preparação de peça, a recuperação inclui o contexto documental completo, evitando restringir a resposta à inicial quando a fase atual exige conferir sentença e histórico. Perguntas específicas sobre pedidos da inicial mantêm sua busca restrita à peça.

A divergência cronológica demonstrativa compara datas extraídas do histórico atual com a referência a anterioridade no pronunciamento. É um sinal de revisão, não uma conclusão jurídica ou extrator geral de relações temporais. O apoio à inicial informa a existência de sentença e solicita definir o objetivo; deixa competência, qualificação, fundamentos, valores e requerimentos em campos a conferir. Não redige recurso, calcula prazo ou protocola documento.
