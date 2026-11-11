# Avaliação do PDF Cadastro de Inadimplentes

## Decisão

O documento serve como acervo inicial de recuperação para a POC de negativação indevida. Ele é uma compilação temática de teses, não uma coleção de acórdãos em inteiro teor. A POC preserva essa distinção na interface, nos dossiês e na ferramenta oferecida ao modelo.

## Identificação verificada no arquivo

- Publicação: STJ, Jurisprudência em Teses, edição 59, Cadastro de Inadimplentes.
- Data indicada: 8 de junho de 2016.
- Estrutura: oito páginas, vinte teses, referências a precedentes e súmulas.
- Corte declarado no rodapé: precedentes publicados até 29 de abril de 2016.
- SHA-256: `751cd95d25b6fda895c94e3a8b080061b64431006d7f70dba765253d3d926539`.
- Extração: texto nativo com pdftotext, sem OCR; espaços e palavras quebradas em linhas são normalizados.
- Inspeção visual: capa e página 3, incluindo a tese 7 e a identificação da Súmula 385.

A ressalva institucional na primeira página informa que as teses resumidas não constituem repositórios oficiais de jurisprudência. Além disso, a tese 8 inclui referência a publicação no DJe em 16/05/2016, posterior ao corte declarado no rodapé. A importação preserva ambas as informações sem presumir uniformidade temporal ou atualidade em 2026.

## Seleção temática inicial

| Tese | Página | Tema para recuperação |
| --- | --- | --- |
| 1 | 1 | Inscrição indevida e dano moral. |
| 3 | 2 | Exclusão após pagamento. |
| 4 | 2 | Notificação prévia. |
| 7 | 3 | Inscrição legítima preexistente e Súmula 385. |
| 8 | 3 | Discussão em face do credor e Súmula 385. |
| 9 | 4 | Comunicação e aviso de recebimento. |
| 10 | 4 | Multa para cumprimento da exclusão. |
| 12 | 5 | Tutela em discussão de débito, com contexto específico a conferir. |
| 13 | 5 | Permanência do registro e prescrição. |
| 17 | 7 | Ciência do registro e prescrição. |
| 18 | 7 | Prazo de pretensão indenizatória. |
| 19 | 7 | Distinção entre cobrança e negativação. |

As doze teses são candidatas a recuperação, não proposições automaticamente aplicáveis aos seis casos. As outras oito também foram importadas, mas ficam fora da pesquisa padrão para reduzir mistura com alimentos, recuperação judicial e dívida tributária, entre outros assuntos.

## Incorporação à solução

`poc/corpus.py` extrai cada tese e mantém número, página, texto, precedentes citados, data do documento, hash e classificação temática. SQLite FTS5 permite pesquisa lexical; existe fallback lexical se FTS5 não estiver disponível. A busca nunca acessa o portal do STJ.

A aba Acervo jurídico real permite pesquisar e abrir o PDF original no localhost. O agente recebe trechos extraídos e citações com página. Os dossiês separam referências editoriais de trechos reais do PDF. O texto livre do modelo não é aceito como fundamento jurídico.

## O que ainda não está validado

- Autenticidade por comparação binária com uma cópia obtida diretamente do site: o arquivo usado foi fornecido pelo usuário e apresenta a identificação institucional.
- Vigência ou atualidade das teses e sua aplicabilidade a um processo real.
- Conteúdo integral e contexto dos acórdãos citados.
- Qualidade jurídica das escolhas do modelo.

## Complementos sugeridos a partir da lista fornecida

A edição 59 permanece como núcleo. A edição 125, Responsabilidade Civil — Dano Moral, é a candidata mais direta a complemento, condicionada à leitura. Edições de Direito do Consumidor podem fornecer teses adicionais pertinentes. A edição 282, Superendividamento, justifica outro recorte e não precisa ser acrescentada ao atual somente por ser recente.

As datas 30/11/1899 que aparecem na lista devem ser tratadas como metadados inválidos ou ausentes, não como data de publicação confirmada. A coluna de última versão não substitui a verificação do documento e das fontes atuais.
