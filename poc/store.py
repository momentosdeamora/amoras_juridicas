import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .fixtures import CASES, REFERENCES, documents

DEFAULT_DB = Path(os.environ.get('FAROL_DATA_DIR',str(Path(__file__).resolve().parent.parent / 'data'))) / 'poc.sqlite3'

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

@contextmanager
def connect(path=DEFAULT_DB):
    con = sqlite3.connect(str(path), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA secure_delete=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def audit(con, action, detail, case_id=None, actor='sistema'):
    con.execute('INSERT INTO audit(at,actor,action,case_id,detail) VALUES(?,?,?,?,?)', (now(), actor, action, case_id, detail))

def csrf_token(path=DEFAULT_DB,candidate=None):
    import secrets
    with connect(path) as con:
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('csrf_token',?)",(candidate or secrets.token_urlsafe(32),))
        return con.execute("SELECT value FROM settings WHERE key='csrf_token'").fetchone()[0]

def init(path=DEFAULT_DB):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS user_sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,title TEXT,tag TEXT,person TEXT,owner TEXT,expected TEXT);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,case_id TEXT REFERENCES cases(id),kind TEXT,title TEXT,body TEXT,hash TEXT,version INTEGER DEFAULT 1,origin TEXT);
        CREATE TABLE IF NOT EXISTS refs(id TEXT PRIMARY KEY,title TEXT,topic TEXT,body TEXT,url TEXT,tags TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,source TEXT,external_id TEXT,case_id TEXT REFERENCES cases(id),version INTEGER,body TEXT,hash TEXT,at TEXT,category TEXT DEFAULT 'pendente',reason TEXT, UNIQUE(source,external_id,version));
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,event_id INTEGER UNIQUE REFERENCES events(id),status TEXT DEFAULT 'pendente',attempts INTEGER DEFAULT 0,error TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY,event_id INTEGER UNIQUE REFERENCES events(id),case_id TEXT REFERENCES cases(id),status TEXT DEFAULT 'pendente',note TEXT DEFAULT '',reviewer TEXT,at TEXT);
        CREATE TABLE IF NOT EXISTS dossiers(event_id INTEGER PRIMARY KEY REFERENCES events(id),case_id TEXT REFERENCES cases(id),body TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,event_id INTEGER REFERENCES events(id),at TEXT,mode TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at TEXT,actor TEXT,action TEXT,case_id TEXT,detail TEXT);
        CREATE TABLE IF NOT EXISTS sources(name TEXT PRIMARY KEY,status TEXT,last_attempt TEXT,last_success TEXT,message TEXT);
        CREATE TABLE IF NOT EXISTS checkpoints(task_id INTEGER PRIMARY KEY REFERENCES tasks(id),stage TEXT,body TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY,at TEXT,body TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY,title TEXT,mode TEXT CHECK(mode IN ('geral','processo','acervo')),case_id TEXT REFERENCES cases(id),created TEXT,updated TEXT);
        CREATE TABLE IF NOT EXISTS chat_turns(id INTEGER PRIMARY KEY,conversation_id INTEGER REFERENCES conversations(id),question TEXT NOT NULL,answer TEXT,status TEXT CHECK(status IN ('pendente','executando','concluida','falhou')),sources TEXT DEFAULT '[]',metrics TEXT DEFAULT '{}',error TEXT,request_key TEXT UNIQUE NOT NULL,created TEXT,updated TEXT);
        CREATE INDEX IF NOT EXISTS chat_queue ON chat_turns(status,id);
        ''')
        chat_columns={r['name'] for r in con.execute('PRAGMA table_info(conversations)')}
        if 'case_ids' not in chat_columns:con.execute("ALTER TABLE conversations ADD COLUMN case_ids TEXT NOT NULL DEFAULT '[]'")
        if 'include_acervo' not in chat_columns:con.execute("ALTER TABLE conversations ADD COLUMN include_acervo INTEGER NOT NULL DEFAULT 0")
        if 'custom_title' not in chat_columns:con.execute("ALTER TABLE conversations ADD COLUMN custom_title INTEGER NOT NULL DEFAULT 0")
        columns={r['name'] for r in con.execute('PRAGMA table_info(users)')}
        if 'role' not in columns:con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'advogado'")
        if 'display_name' not in columns:con.execute("ALTER TABLE users ADD COLUMN display_name TEXT NOT NULL DEFAULT ''")
        if 'persona' not in columns:con.execute("ALTER TABLE users ADD COLUMN persona TEXT NOT NULL DEFAULT 'ana'")
        con.execute("INSERT OR IGNORE INTO settings VALUES('worker_paused','0')")
        for c in CASES:
            con.execute('INSERT OR IGNORE INTO cases VALUES(?,?,?,?,?,?)', c[:6])
            for kind, title, body in documents(c):
                con.execute('INSERT OR IGNORE INTO documents(id,case_id,kind,title,body,hash,origin) VALUES(?,?,?,?,?,?,?)', (c[0]+'-'+kind,c[0],kind,title,body,digest(body),'Sintético autoral'))
        con.executemany('INSERT OR IGNORE INTO refs VALUES(?,?,?,?,?,?)', REFERENCES)
        for name in ('DataJud simulado','DJEN simulado'):
            con.execute('INSERT OR IGNORE INTO sources(name,status,message) VALUES(?,?,?)',(name,'aguardando','Nenhuma chamada externa.'))
        try:
            con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(ref_id UNINDEXED,title,body,tags, tokenize="unicode61 remove_diacritics 2")')
            if con.execute('SELECT count(*) FROM search_index').fetchone()[0] == 0:
                con.executemany('INSERT INTO search_index VALUES(?,?,?,?)', [(r[0],r[1],r[3],r[5]) for r in REFERENCES])
        except sqlite3.OperationalError:
            pass

def allowed(con, case_id, profile):
    row = con.execute('SELECT owner FROM cases WHERE id=?',(case_id,)).fetchone()
    return bool(row and (profile == 'gestor' or row['owner'].lower() == profile))

def ingest(case_id, source='DJEN simulado', correction=False, path=DEFAULT_DB):
    with connect(path) as con:
        if not con.execute('SELECT 1 FROM cases WHERE id=?',(case_id,)).fetchone():
            raise ValueError('Processo inexistente')
        state = con.execute('SELECT status FROM sources WHERE name=?',(source,)).fetchone()
        t = now()
        if not state:
            raise ValueError('Fonte desconhecida')
        con.execute('UPDATE sources SET last_attempt=? WHERE name=?',(t,source))
        if state['status'] == 'indisponível':
            audit(con,'coleta_falhou','Fonte simulada indisponível; nenhum evento criado.',case_id)
            return False, 'Fonte indisponível. Restaure e repita a coleta.'
        body = con.execute("SELECT body FROM documents WHERE case_id=? AND kind='evento'",(case_id,)).fetchone()[0]
        if source == 'DataJud simulado':
            case = dict(con.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone())
            body = jsondump({'contrato':'snapshot sintético de metadados, não é payload oficial','processo':case['id'],'tribunal':'TJ-DEMO','classe':'Procedimento comum cível','assunto':'Inclusão indevida em cadastro de inadimplentes','responsavel':case['owner']})
        version = 2 if correction else 1
        if correction:
            body += ' RETIFICAÇÃO SINTÉTICA: retificada a identificação do documento. O teor decisório permanece conforme texto acima.'
        ext = f'{case_id}-'+('METADADOS' if source == 'DataJud simulado' else 'PUBLICACAO')
        exists = con.execute('SELECT id,hash FROM events WHERE source=? AND external_id=? AND version=?',(source,ext,version)).fetchone()
        if exists:
            audit(con,'duplicata_ignorada','Identificador e versão já recebidos.',case_id)
            con.execute('UPDATE sources SET status=?,last_success=?,message=? WHERE name=?',('disponível',t,'Coleta repetida sem duplicar evento.',source))
            return False,'Duplicata reconhecida. Nenhum alerta ou tarefa duplicado.'
        cur = con.execute('INSERT INTO events(source,external_id,case_id,version,body,hash,at) VALUES(?,?,?,?,?,?,?)',(source,ext,case_id,version,body,digest(body),t))
        con.execute('INSERT INTO tasks(event_id,updated) VALUES(?,?)',(cur.lastrowid,t))
        con.execute('UPDATE sources SET status=?,last_success=?,message=? WHERE name=?',('disponível',t,'Resposta sintética recebida e persistida.',source))
        audit(con,'evento_recebido',f'{source}, versão {version}. Evento e tarefa gravados na mesma transação.',case_id)
        return True, 'Evento recebido; processamento em segundo plano.'

def toggle_source(name, path=DEFAULT_DB):
    with connect(path) as con:
        r=con.execute('SELECT status FROM sources WHERE name=?',(name,)).fetchone()
        if not r: raise ValueError('Fonte desconhecida')
        state='disponível' if r[0]=='indisponível' else 'indisponível'
        con.execute('UPDATE sources SET status=?,message=? WHERE name=?',(state,'Estado alterado manualmente no simulador.',name))
        audit(con,'estado_fonte',f'{name}: {state}')


def jsondump(obj):
    return json.dumps(obj, ensure_ascii=False)
