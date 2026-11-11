import json
import tempfile
from pathlib import Path
import pytest
from poc.accounts import register,login,current_user,update_account
from poc.store import init,connect
from poc.chat import create_conversation,context_for
from poc.roles import can_page,can_action

@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'db.sqlite3';init(db);yield db

def test_account_updates_self_only_and_revokes_old_sessions(db):
    register('ana','antiga',db,'financeiro',display_name='Ana')
    first=login('ana','antiga',db);second=login('ana','antiga',db)
    assert update_account(first,'Ana Silva','','','',db) is None
    assert current_user(first,db)['display_name']=='Ana Silva'
    with pytest.raises(ValueError):update_account(first,'Não salvar','errada','nova','nova',db)
    assert current_user(first,db)['display_name']=='Ana Silva'
    fresh=update_account(first,'Ana Souza','antiga','nova','nova',db)
    assert current_user(first,db) is None and current_user(second,db) is None
    account=current_user(fresh,db)
    assert account['display_name']=='Ana Souza' and account['role']=='financeiro' and account['username']=='ana'
    assert login('ana','antiga',db) is None and login('ana','nova',db)

def test_all_roles_have_help_and_own_account():
    for role in ('gestor','ti','advogado','comercial','financeiro'):
        assert can_page(role,'como_usar') and can_page(role,'minha_conta') and can_action(role,'account_update')
    assert not can_page('invalido','minha_conta')

def test_scope_separation_and_combined_mode(db,monkeypatch):
    calls=[]
    def search(*args,**kw):
        calls.append(args)
        return [{'id':'J1','citation':'Tese de teste','body':'Trecho de teste','page':1,'document_hash':'hash','warning':'Histórica','url':'/corpus.pdf'}]
    monkeypatch.setattr('poc.corpus.search',search)
    def session(mode):
        cid=create_conversation(mode,path=db,case_ids=['CASO-001','CASO-002'])
        with connect(db) as con:return dict(con.execute('SELECT * FROM conversations WHERE id=?',(cid,)).fetchone())
    docs=context_for(session('processo'),'jurisprudência sobre inscrição anterior',db)
    assert not calls and docs and all(s['id'].startswith('D') for s in docs)
    refs=context_for(session('acervo'),'inscrição anterior',db)
    assert refs and all(s['id'].startswith('J') for s in refs)
    both=session('ambos');sources=context_for(both,'inscrição anterior',db)
    assert both['include_acervo']==1
    assert {s['id'][0] for s in sources}=={'D','J'}
    assert {s['case_id'] for s in sources if s['id'].startswith('D')}=={'CASO-001','CASO-002'}
    with pytest.raises(ValueError):create_conversation('ambos',path=db)
