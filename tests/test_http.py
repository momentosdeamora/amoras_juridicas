"""Teste do protocolo HTTP com socket em memória; nenhum acesso externo."""
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from run import Handler,TOKEN
from poc.engine import process_one
from poc.store import init,ingest,connect

class MemorySocket:
    def __init__(self,data): self.input=io.BytesIO(data); self.output=io.BytesIO()
    def makefile(self,mode,*args): return self.input if 'r' in mode else self.output
    def sendall(self,data): self.output.write(data)

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/'http.sqlite3'; init(self.db)
        self.server=SimpleNamespace(server_address=('127.0.0.1',5000),db_path=self.db)
    def tearDown(self): self.tmp.cleanup()
    def request(self,path='/',method='GET',data=None,headers=None):
        body=urlencode(data or {}).encode() if data is not None else b''
        hs={'Host':'127.0.0.1:5000',**(headers or {})}
        if data is not None: hs.update({'Content-Type':'application/x-www-form-urlencoded','Content-Length':str(len(body))})
        raw=f'{method} {path} HTTP/1.0\r\n'.encode()+''.join(f'{k}: {v}\r\n' for k,v in hs.items()).encode()+b'\r\n'+body
        sock=MemorySocket(raw); Handler(sock,('127.0.0.1',1),self.server)
        return sock.output.getvalue().decode()
    def post(self,**kw): return self.request('/action','POST',{'csrf':TOKEN,'profile':'gestor',**kw})
    def test_all_routes_and_head(self):
        for page in ['inicio','processos','simulador','avaliacao','arquitetura','economia','seguranca','auditoria','acervo']:
            self.assertIn('200 OK',self.request('/?page='+page))
        head=self.request('/','HEAD'); self.assertIn('200 OK',head); self.assertNotIn('<!doctype',head)
    def test_unknown_path_shows_construction_page(self):
        response=self.request('/pagina-futura?profile=ana')
        self.assertIn('404 Not Found',response)
        self.assertIn('Página em construção',response)
        self.assertIn('Volte mais tarde',response)
        self.assertIn('Voltar ao painel',response)
        self.assertIn('profile=ana',response)
    def test_unknown_page_parameter_does_not_fall_back_to_home(self):
        response=self.request('/?page=relatorio-futuro')
        self.assertIn('404 Not Found',response)
        self.assertIn('Página em construção',response)
        self.assertNotIn('Operação em um olhar',response)
        head=self.request('/nao-existe','HEAD')
        self.assertIn('404 Not Found',head)
        self.assertNotIn('<!doctype',head)
    def test_csrf_and_origin_and_host(self):
        self.assertIn('403',self.request('/action','POST',{'action':'seed'}))
        self.assertIn('403',self.request('/action','POST',{'csrf':TOKEN,'action':'seed'}, {'Origin':'https://example.com'}))
        self.assertIn('403',self.request('/',headers={'Host':'evil.example'}))
    def test_csrf_survives_server_restart(self):
        from poc.store import csrf_token
        first=csrf_token(self.db,'primeiro-token-local')
        second=csrf_token(self.db,'token-gerado-no-reinicio')
        self.assertEqual(first,second)
    def test_actual_rendered_new_chat_form_submits(self):
        from poc.http_probe import Forms
        parser=Forms();parser.feed(self.request('/?page=chat&profile=gestor'))
        fields=parser.find('chat_new')
        self.assertIsNotNone(fields)
        fields.update({'mode':'geral','case':''})
        response=self.request('/action','POST',fields)
        self.assertIn('303 See Other',response)
        self.assertIn('conversation=1',response)
    def test_browser_origin_policy_allows_create_select_process_and_send(self):
        from poc.http_probe import Forms
        page=self.request('/?page=chat&profile=gestor')
        self.assertIn('Referrer-Policy: same-origin',page)
        # Simular a origem que o navegador envia conforme a política da página.
        origin='null' if 'Referrer-Policy: no-referrer\r\n' in page else 'http://127.0.0.1:5000'
        forms=Forms();forms.feed(page)
        fields=forms.find('chat_new');fields.update({'mode':'processo','case':'CASO-001'})
        response=self.request('/action','POST',fields,{'Origin':origin})
        self.assertIn('303 See Other',response)
        forms=Forms();forms.feed(self.request('/?page=chat&profile=gestor&conversation=1'))
        fields=forms.find('chat_send');fields['question']='Quais pedidos aparecem na inicial?'
        self.assertIn('303 See Other',self.request('/action','POST',fields,{'Origin':origin}))
    def test_opaque_origin_is_still_rejected_with_valid_token(self):
        fields={'csrf':TOKEN,'profile':'gestor','action':'chat_new','mode':'geral'}
        self.assertIn('403',self.request('/action','POST',fields,{'Origin':'null'}))
    def test_real_form_sequence(self):
        self.assertIn('303',self.post(action='seed'))
        for _ in range(12): process_one(self.db)
        self.assertIn('Dossiê de apoio',self.request('/?page=processos&case=CASO-001'))
        self.assertIn('303',self.post(action='review',case='CASO-001',event='1',status='revisado',note='Revisão de teste.'))
        with connect(self.db) as con:
            self.assertEqual(con.execute('SELECT status FROM alerts WHERE event_id=1').fetchone()[0],'revisado')
    def test_cross_case_export_and_review_blocked(self):
        ingest('CASO-003',path=self.db); process_one(self.db)
        self.assertIn('403',self.request('/export?event=1&profile=ana'))
        self.assertIn('403',self.request('/?page=processos&case=CASO-003&profile=ana'))
        self.assertIn('403',self.post(action='review',profile='ana',case='CASO-003',event='1',status='revisado',note='negado'))
        self.assertIn('403',self.request('/?page=avaliacao&profile=ana'))
    def test_escaping_user_review(self):
        ingest('CASO-001',path=self.db); process_one(self.db)
        self.post(action='review',case='CASO-001',event='1',status='revisado',note='<script>alert(1)</script>')
        response=self.request('/?page=processos&case=CASO-001')
        self.assertNotIn('<script>',response); self.assertIn('&lt;script&gt;',response)
    def test_remove_and_restore_document_requeues(self):
        ingest('CASO-002',path=self.db); process_one(self.db)
        for _ in range(2):
            self.assertIn('303',self.post(action='document',case='CASO-002')); process_one(self.db)
        with connect(self.db) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM runs').fetchone()[0],3)
    def test_global_actions_forbidden_to_lawyer(self):
        for action in ('seed','source','fault','pause','retry','document','evaluate','chat_new','chat_send','chat_retry'):
            self.assertIn('403',self.post(action=action,profile='ana'))
    def test_chat_is_manager_only_and_messages_use_queue(self):
        self.assertIn('403',self.request('/?page=chat&profile=ana'))
        self.assertNotIn('Conversar com a IA',self.request('/?profile=ana'))
        self.assertIn('303',self.post(action='chat_new',mode='geral'))
        self.assertIn('Conversar com a IA',self.request('/?page=chat&conversation=1'))
        self.assertIn('303',self.post(action='chat_send',conversation='1',question='Olá',request_key='identificador-de-teste-123'))
        with connect(self.db) as con:
            row=con.execute('SELECT * FROM chat_turns').fetchone()
            self.assertEqual(row['status'],'pendente')
    def test_pdf_route_and_real_corpus_page(self):
        from poc.corpus import import_pdf
        import_pdf(self.db)
        self.assertIn('20 teses',self.request('/?page=acervo'))
        # O corpo PDF é binário; verificar via HEAD sem decodificá-lo.
        response=self.request('/corpus.pdf','HEAD')
        self.assertIn('200 OK',response);self.assertIn('application/pdf',response)
    def test_reprocess_foreign_case_forbidden(self):
        self.assertIn('403',self.post(action='reprocess',profile='ana',case='CASO-003',event='1'))

if __name__=='__main__': unittest.main()
