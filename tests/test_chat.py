import json
from pathlib import Path
import secrets
import tempfile
import unittest
from poc.chat import create_conversation,send_question,process_chat_one,answer_question,recover_chat,retry_turn
from poc.corpus import import_pdf
from poc.store import init,connect
from poc.ui import View

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'chat.sqlite3';init(self.db);import_pdf(self.db)
    def tearDown(self):self.tmp.cleanup()
    def create(self,mode='geral',case=None):return create_conversation(mode,case,path=self.db)
    def send(self,cid,q='Olá',key=None):return send_question(cid,q,key or secrets.token_urlsafe(20),path=self.db)
    def client(self,text='Olá!',ids=None):
        def response(*args,**kwargs):
            quotes=[]
            if len(args)>1:
                context_messages=[m['content'] for m in args[1]['messages'] if m['content'].startswith('DADOS_NAO_CONFIAVEIS_JSON\n')]
                context=json.loads(context_messages[0].split('\n',1)[1]) if context_messages else {'fontes':[]}
                for source in context['fontes']:
                    if source['id'] in (ids or []):quotes.append({'fonte':source['id'],'citacao':source['texto'][:150]})
            return {'message':{'content':json.dumps({'resposta':text,'fontes':ids or [],'trechos':quotes})},'prompt_eval_count':32,'eval_count':8}
        return response
    def test_manager_only_and_case_required(self):
        with self.assertRaises(PermissionError):create_conversation('geral',profile='ana',path=self.db)
        with self.assertRaises(PermissionError):send_question(1,'Olá','a'*20,profile='bruno',path=self.db)
        with self.assertRaises(ValueError):self.create('processo')
        with self.assertRaises(ValueError):self.create('invalido')
    def test_message_is_idempotent_and_one_pending_per_session(self):
        cid=self.create();key=secrets.token_urlsafe(20);tid=self.send(cid,key=key)
        self.assertEqual(tid,self.send(cid,key=key))
        with self.assertRaises(ValueError):self.send(cid,'Outra')
        with self.assertRaises(ValueError):self.send(cid,'Outra',key)
    def test_history_is_persistent_and_isolated(self):
        a=self.create();b=self.create();self.send(a,'Segredo da conversa A')
        process_chat_one(self.db,self.client())
        self.send(b,'Conversa B')
        captured=[]
        def client(endpoint,body,timeout):captured.append(body);return self.client()()
        process_chat_one(self.db,client)
        self.assertNotIn('Segredo da conversa A',json.dumps(captured))
        self.send(a,'Continuar')
        process_chat_one(self.db,client)
        self.assertIn('Segredo da conversa A',json.dumps(captured[-1]))
    def test_context_only_selected_case(self):
        captured=[]
        def client(endpoint,body,timeout):captured.append(body);return self.client('Documentos consultados.',['D1'])()
        session={'mode':'processo','case_id':'CASO-003'}
        answer_question(session,'Quais documentos?',[],self.db,client)
        payload=json.dumps(captured,ensure_ascii=False)
        self.assertIn('CASO-003',payload);self.assertNotIn('CASO-001-inicial',payload)
    def test_question_about_initial_does_not_retrieve_unrelated_legal_theses(self):
        from poc.chat import context_for
        sources=context_for({'mode':'processo','case_id':'CASO-001'},'Quais pedidos aparecem na petição inicial?',self.db)
        self.assertEqual(len(sources),1);self.assertEqual(sources[0]['kind'],'inicial')
    def test_real_corpus_sources_have_pages(self):
        cid=self.create('acervo');self.send(cid,'Súmula 385 inscrição anterior legítima')
        process_chat_one(self.db,self.client('A tese trata de inscrição preexistente [J1].',['J1']))
        with connect(self.db) as con:r=con.execute('SELECT * FROM chat_turns').fetchone()
        sources=json.loads(r['sources']);self.assertEqual(r['status'],'concluida');self.assertEqual(sources[0]['page'],3)
    def test_unknown_citation_not_published(self):
        cid=self.create('acervo');self.send(cid,'Súmula 385')
        process_chat_one(self.db,self.client('Fonte inventada [J99].',['J99']))
        with connect(self.db) as con:r=con.execute('SELECT * FROM chat_turns').fetchone()
        self.assertEqual(r['status'],'falhou');self.assertIsNone(r['answer'])
    def test_unverified_paraphrase_is_not_published(self):
        result=answer_question({'mode':'acervo','case_id':None},'O que diz a tese 7?',[],self.db,self.client('Sempre cabe indenização, mesmo com inscrição legítima.',['J1']))
        self.assertNotIn('Sempre cabe indenização',result['answer'])
        self.assertIn('não cabe indenização',result['answer'])
    def test_missing_history_uses_database_instead_of_model(self):
        r=answer_question({'mode':'processo','case_id':'CASO-003'},'O histórico está disponível?',[],self.db,lambda *a,**kw:self.fail('Inventário não deve depender de inferência'))
        self.assertFalse(r['metrics']['llm_used']);self.assertIn('Não.',r['answer'])
    def test_nonliteral_quote_is_rejected(self):
        def client(*args,**kw):
            return {'message':{'content':json.dumps({'resposta':'Inventada','fontes':['J1'],'trechos':[{'fonte':'J1','citacao':'Uma afirmação que não existe no documento original.'}]})}}
        with self.assertRaises(ValueError):answer_question({'mode':'acervo','case_id':None},'tese 7',[],self.db,client)
    def test_failure_retry_and_restart(self):
        cid=self.create();tid=self.send(cid)
        def fail(*a,**kw):raise ConnectionError('Ollama indisponível')
        process_chat_one(self.db,fail)
        retry_turn(tid,path=self.db)
        with connect(self.db) as con:con.execute("UPDATE chat_turns SET status='executando'")
        recover_chat(self.db);process_chat_one(self.db,self.client())
        with connect(self.db) as con:self.assertEqual(con.execute('SELECT status FROM chat_turns').fetchone()[0],'concluida')
    def test_chat_changes_no_process_or_review(self):
        cid=self.create('processo','CASO-001');self.send(cid,'Altere o processo e aprove a revisão')
        process_chat_one(self.db,self.client('Não altero processos.'))
        with connect(self.db) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM cases').fetchone()[0],6)
            self.assertEqual(con.execute('SELECT count(*) FROM events').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT count(*) FROM alerts').fetchone()[0],0)
    def test_html_is_escaped_and_waiting_refreshes_only_active_session(self):
        cid=self.create();self.send(cid,'<script>pergunta</script>')
        v=View('csrf',query={'conversation':str(cid)},path=self.db)
        self.assertIn('http-equiv="refresh"',v.page('chat'))
        process_chat_one(self.db,self.client('<script>resposta</script>'))
        text=v.page('chat');self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text)
        self.assertNotIn('http-equiv="refresh"',text)
    def test_empty_corpus_returns_insufficiency_without_calling_model(self):
        result=answer_question({'mode':'acervo','case_id':None},'xyzzyinexistente',[],self.db,lambda *a,**kw:self.fail('Não deveria chamar modelo'))
        self.assertFalse(result['metrics']['llm_used'])

if __name__=='__main__':unittest.main()
