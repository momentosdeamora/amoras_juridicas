# Segurança e execução isolada do Amoras Jurídicas

## Estado de execução

O projeto tem Poetry 2.2.1 instalado de forma isolada em `.tools/poetry-env`, ambiente `.venv`, dependências de desenvolvimento travadas em `poetry.lock` e configuração Compose validada com Docker Compose standalone 2.40.3. As imagens base foram resolvidas no registry oficial e fixadas por digest; o registro está em `docs/container_images.json`.

Não há Docker Engine, Podman, socket Docker ou dependências de Docker rootless neste ambiente. Os containers foram preparados e sua configuração foi validada, mas não foram construídos nem executados aqui. O painel local pode continuar funcionando com Poetry e o Ollama local já instalado. Não é correto afirmar que está rodando dentro de containers neste host.

## Ambiente virtual

```bash
python3 run.py --prepare-dev
python3 run.py --dev-check
python3 run.py --serve-dev --secure
```

O bootstrap usa o virtualenv da distribuição oficial PyPA para contornar a ausência de ensurepip, sem sudo. Poetry fica em um ambiente próprio; o Python da aplicação e as dependências de desenvolvimento ficam em `.venv`. Nenhum pacote de aplicação exige cloud ou API paga.

Com Poetry já instalado em outro ambiente:

```bash
poetry install
poetry run pytest -q
poetry run python run.py --secure
```

O login usa contas no SQLite, senha com hash scrypt e sessões opacas revogáveis de oito horas (HttpOnly e SameSite=Strict). O cadastro é livre e permite escolher o cargo apenas para demonstração; gestor/CEO e TI têm visão completa, advogado somente carteira atribuída e acervo, comercial/financeiro suas áreas. `--secure` ainda prepara o segredo legado `.secrets/access_token`, sem usá-lo como senha de entrada. MFA/SSO, aprovação de cargos, recuperação de senha e TLS ficam para produção.

## Containers

Com Docker Engine e Compose disponíveis:

```bash
python3 run.py --init-security
docker compose build
```

Reutilizar o modelo já existente, sem baixar os pesos novamente:

```bash
docker compose --profile setup run --rm model-import
```

Alternativa para um host sem os pesos locais:

```bash
docker compose --profile setup run --rm model-download
```

Esse último comando acessa o registry de modelos para download, não para inferência. Somente o serviço de preparação usa a rede bootstrap com acesso externo. Não execute importação/download simultaneamente ao serviço de inferência usando o mesmo volume.

Iniciar aplicação e modelo:

```bash
docker compose up -d app
```

Se a versão local já ocupar a porta 5000, encerre-a ou use outra porta:

```bash
FAROL_PORT=5001 docker compose up -d app
```

O painel exige login e senha de uma conta cadastrada no banco. O arquivo `.secrets/access_token` permanece um segredo legado de implantação, não uma credencial de usuário. A aplicação publica somente em 127.0.0.1. Ollama não publica porta no host. Aplicação e inferência usam exclusivamente uma rede Compose interna, sem saída externa. O backend aceito é o serviço interno fixo `ollama:11434`; URLs arbitrárias são rejeitadas.

Os dois serviços usam usuários não root, filesystem somente leitura, diretórios temporários limitados, limites de memória/CPU/PIDs, todas as capabilities removidas e no-new-privileges. Não há montagem do socket Docker. Os dados da aplicação usam o diretório atual `data`, mantendo a carteira e o histórico existentes. Os pesos e o estado do Ollama usam volumes próprios.

Para verificar a configuração sem engine:

```bash
python3 run.py --check-containers
```

Esse comando valida o Compose com uma distribuição oficial cujo checksum foi conferido. Ele não comprova build, funcionamento do isolamento em runtime, permissões dos volumes ou conectividade entre containers; esses itens permanecem para teste com engine. Em um host com UID diferente de 1000, as permissões do bind mount de dados e do segredo precisam ser ajustadas antes de iniciar.

## Exclusão de conversa

