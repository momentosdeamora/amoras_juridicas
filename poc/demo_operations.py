"""Coleta e experimentos locais: nenhuma chamada a portais judiciais."""
import json
import os
import time
from .store import connect,ingest,now,audit,jsondump
from .fixtures import CASES

INTERVAL=60

def collect_tick(path,clock=None):
    clock=time.time() if clock is None else clock
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        settings=dict(con.execute('SELECT key,value FROM settings'))
        if settings.get('collector_enabled','1')!='1' or clock-float(settings.get('collector_tick','0'))<INTERVAL:return False
        con.execute("INSERT OR REPLACE INTO settings VALUES('collector_tick',?)",(str(clock),))
    accepted=0
    for case in CASES:
        for source in ('DataJud simulado','DJEN simulado'):
            created,_=ingest(case[0],source=source,path=path)
            accepted+=int(created)
    with connect(path) as con:
        con.execute("INSERT OR REPLACE INTO settings VALUES('collector_last',?)",(now(),))
        audit(con,'coleta_periodica',f'12 consultas locais; {accepted} eventos novos. Reconciliação por identidade e versão; sem acesso externo.')
    return True

def operational_triage(category,owner):
    status={'sentenca':'Revisar possível manifestação','decisao':'Revisar possível atuação','incerto':'Conferir documento antes da triagem','ordinaria':'Acompanhar movimentação'}
    return {'status':status.get(category,'Aguardar classificação'),'owner':owner,
            'checklist':'Conferir inteiro teor, intimação, histórico e documentos; advogado decide necessidade de atuação e prazo.' if category in {'sentenca','decisao'} else 'Solicitar documento legível e validar natureza do ato.' if category=='incerto' else 'Não foi identificado ato decisório pelas regras da demonstração.',
            'notice':'Triagem operacional demonstrativa; não determina cabimento de recurso nem calcula prazo.'}

def compare_pending(path):
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        pending=con.execute("SELECT value FROM settings WHERE key='comparison_pending'").fetchone()
        if not pending:return False
        cid=pending[0]
        con.execute("DELETE FROM settings WHERE key='comparison_pending'")
        con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_state','executando')")
    try:
        from .engine import classify,research
        with connect(path) as con:text=con.execute("SELECT body FROM documents WHERE case_id=? AND kind='evento'",(cid,)).fetchone()[0]
        category,_=classify(text)
        fixed=research(cid,text,category,path,adaptive=False,use_llm=False)
        agent=None
        native_error=None
        if os.environ.get('POC_OLLAMA_MODEL') and category!='incerto':
            try:
                from .local_agent import run_agent
                native=run_agent(cid,text,path)
                if not native['sufficient_tools']:raise ValueError('Ferramentas mínimas não completadas.')
                agent={'mode':'Ollama local · tool calling nativo independente','calls':native['calls'],'duration_ms':native['duration_ms'],'llm_choices':native['calls'],'llm_error':None,'trace':native['trace'],'gaps':[], 'references':[], 'jurisprudence':native['retrieved']}
            except Exception as exc:native_error=type(exc).__name__
        if agent is None:
            agent=research(cid,text,category,path,adaptive=True,use_llm=False)
            agent['mode']='Contingência determinística · sem execução válida do agente'
            agent['llm_error']=native_error
        def measure(d):
            return {k:d[k] for k in ('mode','calls','duration_ms','llm_choices','llm_error','trace','gaps')} | {'references':[r['id'] for r in d['references']],'theses':[r['id'] for r in d['jurisprudence']]}
        report={'case':cid,'at':now(),'fixed':measure(fixed),'agent':measure(agent),'native_agent':bool(agent['llm_choices']),'limitation':'Uma execução sintética. Fluxo fixo e agente independente acessam a mesma base, por percursos distintos. Chamadas locais e tool calls têm naturezas diferentes. Contagens não medem relevância, suporte jurídico ou superioridade. Sem rótulos independentes.'}
        with connect(path) as con:
            con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_report',?)",(jsondump(report),))
            con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_state','concluido')")
            audit(con,'comparacao','Fluxo fixo e agente/política executados sobre o mesmo documento.',cid)
    except Exception:
        with connect(path) as con:con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_state','falhou')")
    return True
