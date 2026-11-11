"""Respostas demonstrativas estruturadas, fundamentadas nos documentos recuperados.

A composição é determinística. Não atribuir esses resultados à inferência do LLM.
"""
import re
from datetime import datetime

EXAMPLES=[
 ('Resumir processo','Resuma os processos selecionados com fatos, pedidos, defesa, decisão e pontos de atenção.'),
 ('Preparar uma peça','Como posso preparar uma petição inicial para os processos selecionados? Considere a fase processual e indique as informações pendentes.'),
 ('Conferir possível atuação','Faça a triagem operacional dos processos selecionados: existe decisão para revisão e possível manifestação?'),
 ('Conferir documentos','Confira documentos ausentes e contradições nos processos selecionados antes de preparar uma manifestação.'),
]

def intent(question):
    from .engine import plain
    q=plain(question)
    if any(w in q for w in ('peticao','minuta','peca')) and any(w in q for w in ('como','prepare','preparar','elabore','redija','crie','estrutur','fazer','preciso de')):return 'peca'
    if any(w in q for w in ('resuma','resumir','resumo','sintetize')):return 'resumo'
    if any(w in q for w in ('triagem operacional','possivel manifestacao','preciso me manifestar','preciso recorrer')):return 'triagem'
    if any(w in q for w in ('documentos ausentes','contradicoes','documentos faltando','quais documentos faltam')):return 'conferencia'
    return None


def compose(session,sources,kind,blocked):
    from .chat import session_cases
    from .engine import classify,plain
    sections=[];used={}
    for cid in session_cases(session):
        docs={s['kind']:s for s in sources if s.get('case_id')==cid}
        lines=[cid]
        owner=next((s.get('owner') for s in docs.values() if s.get('owner')),None)
        if owner:lines.append('Responsável na carteira fictícia: '+owner+'.')
        def evidence(key,label):
            source=docs.get(key)
            if source:
                used[source['id']]=source
                lines.append(f"{label}: {source['body']} [{source['id']}]")
            else:lines.append(label+': documento seguro não disponível no contexto atual.')
        event=docs.get('evento')
        category=classify(event['body'])[0] if event else 'incerto'
        if kind=='resumo':
            for key,label in [('inicial','Alegações e pedidos da parte autora'),('contestacao','Argumentos da defesa'),('contrato','Situação documental da contratação'),('evento','Pronunciamento disponível'),('historico','Histórico para conferência')]:evidence(key,label)
        elif kind=='peca':
            evidence('evento','Fase indicada pelo documento disponível')
            if category=='sentenca':lines.append('Já existe uma sentença neste conjunto. Confirme se deseja analisar a petição inicial existente, preparar uma inicial para outro caso ou reunir subsídios para uma manifestação posterior. A peça adequada depende dessa definição e da revisão do advogado.')
            elif category=='incerto':lines.append('O documento disponível não permite confirmar a fase processual. Solicite inteiro teor legível antes de definir a peça.')
            else:lines.append('Confirme a fase e o objetivo da peça com o advogado antes de usar a estrutura abaixo.')
            lines.append('Estrutura de trabalho para uma petição inicial, caso esse seja o objetivo confirmado:\n1. Endereçamento: [órgão competente a confirmar].\n2. Qualificação e representação: [dados das partes e procuração].\n3. Fatos e cronologia: usar os documentos conferidos abaixo.\n4. Fundamentos: [dispositivos e precedentes pertinentes, com atualidade e aplicabilidade revisadas].\n5. Pedidos: [formular conforme objetivo e provas disponíveis].\n6. Provas, valor da causa e requerimentos: [preencher e conferir].')
            evidence('inicial','Informações existentes para a seção de fatos e pedidos')
            evidence('contrato','Prova da contratação a conferir')
            evidence('historico','Cronologia disponível')
            lines.append('Dados ainda necessários à preparação: qualificação completa, representação, competência, documentos originais, valores, objetivo específico e conferência de eventual intimação. Os campos acima são um roteiro demonstrativo, sem validade para protocolo.')
        elif kind=='triagem':
            evidence('evento','Ato que fundamenta a triagem')
            label={'sentenca':'Revisar possível manifestação','decisao':'Revisar possível atuação','ordinaria':'Acompanhar movimentação ordinária','incerto':'Solicitar documento legível e conferir natureza do ato'}[category]
            lines.append('Encaminhamento operacional: '+label+'.')
            lines.append('Checklist de revisão: conferir inteiro teor, intimação, pedidos, resultado, documentos e responsável. A necessidade de manifestação e os prazos dependem de análise humana. A presença da palavra sentença em um documento não determina, por si só, sua natureza.')
        else:
            for key,label in [('evento','Decisão ou movimentação a conferir'),('contrato','Comprovação da contratação'),('historico','Cronologia das inscrições')]:evidence(key,label)
            lines.append('Documentos a obter ou conferir: inteiro teor legível, registros originais da contratação, histórico com cobertura identificada, intimação e representação processual. Disponibilidade de um resumo sintético não equivale à comprovação desses documentos.')
        if kind in {'resumo','conferencia','peca'}:
            hist=docs.get('historico')
            if hist and event:
                dates=re.findall(r'\b\d{2}/\d{2}/\d{4}\b',hist['body'])
                chronology=False
                if len(dates)>=2:
                    try:chronology=datetime.strptime(dates[1],'%d/%m/%Y')>datetime.strptime(dates[0],'%d/%m/%Y')
                    except ValueError:pass
                if chronology and 'anterior' in plain(event['body']):
                    used[hist['id']]=hist;used[event['id']]=event
                    lines.append(f"Ponto de atenção: o pronunciamento menciona inscrição anterior, enquanto o histórico registra a outra inscrição em data posterior à discutida. A divergência exige conferência dos documentos originais e da legitimidade da inscrição. [{event['id']}] [{hist['id']}]")
            if not hist:lines.append('Lacuna: histórico seguro indisponível. Não é possível confirmar anterioridade ou legitimidade a partir desse documento.')
            if category=='incerto':lines.append('Limite: o ato não pôde ser classificado com segurança. Conferir documento original legível.')
        sections.append('\n\n'.join(lines))
    if not sections:sections=['Selecione um ou mais processos no modo processo ou combinado para usar este exemplo.']
    answer='\n\n'.join(sections)+'\n\nDemonstração com documentos sintéticos. Composição por roteiro local e fontes identificadas; revisão jurídica necessária.'
    if blocked:answer+=' Fontes suspeitas foram isoladas e não foram usadas na composição.'
    return {'answer':answer,'sources':list(used.values()),'metrics':{'model':None,'llm_used':False,'reason':'demonstracao_estruturada','demo_intent':kind,'input_tokens':0,'output_tokens':0,'duration_ms':0,'quarantined_sources':blocked,'composition':'deterministic_grounded_template'}}
