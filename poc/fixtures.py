"""Fixtures autorais: nenhuma identidade ou numeração processual real."""
CASES = [
    ('CASO-001', 'Contrato não reconhecido', 'Completo', 'Consumidor A', 'Ana', 'sentenca', False, False),
    ('CASO-002', 'Inscrição anterior controversa', 'Contradição', 'Consumidor B', 'Ana', 'sentenca', True, False),
    ('CASO-003', 'Histórico de crédito ausente', 'Incompleto', 'Consumidor C', 'Bruno', 'sentenca', True, True),
    ('CASO-004', 'Pedido urgente de exclusão', 'Tutela', 'Consumidor D', 'Bruno', 'decisao', False, False),
    ('CASO-005', 'Juntada de comprovante', 'Ordinário', 'Consumidor E', 'Ana', 'ordinaria', False, False),
    ('CASO-006', 'Decisão digitalizada ilegível', 'Abstenção', 'Consumidor F', 'Bruno', 'incerto', False, True),
]
REFERENCES = [
    ('REF-CDC6', 'CDC artigo 6º', 'Direitos básicos e prova', 'Direitos básicos do consumidor incluem reparação de danos e facilitação da defesa, nos termos e condições do dispositivo. A inversão do ônus da prova depende de apreciação judicial.', 'https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm', 'consumidor prova reparacao'),
    ('REF-CDC14', 'CDC artigo 14', 'Prestação de serviços', 'O dispositivo disciplina a responsabilidade do fornecedor por defeitos na prestação do serviço e as hipóteses de exclusão previstas no próprio artigo.', 'https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm', 'contrato servico responsabilidade'),
    ('REF-CDC43', 'CDC artigo 43', 'Cadastros de consumidores', 'O artigo disciplina acesso, características e correção das informações em cadastros de consumidores, além da comunicação de abertura de cadastro nas condições legais.', 'https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm', 'negativacao cadastro inscricao'),
    ('REF-S385', 'STJ Súmula 385', 'Inscrição legítima preexistente', 'A orientação trata da repercussão de uma inscrição legítima preexistente sobre a indenização moral por anotação irregular, preservando o direito ao cancelamento. Verificar anterioridade e legitimidade no caso concreto.', 'https://scon.stj.jus.br/SCON/sumstj/toc.jsp?livre=%22385%22.num.', 'anterior preexistente legitimidade moral'),
    ('REF-CPC373', 'CPC artigo 373', 'Ônus da prova', 'O artigo distribui o ônus da prova e prevê condições para distribuição diversa. O enquadramento de cada fato depende do caso e da apreciação judicial.', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105compilada.htm', 'prova contrato legitimidade'),
    ('REF-CPC300', 'CPC artigo 300', 'Tutela de urgência', 'A tutela de urgência exige elementos relacionados à probabilidade do direito e ao perigo de dano ou risco ao resultado útil, observadas as demais condições do dispositivo.', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105compilada.htm', 'tutela urgencia exclusao'),
]
# Corpus independente de avaliação: expectativas autorais, sem validação jurídica.
EVAL_EVENTS = [
 ('Sentença: julgo parcialmente procedentes os pedidos.', 'sentenca'),
 ('SENTENÇA. Julgo improcedente o pedido de reparação.', 'sentenca'),
 ('Decisão interlocutória. Defiro a tutela de urgência.', 'decisao'),
 ('Indefiro o pedido de tutela de urgência. Intimem-se.', 'decisao'),
 ('Juntada de documento pela parte autora.', 'ordinaria'),
 ('Certidão de remessa dos autos ao cartório.', 'ordinaria'),
 ('Expedição de documento.', 'incerto'),
 ('OCR: $% [trecho ilegível]', 'incerto'),
 ('Certidão: a sentença foi publicada ontem.', 'ordinaria'),
 ('Petição juntada: requer a reforma da sentença.', 'ordinaria'),
 ('Despacho: intime-se a parte para regularizar a representação.', 'ordinaria'),
 ('Movimentação sem documento e sem descrição.', 'incerto'),
]

def documents(case):
    cid, title, tag, person, owner, kind, prior, missing = case
    docs = [
      ('inicial', 'Petição inicial', f'Caso fictício {cid}. O consumidor não reconhece a contratação. Pede declaração de inexistência da dívida, exclusão da inscrição e análise de reparação moral. Documento sintético para avaliação técnica.'),
      ('contestacao', 'Contestação', 'O fornecedor sustenta regularidade da cobrança. A contratação não foi demonstrada neste conjunto de documentos. As alegações da defesa não são fatos incontroversos.'),
      ('contrato', 'Informação sobre contratação', 'Não foi apresentado contrato assinado ou registro verificável de contratação. Esta observação descreve somente o conjunto sintético disponível.'),
    ]
    if not missing:
        if prior:
            text = 'Histórico sintético: inscrição discutida em 15/02/2025. Outra inscrição ocorreu em 10/03/2025. A segunda inscrição é posterior, em conflito com a anterioridade referida na decisão. A legitimidade não está comprovada por este extrato.'
        else:
            text = 'Histórico sintético: inscrição discutida em 15/02/2025. Não constam outras inscrições neste extrato. Isso não comprova a inexistência de registros fora da cobertura do documento.'
        docs.append(('historico', 'Histórico de inscrições', text))
    if kind == 'sentenca':
        reason = 'O pedido de dano moral é rejeitado porque a decisão considera existir inscrição anterior legítima. Conferir o histórico e a legitimidade dessa inscrição.' if prior else 'A decisão declara inexistência do débito e determina retirada da inscrição. O pedido de reparação moral foi acolhido neste exemplo fictício.'
        event = 'SENTENÇA. Julgo parcialmente procedentes os pedidos. ' + reason
    elif kind == 'decisao':
        event = 'DECISÃO INTERLOCUTÓRIA. Defiro a tutela de urgência para exclusão provisória da inscrição. A análise do mérito e a verificação da contratação permanecem pendentes.'
    elif kind == 'ordinaria':
        event = 'JUNTADA de comprovante. Movimentação ordinária sem julgamento de pedido ou decisão sobre tutela.'
    else:
        event = 'OCR: $% [trecho ilegível]. Tipo de pronunciamento não recuperado. Documento incompleto; exigir revisão humana.'
    docs.append(('evento', 'Documento do evento', event))
    return docs