Selecione uma conversa e clique em Excluir conversa. A tela seguinte mostra a ação concreta e exige confirmação. GET não exclui nada; o POST exige gestor, acesso ao ambiente quando configurado, origem válida e token CSRF.

A exclusão remove a conversa e suas mensagens em uma transação. Se uma inferência já estiver em andamento, sua resposta é descartada ao terminar, sem recriar o histórico. A auditoria mantém apenas o identificador da exclusão, sem preservar o conteúdo da conversa. SQLite usa secure_delete, mas isso não garante eliminação forense de WAL, backups, snapshots ou memória do modelo.

## Mitigações de prompt injection

As fronteiras de acesso e execução são os controles principais. A detecção textual é uma camada adicional e pode ter falsos positivos ou deixar passar ataques desconhecidos.

1. **Sem autoridade para agir:** o chat não recebe ferramentas de escrita, shell, arquivos ou rede. Uma resposta não altera processos ou revisões. A exclusão é uma ação da interface, nunca uma ferramenta do modelo.
2. **Contexto separado:** documentos são serializados em um envelope JSON de dados não confiáveis em mensagem user. Não são concatenados ao papel system. O servidor define os papéis e o processo autorizado.
3. **Isolamento por conversa e processo:** o contexto usa somente a sessão e o processo selecionados. O histórico enviado é limitado e passa por inspeção antes de voltar ao modelo.
4. **Inspeção e quarentena:** entradas e fontes passam por regras para overrides, spoofing de papéis, pedidos de segredos, execução de código e exfiltração. Há normalização Unicode, remoção de caracteres invisíveis, decodificação limitada de entidades/percent-encoding e inspeção de payloads explicitamente apresentados como base64.
5. **Ferramentas limitadas:** o agente usa allowlist de ferramentas, argumentos exatos, processo fixo, limite de chamadas/rodadas e rejeição de buscas suspeitas. Documentos e resultados suspeitos são isolados antes da inferência.
6. **Saída estruturada:** respostas precisam seguir o contrato; IDs desconhecidos e citações que não correspondem à fonte são rejeitados. Nos modos jurídicos, só são publicados trechos conferidos, sem paráfrases livres do modelo pequeno.
7. **Segredos fora do prompt:** a chave do ambiente não entra no contexto e seu envio no chat é rejeitado antes de persistir a mensagem. As credenciais ficam fora do build e do controle de versão.
8. **Limites operacionais:** tamanho de entrada/saída, timeout HTTP, orçamento de contexto, fila limitada e limitação de requisições e tentativas de login reduzem abuso de recursos.
9. **Rastreabilidade:** eventos de bloqueio e isolamento registram identificadores e regras, sem copiar o payload para a auditoria.

Os testes incluem ataque direto, instrução em documento, histórico contaminado, Unicode invisível, base64, tentativa de ferramenta desconhecida, acesso a outro processo e saída maliciosa. Passar nesses casos conhecidos não comprova imunidade a prompt injection. Avaliações adversariais mais amplas e revisão contínua continuam necessárias.

## Referências técnicas

- [OWASP sobre prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).
- [Poetry e ambientes virtuais](https://python-poetry.org/docs/basic-usage/).
- [Redes internas no Docker Compose](https://docs.docker.com/reference/compose-file/networks/).


## Cadastro pessoal e contextos do chat

Todos os perfis autenticados podem editar somente o próprio nome de exibição e senha em Minha conta. O usuário é determinado pela sessão. Login/cargo não são campos de atualização; alterar o HTML ou enviar parâmetros extras não concede privilégios. Senha atual e confirmação são exigidas para trocar senha; sessões antigas são revogadas e uma nova é emitida ao navegador atual. Valores de senhas não entram na auditoria.

O chat separa os escopos acervo, processos e combinado. Fontes processuais mantêm o identificador do processo e todas as seleções são conferidas no banco. O perfil que acessa o chat continua restrito a gestor/CEO e TI. A página Como usar o site está disponível a todos sem ampliar o acesso a outras áreas.
