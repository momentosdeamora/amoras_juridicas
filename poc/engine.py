"""Triagem, pesquisa adaptativa e trabalhador persistente. Sem serviços externos."""
import json
import os
import re
import threading
import time
import unicodedata
from .fixtures import EVAL_EVENTS
from .store import DEFAULT_DB, allowed, audit, connect, jsondump, now


def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))


def classify(text):
    t=plain(text).strip()
    # Priorizar o ato atual, em vez de confundir menção a sentença com uma sentença.
    if t.startswith(('certidao','juntada','peticao juntada','despacho','remessa','expedicao de certidao')):
        return 'ordinaria','Ato atual de expediente; menção a decisão não altera sua natureza.'
    if any(x in t for x in ('ilegivel','ocr:','sem descricao')) or len(t)<30:
        return 'incerto','Texto insuficiente ou extração ilegível; exige revisão humana.'
    if t.startswith('sentenca') or re.search(r'\bjulgo\s+(parcialmente\s+)?(improcedente|procedente|extinto)',t):
        return 'sentenca','Pronunciamento identificado por título ou dispositivo; conferir o documento original.'
    if any(x in t for x in ('decisao interlocutoria','defiro a tutela','indefiro o pedido de tutela')):
        return 'decisao','Decisão sobre pedido ou tutela identificada no conteúdo.'
    return 'incerto','Sem evidência suficiente nas regras locais; revisão necessária.'


def baseline(text):
    t=plain(text)
    if 'sentenca' in t: return 'sentenca'
    if 'decisao' in t or 'tutela' in t: return 'decisao'
    return 'ordinaria'


