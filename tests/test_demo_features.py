import tempfile
from pathlib import Path
from poc.store import init,connect
from poc.accounts import register,login,current_user,logout
from poc.demo_operations import collect_tick,operational_triage,compare_pending
from tests.test_http import HTTPTests as _HTTPTests
import unittest
from run import TOKEN


def test_accounts_sessions_and_password_storage():
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'test.db';init(db)
        register('Alice','senha-local',db,'financeiro')
        assert login('alice','errada',db) is None
        cookie=login('ALICE','senha-local',db)
        assert current_user(cookie,db)['role']=='financeiro'
        with connect(db) as con:assert con.execute('SELECT password_hash FROM users').fetchone()[0]!='senha-local'
        logout(cookie,db);assert current_user(cookie,db) is None


def test_collector_interval_idempotence_and_pause():
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'test.db';init(db)
        assert collect_tick(db,100)
        assert not collect_tick(db,120)
        assert collect_tick(db,160)
        with connect(db) as con:
            assert con.execute('SELECT count(*) FROM events').fetchone()[0]==12
            con.execute("INSERT OR REPLACE INTO settings VALUES('collector_enabled','0')")
        assert not collect_tick(db,220)


def test_operational_triage():
    assert operational_triage('sentenca','Ana')['status']=='Revisar possível manifestação'
    assert operational_triage('incerto','Ana')['status']=='Conferir documento antes da triagem'


class AccountHTTPTests(unittest.TestCase):
    setUp=_HTTPTests.setUp
    tearDown=_HTTPTests.tearDown
    request=_HTTPTests.request
    # Somente os testes abaixo exercitam o servidor autenticado; os herdados
    # continuam cobrindo os handlers isolados no modo de teste preexistente.
    def test_role_cannot_escalate_query_or_post(self):
        self.server.user_auth=True
        register('fin','senha',self.db,'financeiro')
        cookie=login('fin','senha',self.db).split(';')[0]
        assert '403 Forbidden' in self.request('/?page=processos&profile=gestor',headers={'Cookie':cookie})
        assert '200 OK' in self.request('/?page=financeiro',headers={'Cookie':cookie})
        assert '403 Forbidden' in self.request('/action','POST',{'csrf':TOKEN,'profile':'gestor','action':'seed'},headers={'Cookie':cookie})
        assert '403 Forbidden' in self.request('/export?event=1',headers={'Cookie':cookie})
    def test_registration_and_session_logout(self):
        self.server.user_auth=True
        assert '303 See Other' in self.request('/')
        r=self.request('/register','POST',{'csrf':TOKEN,'username':'nova','password':'senha','role':'advogado','persona':'bruno'})
        assert 'Set-Cookie: amoras_session=' in r
        cookie=next(line.split(': ',1)[1].split(';')[0] for line in r.splitlines() if line.startswith('Set-Cookie:'))
        assert '403 Forbidden' in self.request('/?page=seguranca&profile=gestor',headers={'Cookie':cookie})
        assert '200 OK' in self.request('/?page=processos&profile=ana',headers={'Cookie':cookie})
        assert '403 Forbidden' in self.request('/?page=processos&case=CASO-001',headers={'Cookie':cookie})
        assert '303 See Other' in self.request('/logout','POST',{'csrf':TOKEN},headers={'Cookie':cookie})
        assert '303 See Other' in self.request('/',headers={'Cookie':cookie})


def test_role_matrix():
    from poc.roles import can_page,can_action
    for role in ('gestor','ti'):
        assert all(can_page(role,p) for p in ('processos','chat','comercial','financeiro','seguranca'))
        assert can_action(role,'seed')
    assert can_page('advogado','processos') and not can_page('advogado','financeiro')
    assert can_page('comercial','comercial') and not can_page('comercial','processos')
    assert can_page('financeiro','financeiro') and not can_page('financeiro','chat')
    assert not can_action('financeiro','ingest')


def test_comparison_labels_fallback_and_preserves_both_traces(monkeypatch):
    import json
    monkeypatch.delenv('POC_OLLAMA_MODEL',raising=False)
    with tempfile.TemporaryDirectory() as tmp:
        db=Path(tmp)/'test.db';init(db)
        with connect(db) as con:con.execute("INSERT INTO settings VALUES('comparison_pending','CASO-002')")
        assert compare_pending(db)
        with connect(db) as con:r=json.loads(con.execute("SELECT value FROM settings WHERE key='comparison_report'").fetchone()[0])
        assert not r['native_agent']
        assert r['fixed']['trace'] and r['agent']['trace']
        assert 'REF-S385' in r['agent']['references']
        assert not compare_pending(db)
