import json
import tempfile
from pathlib import Path
import pytest
from poc.store import init,connect
from poc.chat import create_conversation,rename_conversation,delete_conversations,send_question,context_for,answer_question,process_chat_one
from poc.ui import View

@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'chat.db';init(path);yield path

def test_multiple_processes_are_persisted_and_retrieved(db):
    cid=create_conversation('processo',path=db,case_ids=['CASO-001','CASO-003','CASO-001'])
    with connect(db) as con:session=dict(con.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone())
    assert json.loads(session['case_ids'])==['CASO-001','CASO-003']
    sources=context_for(session,'Quais documentos existem?',db)
    assert {s['case_id'] for s in sources}=={'CASO-001','CASO-003'}
    assert len({s['id'] for s in sources})==len(sources)
    r=answer_question(session,'Existe histórico disponível?',[],db)
    assert 'CASO-001: Sim.' in r['answer'] and 'CASO-003: Não.' in r['answer']
    with pytest.raises(ValueError):create_conversation('processo',path=db,case_ids=['CASO-001','inexistente'])

def test_general_discards_unrelated_process_selection(db):
    cid=create_conversation('geral',path=db,case_ids=['CASO-001'])
    with connect(db) as con:row=dict(con.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone())
    assert row['case_id'] is None and json.loads(row['case_ids'])==[]

def test_rename_is_not_overwritten_and_html_is_escaped(db):
    cid=create_conversation('geral',path=db)
    rename_conversation(cid,'<Meu nome>',path=db)
    send_question(cid,'Primeira pergunta','a'*20,path=db)
    with connect(db) as con:assert con.execute('SELECT title FROM conversations WHERE id=?',(cid,)).fetchone()[0]=='<Meu nome>'
    html=View('token',query={'conversation':str(cid)},path=db).page('chat')
    assert '&lt;Meu nome&gt;' in html and '<Meu nome>' not in html
    assert 'Pensando em uma resposta…' in html
    assert 'name="cases"' in html and 'name="conversation_ids"' in html

def test_batch_delete_is_confirmed_and_atomic(db):
    ids=[create_conversation('geral',path=db) for _ in range(3)]
    send_question(ids[0],'Olá','b'*20,path=db)
    with pytest.raises(ValueError):delete_conversations(ids[:2],'',path=db)
    with pytest.raises(ValueError):delete_conversations([ids[0],9999],'excluir',path=db)
    assert delete_conversations(ids[:2],'excluir',path=db)==2
    with connect(db) as con:
        assert [r[0] for r in con.execute('SELECT id FROM conversations')]==ids[2:]
        assert con.execute('SELECT count(*) FROM chat_turns').fetchone()[0]==0
    with pytest.raises(PermissionError):delete_conversations(ids[2:],'excluir',profile='ana',path=db)

def test_batch_delete_during_inference_never_restores_conversation(db):
    cid=create_conversation('geral',path=db)
    send_question(cid,'Olá','c'*20,path=db)
    def client(*args,**kwargs):
        delete_conversations([cid],'excluir',path=db)
        return {'message':{'content':json.dumps({'resposta':'Olá','fontes':[],'trechos':[]})}}
    assert process_chat_one(db,client)
    with connect(db) as con:
        assert con.execute('SELECT count(*) FROM conversations').fetchone()[0]==0
        assert con.execute('SELECT count(*) FROM chat_turns').fetchone()[0]==0