def search_refs(con, query):
    words=re.findall(r'[a-z0-9]+',plain(query))
    words=[w for w in words if len(w)>3][:10]
    if not words: return []
    try:
        rows=con.execute('SELECT r.* FROM search_index s JOIN refs r ON r.id=s.ref_id WHERE search_index MATCH ? ORDER BY bm25(search_index) LIMIT 3',(' OR '.join(words),)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        scored=[]
        for r in con.execute('SELECT * FROM refs'):
            score=sum(w in plain(r['title']+' '+r['body']+' '+r['tags']) for w in words)
            if score: scored.append((score,dict(r)))
        return [r for _,r in sorted(scored,key=lambda x:x[0],reverse=True)[:3]]


def research(case_id, event_body, category, path=DEFAULT_DB, profile='gestor', adaptive=True, use_llm=True):
    start=time.perf_counter()
    trace=[]; evidence=[]; refs={}; gaps=[]; findings=[]; tools_used=set()
    with connect(path) as con:
        if not allowed(con,case_id,profile): raise PermissionError('Acesso ao processo negado')
        available=['ler_decisao','consultar_documentos','buscar_base_legal']
        if adaptive: available += ['investigar_inscricao_anterior','buscar_tutela']
        plan=['ler_decisao','consultar_documentos','buscar_base_legal']
        prior='anterior' in plain(event_body) or 'preexistente' in plain(event_body)
        if adaptive and prior: plan.append('investigar_inscricao_anterior')
        if adaptive and category=='decisao': plan.append('buscar_tutela')
        llm_requested=bool(os.environ.get('POC_OLLAMA_MODEL')) and use_llm
        llm_choices=0
        for step in range(6):
            pending=[x for x in plan if x not in tools_used]
            if not pending: break
            objective=event_body+'\nResultados já obtidos: '+jsondump(trace[-2:])
            # A política permanece como preparação determinística e contingência.
            # O agente nativo executa sua própria pesquisa abaixo, com resultados de ferramentas.
            chosen=None
            tool=chosen or pending[0]
            if chosen: llm_choices+=1
            tools_used.add(tool)
            reason='Escolha do modelo local, validada contra ferramentas permitidas.' if chosen else 'Política adaptativa local baseada nas evidências e lacunas.'
            result=''
            if tool=='ler_decisao':
                evidence.append({'id':'EVENTO','title':'Documento do evento recebido','text':event_body,'kind':'evento','version':1,'source':'Publicação sintética recebida'})
                findings.append({'claim':'Conteúdo do pronunciamento recebido','evidence':'EVENTO','quote':event_body})
                result='Documento preservado; resumo extrativo evita inventar fundamentos.'
            elif tool=='consultar_documentos':
                docs=con.execute('SELECT * FROM documents WHERE case_id=? ORDER BY kind',(case_id,)).fetchall()
                for doc in docs:
                    if doc['kind']=='evento': continue
                    evidence.append({'id':doc['id'],'title':doc['title'],'text':doc['body'],'kind':doc['kind'],'version':doc['version'],'source':doc['origin']})
                if not any(d['kind']=='historico' for d in docs):
                    gaps.append('Histórico de inscrições ausente. Não confirmar anterioridade nem legitimidade com os documentos disponíveis.')
                result=f'{len(docs)} documentos encontrados no processo autorizado.'
            elif tool=='buscar_base_legal':
                found=search_refs(con,'consumidor cadastro inscricao prova contrato')
                refs.update({r['id']:r for r in found})
                result=f'{len(found)} referências recuperadas por busca textual local.'
            elif tool=='investigar_inscricao_anterior':
                found=search_refs(con,'anterior preexistente legitimidade moral')
                refs.update({r['id']:r for r in found})
                hist=con.execute("SELECT * FROM documents WHERE case_id=? AND kind='historico'",(case_id,)).fetchone()
                if hist:
                    if 'posterior' in plain(hist['body']):
                        findings.append({'claim':'Conflito temporal a conferir: o histórico descreve outra inscrição posterior, enquanto o pronunciamento menciona inscrição anterior.','evidence':hist['id'],'quote':hist['body']})
                        gaps.append('Conflito entre decisão e histórico. A análise de aplicabilidade da Súmula 385 exige revisão humana e confirmação da legitimidade.')
                    else:
                        gaps.append('A referência a inscrição anterior exige conferência de cobertura, datas e legitimidade do histórico.')
                    result='Histórico examinado; comparação contextual de anterioridade e legitimidade.'
                else:
                    result='Busca não encontrou histórico; insuficiência explicitada, sem inferência substitutiva.'
            elif tool=='buscar_tutela':
                found=search_refs(con,'tutela urgencia exclusao')
                refs.update({r['id']:r for r in found})
                result='Pesquisa direcionada à tutela; mérito permanece distinto da medida provisória.'
            trace.append({'step':step+1,'tool':tool,'reason':reason,'result':result})
        if category=='incerto': gaps.append('Pronunciamento ilegível ou ambíguo. Obter documento legível antes de definir sua natureza ou avaliar atuação.')
        checks=[]
        by_id={e['id']:e for e in evidence}
        for f in findings:
            supported=f['evidence'] in by_id and f['quote'] in by_id[f['evidence']]['text']
            checks.append({'claim':f['claim'],'evidence':f['evidence'],'supported':supported})
        if not all(c['supported'] for c in checks):
            raise ValueError('Verificação de integridade das citações falhou')
        jurisprudence=[]; native=None; llm_error=None
        if category != 'incerto':
            from .corpus import search,WARNING
            if llm_requested and adaptive:
                from .local_agent import run_agent
                try:
                    native=run_agent(case_id,event_body,path,profile)
                    llm_choices=native['calls']
                    for item in native['trace']:
                        trace.append({**item,'step':len(trace)+1})
                    jurisprudence=native['retrieved']
                    if not native['sufficient_tools']:
                        gaps.append('O agente local não completou consulta documental e pesquisa. Usada recuperação determinística de contingência.')
                except Exception as exc:
                    llm_error=str(exc)[:250]
                    gaps.append('Ollama indisponível ou resposta inválida; pesquisa continuou pela política local. '+llm_error)
            if not jurisprudence:
                query='consumidor cadastro inscrição prova contrato' if not adaptive else '385 inscrição anterior preexistente legítima' if prior else 'tutela exclusão multa' if category=='decisao' else 'inscrição indevida dano moral'
                jurisprudence=search(query,path,limit=3)
                if jurisprudence:
                    trace.append({'step':len(trace)+1,'tool':'busca_pdf_local','reason':'Recuperação textual determinística no PDF importado.','result':f'{len(jurisprudence)} teses recuperadas com página e proveniência.'})
            if jurisprudence:
                gaps.append(WARNING)
                for row in jurisprudence:
                    evidence.append({'id':row['id'],'title':row['citation'],'text':row['body'],'kind':'tese_real','version':1,'source':'PDF fornecido: Cadastro de Inadimplentes.pdf','page':row['page'],'document_hash':row['document_hash']})
                    checks.append({'claim':row['citation'],'evidence':row['id'],'supported':True})
        trace.append({'step':len(trace)+1,'tool':'verificar_e_encerrar','reason':'Pesquisa delimitada e verificações concluídas.','result':'Âncoras verificadas por correspondência textual. Isso não comprova validade jurídica das conclusões.'})
        mode='Revisão humana · documento ilegível, sem inferência LLM' if category=='incerto' else 'Ollama local · tool calling nativo' if native and llm_choices else 'Política adaptativa local (fallback de Ollama)' if llm_requested else 'Política adaptativa local (sem LLM)' if adaptive else 'Pesquisa fixa de referência'
        return {'case_id':case_id,'category':category,'mode':mode,'trace':trace,'evidence':evidence,'findings':findings,'references':list(refs.values()),'gaps':list(dict.fromkeys(gaps)),
                'checks':checks,'duration_ms':round((time.perf_counter()-start)*1000,2),'calls':native['calls'] if native else len(tools_used),'llm_choices':llm_choices,
                'jurisprudence':jurisprudence,'llm':{k:v for k,v in native.items() if k not in ('trace','retrieved')} if native else None,'llm_error':llm_error,
                'status':'revisao_necessaria' if gaps else 'pronto_para_revisao','stop_reason':'Pesquisa delimitada concluída; decisão jurídica reservada ao advogado.',
                'notice':'Documentos processuais sintéticos. Referências editoriais são paráfrases. Teses do PDF, quando presentes, são trechos de compilação histórica de 2016, não acórdãos integrais.'}


def recover(path=DEFAULT_DB):
    with connect(path) as con:
        count=con.execute("UPDATE tasks SET status='pendente',updated=? WHERE status='executando'",(now(),)).rowcount
        if count: audit(con,'retomada',f'{count} tarefa(s) recuperada(s) após reinício.')


def process_one(path=DEFAULT_DB):
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        if con.execute("SELECT value FROM settings WHERE key='worker_paused'").fetchone()[0]=='1': return False
        task=con.execute("SELECT t.id task_id,t.attempts,e.* FROM tasks t JOIN events e ON e.id=t.event_id WHERE t.status='pendente' ORDER BY t.id LIMIT 1").fetchone()
        if not task: return False
        task=dict(task)
        con.execute("UPDATE tasks SET status='executando',attempts=attempts+1,updated=? WHERE id=?",(now(),task['task_id']))
    try:
        with connect(path) as con:
            fault=con.execute("SELECT value FROM settings WHERE key='fail_next'").fetchone()
            if fault and fault[0]=='1':
                con.execute("UPDATE settings SET value='0' WHERE key='fail_next'")
                inject=True
            else: inject=False
        if inject: raise RuntimeError('Interrupção sintética antes da classificação. Tarefa preservada para retomada manual.')
        if task['source'] == 'DataJud simulado':
            category,reason='ordinaria','Sincronização de metadados. Não equivale a uma publicação judicial e não gera alerta de decisão.'
        else:
            category,reason=classify(task['body'])
        with connect(path) as con:
            con.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)',(task['task_id'],'classificado',jsondump({'category':category,'reason':reason}),now()))
        dossier=research(task['case_id'],task['body'],category,path=path) if category!='ordinaria' else None
        with connect(path) as con:
            con.execute('UPDATE events SET category=?,reason=? WHERE id=?',(category,reason,task['id']))
            if category!='ordinaria':
                con.execute('INSERT OR IGNORE INTO alerts(event_id,case_id,at) VALUES(?,?,?)',(task['id'],task['case_id'],now()))
                reopened=con.execute("UPDATE alerts SET status='pendente' WHERE event_id=? AND status='revisado'",(task['id'],)).rowcount
                if reopened:
                    audit(con,'revisao_reaberta','Dossiê recalculado; a revisão anterior continua na auditoria e uma nova validação é necessária.',task['case_id'])
            if dossier:
                con.execute('INSERT OR REPLACE INTO dossiers VALUES(?,?,?,?)',(task['id'],task['case_id'],jsondump(dossier),now()))
                con.execute('INSERT INTO runs(event_id,at,mode,body) VALUES(?,?,?,?)',(task['id'],now(),dossier['mode'],jsondump(dossier)))
            # Revisão antiga permanece auditável; versão nova abre sua própria tarefa.
            if task['version']>1:
                con.execute("UPDATE alerts SET status='superado' WHERE event_id IN (SELECT id FROM events WHERE source=? AND external_id=? AND version<?)",(task['source'],task['external_id'],task['version']))
            con.execute("UPDATE tasks SET status='concluida',error=NULL,updated=? WHERE id=?",(now(),task['task_id']))
            con.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)',(task['task_id'],'concluido','{}',now()))
            audit(con,'processado',f'Evento {task["id"]}: {category}.',task['case_id'])
    except Exception as exc:
        with connect(path) as con:
            con.execute("UPDATE tasks SET status='falhou',error=?,updated=? WHERE id=?",(str(exc)[:300],now(),task['task_id']))
            audit(con,'tarefa_falhou',str(exc)[:300],task['case_id'])
    return True


