# Roteiro de apresentação do Amoras Jurídicas

Duração planejada: 18 minutos, com 2 minutos de margem. A apresentação utiliza o próprio painel em localhost, sem depender da internet. Não é um deck de slides; este é o roteiro da demonstração e da defesa.

## Problema e proposta em 2 minutos

Abrir a visão geral. Apresentar as duas dores: buscar novidades em vários portais e reunir contexto para responder a uma decisão. Propor uma central que entrega novidade, evidência e pendências ao responsável.

Explicitar o recorte: negativação indevida em procedimento comum, seis casos sintéticos. O acervo combina referências editoriais com 20 teses reais extraídas do PDF histórico fornecido, identificadas por página. Fontes não estão integradas. O processamento e os registros são reais.

## Fluxo completo em 4 minutos

Clicar em Iniciar demonstração e aguardar a fila. Abrir CASO-001. Mostrar documento recebido, classificação, dossiê e evidência clicável. Registrar revisão humana. Destacar que a decisão de atuar e o julgamento jurídico permanecem com o advogado.

Abrir CASO-005 e mostrar que uma juntada não gera pesquisa ou alerta de decisão. Abrir CASO-006 e mostrar abstenção diante de documento ilegível.

## Pesquisa contextual e insuficiência em 3 minutos

Abrir CASO-002. Mostrar a divergência entre a decisão e o histórico, a pesquisa adicional sobre inscrição anterior e a pendência. Explicar que referências potencialmente pertinentes não equivalem a fundamentação jurídica aprovada.

No laboratório, retirar o histórico de CASO-002 e aguardar reprocessamento. Voltar ao processo e mostrar a ausência explícita. Inspecionar o rastro de ferramentas e o motivo de parada.

Informar o modo efetivo: Ollama local quando o modelo estiver disponível, com política determinística de contingência. Se o modelo local tiver sido configurado e testado, mostrar o modo Ollama no dossiê e quantas escolhas reais ele fez. Não atribuir raciocínio LLM ao modo padrão.

## Arquitetura e falhas em 3 minutos

Abrir Arquitetura. Explicar servidor, banco, trabalhador e contratos de entrada. Evento e tarefa são gravados na mesma transação. Relacionar DataJud a metadados e DJEN a publicações, sem criar duas decisões para o mesmo processo.

Reenviar CASO-001 no laboratório e mostrar que não duplica evento. Mostrar a auditoria. Explicar retificação com nova versão e revisão, indisponibilidade visível e retomada manual de falhas.

Apontar evolução para AWS e a necessidade de validar acesso antes de substituir os conectores sintéticos.

## Avaliação e segurança em 3 minutos

Executar Avaliação. Explicar comparação ingênua versus contextual e fixa versus adaptativa. Exibir falhas da referência inicial, referências recuperadas e custo em chamadas.

Declarar limites: exemplos conhecidos, sem avaliação cega, sem validade estatística ou validação jurídica. A próxima avaliação terá processos reais autorizados e revisão por advogado.

Entrar com uma conta de advogado e mostrar a carteira restrita; entrar com comercial e mostrar que documentos processuais são bloqueados. A escolha de cargo no cadastro é demonstrativa e exige aprovação administrativa em produção. Mencionar CSRF, proteção de HTML, ferramentas limitadas e lacunas de produção.

## Economia e decisão de investimento em 3 minutos

Abrir Viabilidade econômica. Mostrar cenário de 45 minutos e reduzir para 20. Explicar que capacidade liberada só vira lucro com demanda adicional rentável ou contratação evitada. Todos os valores são hipóteses, não preços contratados nem tempo humano medido.

Apresentar o plano de seis semanas como hipótese: acesso real, avaliação, piloto paralelo e decisão de expansão. Pedir validação de um piloto delimitado, condicionado à qualidade, benefício líquido e operação estável.

## Preparação antes de apresentar

- Iniciar o servidor e verificar a URL local.
- Usar uma base nova de demonstração, sem apagar a carteira de trabalho: `python3 run.py --port 5001 --db /tmp/amoras-apresentacao.sqlite3`.
- Ensaiar o percurso e manter o modo sem LLM se não houver modelo previamente validado.
- Não depender dos links externos durante a apresentação.
- Mostrar resultados da avaliação como regressão sintética.
- Ter a documentação de arquitetura aberta para a arguição técnica.

## Perguntas prováveis da banca

**Por que não integrar todos os portais agora?** Acesso, cobertura e autenticação são riscos independentes. O adaptador sintético permite validar o fluxo, mas a integração real continua sendo o primeiro marco externo.

**Por que usar um agente?** Quando o contexto revela inscrição anterior ou tutela, a pesquisa precisa aprofundar um ramo específico. A comparação mostra recuperação adicional e ferramentas extras. Se um fluxo fixo atingir qualidade equivalente com menor custo, ele deve ser preferido.

**Isso comprova qualidade jurídica?** Não. Comprova comportamento nos exemplos. A aplicabilidade das referências, completude e necessidade de atuar precisam de revisão jurídica.

**Por que SQLite?** É suficiente para a POC offline e oferece transações. O desenho admite evolução para PostgreSQL e fila externa quando o volume e a operação justificarem.

**Como evitar decisão perdida?** Disponibilizar eventos mesmo se a IA falhar, monitorar fonte e fila, encaminhar ambiguidades, reconciliar na integração real e manter operação paralela durante o piloto. Não prometer risco zero.

**Quanto custa?** Nenhum serviço é contratado pela POC; há recursos locais. O cenário de produção é fictício e deve ser refinado com medições de consumo e cotações.


## Percurso adicional da versão atual

Antes de apresentar, cadastrar contas por papel em `/register` e executar a comparação em Avaliação. Mostrar coleta periódica no laboratório (60s, snapshots repetidos sem duplicar), triagem com responsável no processo e rastros dos dois percursos em Avaliação. Entrar com advogado para demonstrar carteira restrita e com comercial/financeiro para mostrar áreas próprias; gestor/CEO e TI são os únicos globais. Os cargos escolhidos livremente no cadastro são uma conveniência da demo, não um fluxo aprovado de gestão de identidade. Na produção proposta entram aprovação administrativa, MFA/SSO e recuperação de senha.


## Ajuste final do percurso

Mostrar Como usar o site como orientação inicial. Em Minha conta, mostrar nome editável e cargo fixo; evitar trocar senha ao vivo para não desviar o tempo da banca. No chat, escolher explicitamente acervo, processos ou ambos e selecionar os casos nos dois últimos. Demonstrar a origem das fontes. O arquivo local ignorado `mapa_arquitetura_apresentacao.txt` contém o plano de desenho da arquitetura e o texto sugerido para cada slide; não é um deck já produzido.


## Quatro exemplos de apoio ao advogado

No chat de processo, selecionar CASO-002 e abrir **Resumir processo**: mostrar pedidos, defesa, sentença, histórico e divergência com fontes. Em **Preparar uma peça**, mostrar que a existência de sentença leva à solicitação de esclarecimento e a uma estrutura com campos pendentes. Identificar esse percurso como composição demonstrativa por roteiro local, sem geração livre atribuída ao LLM.

Como exemplos adicionais alinhados ao case, usar **Conferir possível atuação** com CASO-005/CASO-006 (ordinário versus ilegível) e **Conferir documentos** com CASO-002/CASO-003 (cronologia versus histórico ausente). Se houver tempo, retirar o histórico no laboratório e repetir a conferência para mostrar que as fontes vêm da base atual. Esses exemplos substituem parte do tour do chat; manter a apresentação completa em até 20 minutos.
