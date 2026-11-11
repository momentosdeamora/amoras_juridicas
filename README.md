<p align="center">
  <img src="static/img/logotipo.webp" alt="Logotipo Amoras Jurídicas" width="100">
</p>

# Amoras Jurídicas

**Acompanhamento processual e pesquisa jurídica assistida por IA local.**

O protótipo centraliza movimentações simuladas, identifica eventos para revisão e reúne documentos e evidências em dossiês com registro de origem. O advogado analisa os resultados e define o encaminhamento jurídico.

> **Projeto desenvolvido para um case de AI Engineer.** A execução é local, com processos fictícios, fontes judiciais simuladas e um PDF histórico do STJ. Integrações com tribunais e serviços de nuvem fazem parte da proposta de evolução.

## Telas da aplicação

Capturas do protótipo local com processos e indicadores demonstrativos.

### Visão geral

Indicadores da carteira, triagem das publicações e etapas do processamento.

![Visão geral](static/img/aplicacao/tela_03_visao_geral.png)

### Processos e dossiês

Seleção de casos, documentos, eventos e pendências de revisão.

![Processos e dossiês](static/img/aplicacao/tela_08_processos_e_dossies.png)

### Resumo de processos no chat

Exemplo de resposta estruturada com identificação das fontes e pontos de atenção.

![Resumo de processos no chat](static/img/aplicacao/tela_09_conversar_com_a_IA_04.png)

<details>
<summary>Acesso, orientação e conta</summary>

### Login

![Login](static/img/aplicacao/tela_01_login.png)

### Cadastro

![Cadastro](static/img/aplicacao/tela_02_cadastro.png)

### Como usar o site

![Como usar o site](static/img/aplicacao/tela_04_como_usar_o_site.png)

### Minha conta

![Minha conta](static/img/aplicacao/tela_05_minha_conta.png)

</details>

<details>
<summary>Visões comercial e financeira</summary>

### Comercial

![Comercial](static/img/aplicacao/tela_06_comercial.png)

### Financeiro

![Financeiro](static/img/aplicacao/tela_07_financeiro.png)

</details>

<details>
<summary>Outras telas do chat</summary>

### Chat: captura 1

![Chat: captura 1](static/img/aplicacao/tela_09_conversar_com_a_IA_01.png)

### Chat: captura 2

![Chat: captura 2](static/img/aplicacao/tela_09_conversar_com_a_IA_02.png)

### Chat: captura 3

![Chat: captura 3](static/img/aplicacao/tela_09_conversar_com_a_IA_03.png)

</details>

<details>
<summary>Operação, avaliação e arquitetura</summary>

### Laboratório de eventos

![Laboratório de eventos](static/img/aplicacao/tela_09_laboratorio.png)

### Avaliação

![Avaliação](static/img/aplicacao/tela_10_avaliacao.png)

### Acervo jurídico

![Acervo jurídico](static/img/aplicacao/tela_11_acervo_juridico.png)

### Arquitetura

![Arquitetura](static/img/aplicacao/tela_12_arquitetura.png)

### Viabilidade econômica

![Viabilidade econômica](static/img/aplicacao/tela_13_viabilidade.png)

### Segurança e operação

![Segurança e operação](static/img/aplicacao/tela_14_seguranca.png)

### Trilha de auditoria

![Trilha de auditoria](static/img/aplicacao/tela_15_auditoria.png)

</details>

## Objetivos e públicos

| Público | Conteúdo disponível |
| --- | --- |
| **Gestão** | Novidades, responsáveis e pendências em uma central; hipóteses econômicas com análise de sensibilidade. |
| **RH e recrutamento** | Aplicação de conhecimentos de IA e engenharia de software a um problema de negócio, com documentação das decisões e limitações. |
| **Engenharia** | Agente local com ferramentas restritas, alternativa de fluxo fixo, processamento persistente, idempotência, autorização e testes. |
| **Equipe jurídica** | Documentos, fontes e lacunas reunidos para revisão. A decisão de recorrer e a análise de prazos ficam sob responsabilidade do advogado. |