def worker(stop, path=DEFAULT_DB):
    from .chat import recover_chat,process_chat_one
    from .demo_operations import collect_tick,compare_pending
    recover(path)
    recover_chat(path)
    with connect(path) as con:
        con.execute("UPDATE settings SET value='falhou' WHERE key='comparison_state' AND value='executando'")
    while not stop.is_set():
        try:
            collect_tick(path)
            worked=process_chat_one(path) or process_one(path) or compare_pending(path)
        except Exception:
            worked=False
        stop.wait(.25 if worked else 1)


def evaluate(path=DEFAULT_DB):
    """Teste de regressão sintético; não é medição de qualidade jurídica real."""
    start=time.perf_counter(); rows=[]
    for text,expected in EVAL_EVENTS:
        predicted,reason=classify(text)
        rows.append({'text':text,'expected':expected,'actual':predicted,'baseline':baseline(text),'reason':reason})
    relevant={'sentenca','decisao'}
    tp=sum(r['expected'] in relevant and r['actual'] in relevant for r in rows)
    positives=sum(r['expected'] in relevant for r in rows)
    emitted=sum(r['actual'] in relevant for r in rows)
    comparisons=[]
    requirements={'CASO-002':{'REF-S385'},'CASO-003':{'REF-S385'},'CASO-004':{'REF-CPC300'}}
    for cid,expected_refs in requirements.items():
        with connect(path) as con:
            text=con.execute("SELECT body FROM documents WHERE case_id=? AND kind='evento'",(cid,)).fetchone()[0]
        cat,_=classify(text)
        fixed=research(cid,text,cat,path,adaptive=False,use_llm=False)
        adaptive=research(cid,text,cat,path,adaptive=True,use_llm=False)
        def result(d):
            retrieved={r['id'] for r in d['references']}
            return {'required_found':sorted(expected_refs & retrieved),'required_total':len(expected_refs),'calls':d['calls'],'duration_ms':d['duration_ms'],'anchors_ok':all(c['supported'] for c in d['checks']),'gaps':len(d['gaps'])}
        comparisons.append({'case_id':cid,'expected_refs':sorted(expected_refs),'fixed':result(fixed),'adaptive':result(adaptive)})
    report={'rows':rows,'accuracy':sum(r['actual']==r['expected'] for r in rows)/len(rows),'baseline_accuracy':sum(r['baseline']==r['expected'] for r in rows)/len(rows),'recall':tp/positives if positives else 0,'precision':tp/emitted if emitted else 0,'n':len(rows),'comparisons':comparisons,'duration_ms':round((time.perf_counter()-start)*1000,2),'at':now(),'limitation':'Amostra sintética pequena, autoral e conhecida. Teste de regressão, sem estimativa de generalização, avaliação jurídica ou significância estatística. Nenhum tempo humano foi medido.'}
    with connect(path) as con:
        con.execute('INSERT INTO evaluations(at,body) VALUES(?,?)',(now(),jsondump(report)))
        audit(con,'avaliacao','Regressão sintética executada; resultados não representam dados reais.')
    return report
