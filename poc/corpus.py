"""Importação local de teses do PDF fornecido, com página e proveniência."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from .store import DEFAULT_DB, connect, audit, now

ROOT=Path(__file__).resolve().parent.parent
PDF=ROOT/'Cadastro de Inadimplentes.pdf'
DOC_ID='STJ-JT59-2016'
WARNING='Compilação histórica de teses de 2016; não é inteiro teor de acórdão nem repositório oficial. Atualidade e aplicabilidade não verificadas.'
IN_SCOPE={1,3,4,7,8,9,10,12,13,17,18,19}
TAGS={1:'negativação indevida dano moral',3:'pagamento exclusão cinco dias úteis',4:'notificação prévia órgão mantenedor',7:'súmula 385 inscrição anterior preexistente legítima',8:'súmula 385 credor tema 922',9:'aviso recebimento notificação súmula 404',10:'tutela exclusão multa diária',12:'tutela urgência débito caução',13:'cinco anos cadastro prescrição',17:'prescrição ciência inscrição',18:'prescrição indenização três anos',19:'mera cobrança ausência negativação dano moral'}


def schema(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS corpus_documents(id TEXT PRIMARY KEY,title TEXT,filename TEXT,hash TEXT,pages INTEGER,published TEXT,declared_cutoff TEXT,kind TEXT,warning TEXT,imported TEXT);
    CREATE TABLE IF NOT EXISTS corpus_chunks(id TEXT PRIMARY KEY,document_id TEXT REFERENCES corpus_documents(id),page INTEGER,thesis INTEGER,title TEXT,body TEXT,precedents TEXT,tags TEXT,in_scope INTEGER,UNIQUE(document_id,thesis));
    ''')
    try:
        con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS corpus_fts USING fts5(chunk_id UNINDEXED,title,body,tags,tokenize="unicode61 remove_diacritics 2")')
    except Exception:
        pass


def normalize(text):
    text=re.sub(r'([A-Za-zÀ-ÿ])-\s*\n\s*([A-Za-zÀ-ÿ])',r'\1\2',text)
    text=re.sub(r'([0-9])-\s*\n\s*([A-Z])',r'\1-\2',text)
    return re.sub(r'\s+',' ',text).strip()


def parse_pages(text):
    rows=[]
    for page_no,page in enumerate(text.split('\f'),1):
        matches=list(re.finditer(r'(?m)^\s*(\d{1,2})\)\s+',page))
        for i,m in enumerate(matches):
            n=int(m.group(1))
            segment=page[m.end():matches[i+1].start() if i+1<len(matches) else len(page)]
            segment=re.split(r'Os entendimentos foram extraídos',segment)[0]
            parts=re.split(r'Precedentes:\s*',segment,maxsplit=1)
            thesis=normalize(parts[0]); precedents=normalize(parts[1]) if len(parts)>1 else ''
            rows.append({'id':f'{DOC_ID}-T{n:02d}','page':page_no,'thesis':n,'title':f'Tese {n} · {thesis[:85]}','body':thesis,'precedents':precedents,'tags':TAGS.get(n,''),'in_scope':int(n in IN_SCOPE)})
    if sorted(r['thesis'] for r in rows)!=list(range(1,21)):
        raise ValueError('O arquivo não corresponde às 20 teses esperadas da edição 59. Importação interrompida.')
    return rows


def import_pdf(path=DEFAULT_DB,force=False):
    if not PDF.exists(): return {'imported':False,'reason':'PDF não encontrado'}
    sha=hashlib.sha256(PDF.read_bytes()).hexdigest()
    with connect(path) as con:
        schema(con)
        old=con.execute('SELECT hash FROM corpus_documents WHERE id=?',(DOC_ID,)).fetchone()
        if old and old[0]==sha and not force: return {'imported':False,'reason':'Arquivo já importado','chunks':con.execute('SELECT count(*) FROM corpus_chunks WHERE document_id=?',(DOC_ID,)).fetchone()[0]}
    result=subprocess.run(['pdftotext','-layout',str(PDF),'-'],capture_output=True,check=True,timeout=30)
    rows=parse_pages(result.stdout.decode('utf-8'))
    with connect(path) as con:
        con.execute('INSERT OR REPLACE INTO corpus_documents VALUES(?,?,?,?,?,?,?,?,?,?)',(DOC_ID,'STJ · Jurisprudência em Teses 59 · Cadastro de Inadimplentes',PDF.name,sha,8,'2016-06-08','2016-04-29','compilação de teses',WARNING,now()))
        con.execute('DELETE FROM corpus_chunks WHERE document_id=?',(DOC_ID,))
        try: con.execute('DELETE FROM corpus_fts')
        except Exception: pass
        for r in rows:
            con.execute('INSERT INTO corpus_chunks VALUES(?,?,?,?,?,?,?,?,?)',(r['id'],DOC_ID,r['page'],r['thesis'],r['title'],r['body'],r['precedents'],r['tags'],r['in_scope']))
            try: con.execute('INSERT INTO corpus_fts VALUES(?,?,?,?)',(r['id'],r['title'],r['body'],r['tags']))
            except Exception: pass
        audit(con,'acervo_importado',f'{PDF.name}: 20 teses, 8 páginas; SHA-256 {sha[:16]}.')
    return {'imported':True,'chunks':len(rows),'in_scope':sum(r['in_scope'] for r in rows),'sha256':sha}


def search(query,path=DEFAULT_DB,limit=3,include_outside=False):
    from .engine import plain
    thesis_match=re.search(r'\btese\s*(\d{1,2})\b',plain(query))
    tokens=[t for t in re.findall(r'[a-z0-9]+',plain(query)) if len(t)>3 or t.isdigit()][:16]
    if not tokens: return []
    with connect(path) as con:
        # O esquema é criado na inicialização/importação, nunca durante pesquisa concorrente.
        scope='' if include_outside else ' AND c.in_scope=1'
        if thesis_match:
            try:
                found=con.execute('SELECT c.*,d.published,d.warning,d.hash document_hash FROM corpus_chunks c JOIN corpus_documents d ON d.id=c.document_id WHERE c.thesis=?'+scope,(int(thesis_match.group(1)),)).fetchall()
                return [{**dict(r),'citation':f'STJ · JT 59 · tese {r["thesis"]} · página {r["page"]}','url':f'/corpus.pdf#page={r["page"]}'} for r in found]
            except Exception:return []
        try:
            result=con.execute('SELECT c.*,d.published,d.warning,d.hash document_hash FROM corpus_fts f JOIN corpus_chunks c ON c.id=f.chunk_id JOIN corpus_documents d ON d.id=c.document_id WHERE corpus_fts MATCH ?'+scope+' ORDER BY bm25(corpus_fts) LIMIT ?',(' OR '.join(tokens),limit)).fetchall()
        except Exception:
            result=[]
            try:
                candidates=con.execute('SELECT c.*,d.published,d.warning,d.hash document_hash FROM corpus_chunks c JOIN corpus_documents d ON d.id=c.document_id WHERE 1=1'+scope).fetchall()
                scored=[(sum(t in plain(r['body']+' '+r['tags']) for t in tokens),r) for r in candidates]
                result=[r for score,r in sorted(scored,key=lambda v:v[0],reverse=True) if score>0][:limit]
            except Exception:
                return []
        # Uma consulta numérica explícita não deve ser satisfeita apenas pela palavra "súmula".
        if '385' in tokens:
            result=[r for r in result if '385' in r['body'] or '385' in r['tags']]
        return [{**dict(r),'citation':f'STJ · JT 59 · tese {r["thesis"]} · página {r["page"]}','url':f'/corpus.pdf#page={r["page"]}'} for r in result]