## Do evento à revisão humana

```mermaid
flowchart LR
    A[Fontes simuladas] --> B[Coleta periódica]
    B --> C[Evento versionado e fila]
    C --> D[Triagem operacional]
    D --> E[Pesquisa fixa ou agente local]
    E --> F[Dossiê com evidências]
    F --> G[Revisão pelo advogado]
    H[Documentos fictícios e PDF STJ] --> E
```

O ciclo de coleta ocorre a cada **60 segundos**. Reenvios são deduplicados; retificações preservam versões. Eventos ordinários, possíveis decisões e documentos insuficientes recebem encaminhamentos distintos. Fontes indisponíveis e falhas de processamento ficam visíveis no painel.

## Desenhos da arquitetura

### C4 nível 1: contexto do protótipo

Pessoas, responsabilidades e uso da Amoras Jurídicas.

[![C4 nível 1: contexto do protótipo](static/img/c4_contexto.png)](static/img/c4_contexto.svg)

### C4 nível 2: containers do protótipo

Aplicação Python, SQLite, Ollama e arquivos locais. O trabalhador executa em uma thread da aplicação Python.

[![C4 nível 2: containers do protótipo](static/img/c4_containers.png)](static/img/c4_containers.svg)

Os diagramas C4 usam fonte Inter e a paleta `#19414a` / `#efeee9`. Os SVGs contêm a fonte incorporada. Para gerar novamente, use `python3 scripts/gerar_c4.py` com Inter instalada; a exportação PNG utiliza `rsvg-convert`. Convenções: [contexto C4](https://c4model.com/diagrams/system-context) e [containers C4](https://c4model.com/diagrams/container).

### Arquitetura funcional do protótipo

Fluxos implementados de acesso, coleta simulada, persistência, pesquisa, chat e revisão humana.

![Arquitetura funcional do protótipo local](static/img/arquitetura_desenhada_prototipo.png)

### Arquitetura proposta para produção

Integrações autorizadas, identidade, mensageria, processamento, controles operacionais e alternativas de infraestrutura. Os serviços representados dependem de seleção e validação para implantação.

![Arquitetura proposta para produção](static/img/arquitetura_desenhada_producao.jpg)

## Funcionalidades

- **Agente versus fluxo fixo:** execute os dois percursos sobre o mesmo caso e inspecione chamadas, tempo, fontes e rastros. A contingência determinística é identificada.
- **Dossiês com fontes:** os dossiês preservam trechos e origem; contradições e documentos ausentes aparecem como pendências.
- **IA local:** Ollama com Qwen3 1.7B, ferramentas de leitura delimitadas e validação de argumentos. As ferramentas disponíveis ao modelo são limitadas à consulta de documentos e jurisprudência.
- **Controles de segurança:** senha com hash scrypt, sessões revogáveis, autorização no servidor, CSRF, consultas parametrizadas e defesas de prompt injection em camadas.
- **Persistência e processamento:** SQLite transacional, fila persistente, histórico de execução, auditoria funcional e testes automatizados.

A avaliação utiliza casos sintéticos e registra tempo, chamadas e fontes recuperadas. A qualidade jurídica e o ganho de produtividade dependem de avaliação independente.

## Tecnologias utilizadas

| Tecnologia | Aplicação no projeto |
| --- | --- |
| **Python 3.12 a 3.14** | Servidor HTTP, regras de negócio, processamento em segundo plano e geração das páginas. |
| **SQLite e FTS5** | Persistência de contas, sessões, processos, conversas e tarefas; busca textual com alternativa lexical quando FTS5 estiver indisponível. |
| **Ollama** | Execução do modelo de linguagem no equipamento local. |
| **Qwen3 1.7B** | Respostas estruturadas e seleção de ferramentas para pesquisa jurídica. |
| **HTML, CSS e SVG** | Interface, seleção condicional de campos e gráficos locais. |
| **Poppler / pdftotext** | Extração do conteúdo do PDF de jurisprudência. |
| **Poetry e virtualenv** | Gerenciamento de dependências, lockfile e isolamento do ambiente Python. |
| **pytest** | Testes automatizados de regras, fluxos, segurança e protocolo HTTP. |
| **PyYAML** | Leitura e verificação da configuração dos containers nos testes. |
| **Docker e Docker Compose** | Configuração de empacotamento, serviços, volumes e rede. Build e execução pendentes de validação com Docker Engine. |
| **scrypt e hashlib, da biblioteca padrão Python** | Hash de senhas com salt e hash dos tokens de sessão. |

A orquestração do agente utiliza código Python próprio e chamadas nativas de ferramentas do Ollama. A recuperação combina busca textual e trechos com referência à origem. Embeddings, banco vetorial e OCR estão previstos como possibilidades de evolução conforme os resultados da avaliação.

## Execução local

Requisitos: Python **3.12 a 3.14**. A importação do PDF usa **Poppler/pdftotext**. Para conversar com a IA, é necessário Ollama com o modelo instalado; aplicação e inferência usam o equipamento local.

```bash
python3 run.py --prepare-dev
python3 run.py --serve-dev
```

Abra **http://localhost:5000**, clique em **Criar minha conta** e escolha seu perfil. O primeiro acesso exige a criação de uma conta. O campo de carteira fictícia aparece somente para **Advogado**.

O cadastro e a escolha de cargo são livres exclusivamente para a demonstração. Use uma senha exclusiva para este protótipo. A instalação do modelo é feita por comando explícito. O processamento utiliza os recursos do equipamento local.

Para configurar Ollama, importar o PDF, executar diagnósticos ou usar outro banco, consulte o [guia de execução local](docs/guia_execucao_local.md).

## Roteiro de avaliação

1. Cadastre uma conta **Gestor/CEO** ou **TI** para conhecer todas as áreas.
2. Abra **Como usar o site** e acompanhe um ciclo de coleta no laboratório.
3. Em **Processos**, compare um caso completo, um contraditório e um documento ilegível. Confira a triagem, o responsável e as fontes do dossiê.
4. Em **Avaliação**, execute a comparação entre fluxo fixo e agente; inspecione o modo efetivamente utilizado.
5. No chat, escolha **acervo**, **processos** ou **ambos**. Selecione vários processos, confira as fontes e organize o histórico com renomeação ou exclusão em lote.
6. Abra a **Viabilidade econômica** e altere as hipóteses para visualizar a sensibilidade do retorno.

Os seis casos, os valores comerciais e financeiros e os cenários de falha são demonstrativos. Os indicadores do painel representam as hipóteses e os dados dessa demonstração.

## Exemplos de demonstração no chat

Crie uma conversa no modo **processos** ou **ambos** e selecione os casos. O painel oferece quatro exemplos:

| Exemplo | Conteúdo da resposta |
| --- | --- |
| **Resumir processo** | Alegações, pedidos, defesa, situação documental, pronunciamento e pontos de atenção, separados por processo e vinculados às fontes. |
| **Preparar uma peça** | Conferência da fase processual, estrutura de trabalho com campos pendentes e documentos necessários. Quando há sentença, solicita esclarecer o objetivo antes de preparar uma inicial. |
| **Conferir possível atuação** | Triagem operacional do ato, responsável e checklist de revisão. A necessidade de manifestação e os prazos ficam sujeitos à análise do advogado. |
| **Conferir documentos** | Documentos disponíveis, lacunas e divergências de cronologia identificadas nos registros atuais. |

Esses exemplos usam composição determinística com documentos recuperados, identificação das fontes e isolamento de conteúdo suspeito. A interface identifica o modo como demonstração estruturada. O restante do chat mantém o modelo local para seleção de trechos verificáveis. O roteiro de peça contém campos a preencher e exige revisão jurídica antes de qualquer uso profissional.

Para apresentar: selecione **CASO-002** e compare a sentença com o histórico; inclua **CASO-003** para mostrar a ausência de histórico; use **CASO-005** e **CASO-006** para comparar movimento ordinário e documento ilegível. As respostas consultam a base atual, portanto a retirada de um documento no laboratório altera o resultado.

## Perfis de acesso

| Perfil | Áreas disponíveis |
| --- | --- |
| **Gestor/CEO e TI** | Todas as áreas. |
| **Advogado** | Processos da carteira fictícia atribuída e acervo jurídico. |
| **Comercial** | Funil comercial com dados fictícios. |
| **Financeiro** | Cenário financeiro fictício e viabilidade econômica. |
| **Todos os perfis** | Como usar o site e Minha conta. |

Em **Minha conta**, a pessoa pode alterar nome de exibição e senha. Login e cargo permanecem fixos. A troca de senha exige a senha atual e confirmação, revoga as sessões anteriores e mantém uma nova sessão no navegador atual.

Os chats são compartilhados entre Gestor/CEO e TI nesta versão. O isolamento por escritório e a privacidade de conversas por usuário estão previstos para evolução.

## Implementação e evolução

| Implementado no protótipo | Próxima validação para produção |
| --- | --- |
| Coleta de snapshots locais, versões e deduplicação | Acesso autorizado, cobertura e reconciliação de fontes reais. |
| Triagem por regras, abstenção e revisão humana | Avaliação independente com rotulagem por advogado. |
| Pesquisa textual e PDF histórico com proveniência | Atualização jurídica, cobertura documental e OCR quando necessário. |
| Contas, sessões e autorização por papel/carteira | Aprovação administrativa de cargos, MFA/SSO, recuperação de senha e segregação por escritório. |
| Agente local e comparação com registro de execução | Relevância das evidências, qualidade, custo e desempenho em piloto. |
| Poetry, ambiente virtual e configuração de containers | Build e execução dos containers, carga e restauração de backups. |

O ambiente verificado usa Poetry e Ollama locais. Dockerfiles e Compose estão preparados, com configuração validada. O build e a execução dos containers dependem de validação em um ambiente com Docker Engine. AWS, Google Cloud e Azure são alternativas documentadas para a arquitetura de produção.

O PDF de jurisprudência é a edição **59/2016 do STJ**, uma compilação histórica. A atualidade, a relevância e a aplicabilidade dos trechos exigem revisão jurídica. As defesas de prompt injection incluem validações de entrada, isolamento de fontes suspeitas e restrição de ferramentas; sua eficácia exige avaliação contínua.

## Validação e documentação

```bash
python3 run.py --dev-check
```

A suíte utiliza bancos temporários. O relatório de ambiente registra **118 testes e 9 subtestes aprovados**, além de verificações HTTP e execuções locais. A cobertura inclui comportamentos de software. Qualidade jurídica e generalização permanecem como etapas de avaliação.

| Material | Conteúdo |
| --- | --- |
| [Arquitetura e validação](docs/arquitetura_e_validacao.md) | Hipóteses, dados, decisões, limitações e critérios do piloto. |
| [Guia de execução](docs/guia_execucao_local.md) | Comandos, modelo local, diagnóstico e percurso detalhado. |
| [Segurança e containers](docs/seguranca_e_containers.md) | Controles, isolamento, configuração e melhorias futuras. |
| [Roteiro da apresentação](docs/roteiro_apresentacao.md) | Defesa do case e demonstração em até 20 minutos. |
| [Avaliação do PDF](docs/avaliacao_pdf_cadastro.md) | Origem, recorte e limitações do acervo histórico. |
| [Relatório de ambiente](docs/ambiente_validacao.json) | Evidências registradas de execução e testes. |
