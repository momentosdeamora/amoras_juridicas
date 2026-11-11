import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from poc.corpus import import_pdf,search,DOC_ID
from poc.local_agent import run_agent,validate_model
from poc.store import init,connect

class CorpusAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'corpus.sqlite3';init(self.db);import_pdf(self.db)
    def tearDown(self): self.tmp.cleanup()
    def test_pdf_extracted_with_provenance(self):
        with connect(self.db) as con:
            d=con.execute('SELECT * FROM corpus_documents').fetchone()
            self.assertEqual(d['pages'],8);self.assertEqual(d['published'],'2016-06-08');self.assertEqual(len(d['hash']),64)
            self.assertEqual(con.execute('SELECT count(*) FROM corpus_chunks').fetchone()[0],20)
            t=con.execute('SELECT * FROM corpus_chunks WHERE thesis=7').fetchone()
            self.assertEqual(t['page'],3);self.assertIn('385',t['body']);self.assertIn('1061134',t['precedents'])
    def test_reimport_is_idempotent(self):
        self.assertFalse(import_pdf(self.db)['imported'])
        import_pdf(self.db,force=True)
        with connect(self.db) as con:self.assertEqual(con.execute('SELECT count(*) FROM corpus_chunks').fetchone()[0],20)
    def test_search_retrieves_actual_thesis_and_limits_scope(self):
        r=search('súmula 385 inscrição preexistente legítima',self.db)
        self.assertEqual(r[0]['thesis'],7);self.assertTrue(all(t['in_scope'] for t in r))
        self.assertIn('2016',r[0]['warning']);self.assertEqual(r[0]['url'],'/corpus.pdf#page=3')
        self.assertTrue(all('385' in t['body'] or '385' in t['tags'] for t in r))
        self.assertEqual([t['thesis'] for t in search('O que a tese 7 diz sobre inscrição anterior?',self.db)],[7])
    def test_native_tool_roundtrip(self):
        responses=[('consultar_documentos',{'processo':'CASO-002'}),('pesquisar_jurisprudencia',{'consulta':'súmula 385 inscrição anterior legítima'}),('concluir_pesquisa',{'motivo':'pesquisa_concluida'})]
        requests=[]
        def client(endpoint,body,timeout):
            requests.append(body)
            name,args=responses.pop(0)
            return {'message':{'role':'assistant','content':'','tool_calls':[{'function':{'name':name,'arguments':args}}]},'prompt_eval_count':100,'eval_count':20}
        with patch.dict(os.environ,{'POC_OLLAMA_MODEL':'qwen3:1.7b'}):
            r=run_agent('CASO-002','SENTENÇA. Inscrição anterior legítima.',self.db,client=client)
        self.assertTrue(r['sufficient_tools']);self.assertTrue(r['completed']);self.assertEqual(r['calls'],3)
        self.assertEqual(r['input_tokens'],300);self.assertEqual(r['retrieved'][0]['thesis'],7)
        self.assertTrue(any(m['role']=='tool' for m in requests[1]['messages']))
    def test_foreign_case_argument_rejected(self):
        def client(*args,**kw):
            return {'message':{'tool_calls':[{'function':{'name':'consultar_documentos','arguments':{'processo':'CASO-003'}}}]}}
        with self.assertRaises(ValueError):run_agent('CASO-001','Evento',self.db,'ana',client=client)
    def test_unknown_tool_rejected(self):
        def client(*args,**kw):
            return {'message':{'tool_calls':[{'function':{'name':'shell','arguments':{'cmd':'anything'}}}]}}
        with self.assertRaises(ValueError):run_agent('CASO-001','Evento',self.db,client=client)
    def test_cloud_model_and_unauthorized_case_rejected(self):
        with self.assertRaises(ValueError):validate_model('qwen3:cloud')
        with self.assertRaises(PermissionError):run_agent('CASO-003','Evento',self.db,'ana',client=lambda *a,**kw:None)
    def test_no_tool_response_is_bounded_and_not_legal_claim(self):
        calls=[]
        def client(*args,**kw):calls.append(1);return {'message':{'content':'Uma afirmação sem evidência.'}}
        r=run_agent('CASO-001','Evento',self.db,client=client)
        self.assertEqual(len(calls),4);self.assertFalse(r['sufficient_tools']);self.assertEqual(r['retrieved'],[])

if __name__=='__main__':unittest.main()
