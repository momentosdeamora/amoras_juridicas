#!/usr/bin/env python3
"""Servidor local da POC. Execute: python3 run.py"""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from poc.engine import evaluate, worker
from poc.fixtures import CASES, documents
from poc.store import DEFAULT_DB, allowed, audit, connect, csrf_token, digest, ingest, init, jsondump, now, toggle_source
from poc.ui import CSS, NAV, View, esc
from poc.access import authenticated,issue_cookie,limited,load_access_secret

TOKEN=secrets.token_urlsafe(32)
PROFILES={'gestor','ana','bruno','comercial','financeiro'}


def params(value):
    return {k:(v if k in {'cases','conversation_ids'} else v[-1]) for k,v in parse_qs(value,keep_blank_values=True,max_num_fields=1000).items()}


class Server(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True


class Handler(BaseHTTPRequestHandler):
    server_version='AmorasLocal/1.0'
    def setup(self):
        if hasattr(self.request,'settimeout'):self.request.settimeout(15)
        super().setup()
    def version_string(self): return 'AmorasLocal'
    def has_access(self):
        if getattr(self.server,'user_auth',False):
            from poc.accounts import current_user
            return bool(current_user(self.headers.get('Cookie'),self.server.db_path))
        return authenticated(self.headers.get('Cookie'),getattr(self.server,'access_secret',None))
    def login_page(self,message='',register=False):
        action='/register' if register else '/login'
        title='Criar conta' if register else 'Entrar'
        from poc.roles import ROLES
        roles='<label>Perfil de demonstração<select name="role">'+''.join(f'<option value="{r}">{esc(t)}</option>' for r,t in ROLES.items())+'</select></label><label class="registration-wallet">Carteira fictícia (somente advogado)<select name="persona"><option value="ana">Ana</option><option value="bruno">Bruno</option></select></label>' if register else ''
        name_field='<label>Nome<input name="display_name" maxlength="100" autocomplete="name"></label>' if register else ''
        alternate='<a href="/login">Já tenho conta</a>' if register else '<a href="/register">Criar minha conta</a>'
        body=f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Amoras Jurídicas</title><link rel="stylesheet" href="/style.css"></head><body><main class="login-container"><section class="card"><div class="login-brand"><img src="/static/img/logotipo.webp" alt=""><h1>Amoras Jurídicas</h1></div><h2>{title}</h2><p>{esc(message)}</p><form method="post" action="{action}"><input type="hidden" name="csrf" value="{esc(TOKEN)}">{name_field}<label>Login<input name="username" required maxlength="80" autocomplete="username"></label><label>Senha<input type="password" name="password" required maxlength="256" autocomplete="{'new-password' if register else 'current-password'}"></label>{roles}<button class="primary">{title}</button></form><p>{alternate}</p><small>Demonstração: cadastro livre, sem verificação de e-mail. O perfil é escolhido livremente apenas neste protótipo; use uma senha exclusiva.</small></section></main></body></html>'''
        return self.send(body)
    def origins(self):
        ports={self.server.server_address[1],int(os.environ.get('FAROL_PUBLIC_PORT',self.server.server_address[1]))}
        return {f'http://{host}:{port}' for host in ('127.0.0.1','localhost') for port in ports}
    def log_message(self,fmt,*args):
        # Sem query strings nem conteúdo de documentos em logs operacionais.
        print(f'[HTTP] {self.command} {self.path.split("?")[0]} {args[1] if len(args)>1 else ""}',flush=True)
    def send(self,body,status=200,ctype='text/html; charset=utf-8',headers=None):
        data=body.encode() if isinstance(body,str) else body
        self.send_response(status)
        # no-referrer pode produzir Origin:null em POST de formulário e bloquear a própria aplicação.
        # same-origin preserva a origem local e não envia Referer a sites externos.
        for k,v in {'Content-Type':ctype,'Content-Length':str(len(data)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",**(headers or {})}.items():
            self.send_header(k,v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)
    def do_HEAD(self):
        self.do_GET()
    def valid_host(self):
        return self.headers.get('Host') in {value.removeprefix('http://') for value in self.origins()}
    def deny(self,status=403,text='Acesso negado.'):
        if status==403:
            print('[HTTP segurança] '+text,flush=True)
        if status == 404:
            return self.send(View(TOKEN,path=self.server.db_path).page('construcao'),404)
        self.send(f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Acesso negado</title><h1>{status}</h1><p>{esc(text)}</p><a href="/">Voltar ao painel</a></html>',status)
    def do_GET(self):
        if not self.valid_host(): return self.deny(text='Host não permitido. Use localhost ou 127.0.0.1.')
        url=urlsplit(self.path)
        try: q=params(url.query)
        except ValueError: return self.deny(400,'Consulta inválida.')
        profile=q.get('profile','gestor')
        if profile not in PROFILES: return self.deny(400,'Perfil inválido.')
        if url.path=='/style.css': return self.send(CSS,ctype='text/css; charset=utf-8')
        if url.path=='/static/img/logotipo.webp':
            logo=Path(__file__).resolve().parent/'static'/'img'/'logotipo.webp'
            if not logo.is_file(): return self.deny(404,'Logotipo não encontrado.')
            return self.send(logo.read_bytes(),ctype='image/webp')
        if url.path=='/health': return self.send(jsondump({'status':'ok','data':'synthetic','paid_services':False,'runtime':'virtualenv' if sys.prefix!=sys.base_prefix else 'system','authentication':bool(getattr(self.server,'user_auth',False) or getattr(self.server,'access_secret',None))}),ctype='application/json; charset=utf-8')
        if url.path=='/favicon.ico': return self.send(b'',204,'image/x-icon')
        if url.path=='/login':return self.login_page()
        if url.path=='/register':return self.login_page(register=True)
        if not self.has_access():return self.send('',303,headers={'Location':'/login'})
        account=None
        if getattr(self.server,'user_auth',False):
            from poc.accounts import current_user
            from poc.roles import demo_profile,can_page,home
            account=current_user(self.headers.get('Cookie'),self.server.db_path)
            profile=demo_profile(account)
            requested=q.get('page',home(account['role']))
            if url.path in {'/export','/corpus.pdf'}:
                if not can_page(account['role'],'processos' if url.path=='/export' else 'acervo'):return self.deny()
            elif url.path=='/' and not can_page(account['role'],requested):return self.deny(text='Seu perfil não tem acesso a esta área.')
            q['page']=requested
            q['_role']=account['role'];q['_username']=account['username'];q['_name']=account['display_name'] or account['username']
        if url.path=='/corpus.pdf':
            from poc.corpus import PDF
            if not PDF.exists(): return self.deny(404,'PDF não encontrado.')
            return self.send(PDF.read_bytes(),ctype='application/pdf',headers={'Content-Disposition':'inline; filename="cadastro-inadimplentes-stj.pdf"'})
        if url.path=='/export':
            try: eid=int(q.get('event','0'))
            except ValueError: return self.deny(400,'Evento inválido.')
            with connect(self.server.db_path) as con:
                d=con.execute('SELECT * FROM dossiers WHERE event_id=?',(eid,)).fetchone()
                if not d: return self.deny(404,'Dossiê não encontrado.')
                if not allowed(con,d['case_id'],profile): return self.deny()
                audit(con,'exportacao',f'Dossiê do evento {eid}',d['case_id'],profile)
                return self.send(d['body'],ctype='application/json; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="dossie-evento-{eid}.json"'})
        if url.path!='/':
            return self.send(View(TOKEN,profile,q,self.server.db_path).page('construcao'),404)
        page=q.get('page','inicio')
        if page not in {name for name,_,_ in NAV}:
            return self.send(View(TOKEN,profile,q,self.server.db_path).page('construcao'),404)
        if page=='chat' and profile!='gestor': return self.deny(text='Conversa disponível somente ao gestor de demonstração.')
        if page=='avaliacao' and profile!='gestor': return self.deny(text='Avaliação global disponível somente para o Gestor de demonstração.')
        try:
            if page=='processos' and q.get('case'):
                with connect(self.server.db_path) as con:
                    if not allowed(con,q['case'],profile): return self.deny()
            return self.send(View(TOKEN,profile,q,self.server.db_path).page(page))
        except Exception as exc:
            print('[ERRO] Renderização:',type(exc).__name__,flush=True)
            return self.deny(500,'Não foi possível carregar o painel. Consulte o terminal local.')
    def do_POST(self):
        if not self.valid_host(): return self.deny()
        if self.path not in {'/action','/login','/register','/logout'}: return self.deny(404)
        if limited(self.server,(self.client_address[0],'forms')):return self.send('Muitas solicitações. Aguarde um minuto.',429,headers={'Retry-After':'60'})
        origin=self.headers.get('Origin')
        if origin and origin not in self.origins():
            return self.deny(text='Origem não permitida.')
        if self.headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded': return self.deny(415,'Formato inválido.')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=16384: return self.deny(413,'Formulário excede o limite.')
            p=params(self.rfile.read(size).decode('utf-8'))
        except (ValueError,UnicodeError): return self.deny(400,'Formulário inválido.')
        if not secrets.compare_digest(p.get('csrf',''),TOKEN): return self.deny(text='Token inválido. Recarregue a página.')
        if self.path in {'/login','/register'}:
            from poc.accounts import register,login
            if limited(self.server,(self.client_address[0],'login'),limit=30):return self.send('Aguarde antes de tentar novamente.',429)
            try:
                if self.path=='/register':register(p.get('username',''),p.get('password',''),self.server.db_path,p.get('role','advogado'),p.get('persona','ana'),p.get('display_name',''))
                cookie=login(p.get('username',''),p.get('password',''),self.server.db_path)
                if not cookie:return self.login_page('Login ou senha incorretos.')
                return self.send('',303,headers={'Location':'/','Set-Cookie':cookie})
            except ValueError as exc:return self.login_page(str(exc),register=self.path=='/register')
        if not self.has_access():return self.deny(text='Entre no ambiente antes de enviar formulários.')
        if self.path=='/logout':
            from poc.accounts import logout
            return self.send('',303,headers={'Location':'/login','Set-Cookie':logout(self.headers.get('Cookie'),self.server.db_path)})
        profile=p.get('profile','gestor')
        if profile not in PROFILES: return self.deny(400,'Perfil inválido.')
        action=p.get('action'); cid=p.get('case'); path=self.server.db_path
        if getattr(self.server,'user_auth',False):
            from poc.accounts import current_user
            from poc.roles import demo_profile,can_action
            account=current_user(self.headers.get('Cookie'),path)
            if not can_action(account['role'],action):return self.deny(text='Ação não permitida para seu perfil.')
            profile=demo_profile(account)

        if action not in {'ingest','review','reprocess','account_update'} and profile!='gestor': return self.deny()
        try:
            if action in {'ingest','review','document','reprocess'}:
                with connect(path) as con:
                    if not allowed(con,cid,profile): return self.deny()
            if action=='account_update':
                from poc.accounts import update_account
                cookie=update_account(self.headers.get('Cookie'),p.get('display_name',''),p.get('current_password',''),p.get('new_password',''),p.get('confirm_password',''),path)
                headers={'Location':'/?page=minha_conta&msg=Cadastro+atualizado.'}
                if cookie:headers['Set-Cookie']=cookie
                return self.send('',303,headers=headers)
            elif action=='chat_new':
                from poc.chat import create_conversation
                conversation=create_conversation(p.get('mode'),p.get('case') or None,profile,path,case_ids=p.get('cases'))
                self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','profile':profile,'conversation':conversation})})
                return
            elif action=='chat_rename':
                from poc.chat import rename_conversation
                conversation=int(p.get('conversation','0'))
                rename_conversation(conversation,p.get('title',''),profile,path)
                return self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','conversation':conversation})})
            elif action=='chat_delete_many':
                from poc.chat import delete_conversations
                count=delete_conversations(p.get('conversation_ids',[]),p.get('confirm',''),profile,path)
                return self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','msg':f'{count} conversas excluídas.'})})
            elif action=='chat_send':
                from poc.chat import send_question
                conversation=int(p.get('conversation','0'))
                send_question(conversation,p.get('question',''),p.get('request_key',''),profile,path)
                self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','profile':profile,'conversation':conversation})})
                return
            elif action=='chat_retry':
                from poc.chat import retry_turn
                conversation=retry_turn(int(p.get('turn','0')),profile,path)
                self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','profile':profile,'conversation':conversation})})
                return
            elif action=='chat_delete':
                from poc.chat import delete_conversation
                delete_conversation(int(p.get('conversation','0')),p.get('confirm',''),profile,path)
                self.send('',303,headers={'Location':'/?'+urlencode({'page':'chat','profile':profile,'msg':'Conversa excluída.'})})
                return
            elif action=='seed':
                created=0
                for c in CASES:
                    ok,_=ingest(c[0],path=path); created+=ok
                    ok,_=ingest(c[0],source='DataJud simulado',path=path); created+=ok
                msg=f'{created} evento(s) novo(s) na fila. Reenvios são deduplicados.'
            elif action=='ingest':
                _,msg=ingest(cid,source=p.get('source','DJEN simulado'),correction=p.get('correction')=='1',path=path)
            elif action=='collector':
                with connect(path) as con:
                    row=con.execute("SELECT value FROM settings WHERE key='collector_enabled'").fetchone()
                    enabled=not row or row[0]=='1'
                    con.execute("INSERT OR REPLACE INTO settings VALUES('collector_enabled',?)",('0' if enabled else '1',))
                msg='Coleta periódica pausada.' if enabled else 'Coleta periódica ativada (60 segundos).'
            elif action=='compare_agent':
                if cid not in {c[0] for c in CASES}:raise ValueError('Processo inválido.')
                with connect(path) as con:
                    state=con.execute("SELECT value FROM settings WHERE key='comparison_state'").fetchone()
                    if state and state[0] in {'pendente','executando'}:raise ValueError('Comparação em andamento. Aguarde.')
                    con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_pending',?)",(cid,))
                    con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_state','pendente')")
                msg='Comparação enfileirada. Atualize a avaliação após a execução.'
            elif action=='source':
                toggle_source(p.get('source'),path); msg='Estado da fonte alterado. Teste uma coleta para observar o comportamento.'
            elif action=='fault':
                with connect(path) as con:
                    con.execute("INSERT OR REPLACE INTO settings VALUES('fail_next','1')")
                    audit(con,'falha_armada','A próxima tarefa falhará uma vez.',actor=profile)
                msg='Falha única armada. Receba um evento ainda não processado ou uma retificação.'
            elif action=='pause':
                with connect(path) as con:
                    old=con.execute("SELECT value FROM settings WHERE key='worker_paused'").fetchone()[0]
                    con.execute("UPDATE settings SET value=? WHERE key='worker_paused'",('0' if old=='1' else '1',))
                    audit(con,'trabalhador','Estado de pausa alterado.',actor=profile)
                msg='Trabalhador retomado.' if old=='1' else 'Trabalhador pausado. Tarefa já iniciada pode concluir.'
            elif action=='retry':
                with connect(path) as con:
                    n=con.execute("UPDATE tasks SET status='pendente',error=NULL,updated=? WHERE status='falhou'",(now(),)).rowcount
                    audit(con,'retentativa',f'{n} tarefa(s) recolocadas na fila.',actor=profile)
                msg=f'{n} tarefa(s) retomadas.'
            elif action=='document':
                if cid != 'CASO-002':
                    raise ValueError('A alternância de histórico está disponível somente no CASO-002.')
                with connect(path) as con:
                    d=con.execute("SELECT * FROM documents WHERE case_id=? AND kind='historico'",(cid,)).fetchone()
                    if d:
                        con.execute('DELETE FROM documents WHERE id=?',(d['id'],))
                        msg='Histórico retirado da carteira atual; novas pesquisas devem indicar sua ausência.'
                    else:
                        case=next(c for c in CASES if c[0]==cid)
                        kind,title,body=next(d for d in documents(case) if d[0]=='historico')
                        con.execute('INSERT INTO documents(id,case_id,kind,title,body,hash,origin) VALUES(?,?,?,?,?,?,?)',(cid+'-'+kind,cid,kind,title,body,digest(body),'Sintético autoral restaurado'))
                        msg='Histórico restaurado.'
                    con.execute("UPDATE tasks SET status='pendente',error=NULL,updated=? WHERE event_id IN (SELECT id FROM events WHERE case_id=?) AND status!='executando'",(now(),cid))
                    audit(con,'acervo_alterado',msg+' Dossiês serão atualizados; execuções anteriores preservadas.',cid,profile)
            elif action=='reprocess':
                eid=int(p.get('event','0'))
                with connect(path) as con:
                    changed=con.execute("UPDATE tasks SET status='pendente',error=NULL,updated=? WHERE event_id IN (SELECT id FROM events WHERE id=? AND case_id=?) AND status IN ('concluida','falhou')",(now(),eid,cid)).rowcount
                    audit(con,'pesquisa_solicitada',f'Evento {eid}; {changed} tarefa(s) reaberta(s).',cid,profile)
                msg='Pesquisa solicitada na fila local. O dossiê anterior permanece visível até a conclusão.'
            elif action=='review':
                status=p.get('status'); note=p.get('note','').strip(); eid=int(p.get('event','0'))
                if status not in {'pendente','revisado'} or not note or len(note)>1200: raise ValueError('Informe uma revisão válida, com até 1.200 caracteres.')
                with connect(path) as con:
                    r=con.execute('SELECT * FROM alerts WHERE event_id=? AND case_id=?',(eid,cid)).fetchone()
                    if not r or r['status']=='superado': raise ValueError('Alerta inexistente ou superado por versão posterior.')
                    con.execute('UPDATE alerts SET status=?,note=?,reviewer=? WHERE event_id=?',(status,note,profile,eid))
                    audit(con,'revisao',note,cid,profile)
                msg='Revisão humana registrada.'
            elif action=='evaluate':
                r=evaluate(path); msg=f'Avaliação concluída: {r["n"]} exemplos sintéticos. Consulte os limites abaixo.'
            else: return self.deny(400,'Ação desconhecida.')
        except (ValueError,TypeError) as exc:
            return self.deny(400,str(exc))
        except Exception as exc:
            print('[ERRO] Ação:',type(exc).__name__,flush=True)
            return self.deny(500,'A ação não pôde ser concluída. Consulte o terminal local.')
        query={'page':p.get('page','inicio'),'profile':profile,'msg':msg}
        if cid: query['case']=cid
        self.send('',303,headers={'Location':'/?'+urlencode(query)})


def main():
    parser=argparse.ArgumentParser(description='Amoras Jurídicas — POC sintética local sem dependências externas.')
    parser.add_argument('--port',type=int,default=5000)
    parser.add_argument('--host',default='0.0.0.0' if os.environ.get('FAROL_CONTAINER')=='1' else '127.0.0.1')
    parser.add_argument('--init-security',action='store_true')
    parser.add_argument('--secure',action='store_true',help='Prepara o segredo legado de implantação; o login usa contas no banco.')
    parser.add_argument('--db',default=str(DEFAULT_DB))
    parser.add_argument('--check-http',action='store_true',help='Verifica páginas com uma conta temporária de diagnóstico no servidor local.')
    parser.add_argument('--check-chat-http',action='store_true',help='Cria uma conversa de verificação pelo formulário real e aguarda a resposta local.')
    parser.add_argument('--ollama-status',action='store_true')
    parser.add_argument('--install-ollama',action='store_true')
    parser.add_argument('--serve-ollama',action='store_true')
    parser.add_argument('--pull-model',action='store_true')
    parser.add_argument('--test-agent',action='store_true')
    parser.add_argument('--compare-demo',action='store_true',help='Executa comparação demonstrativa e persiste o relatório no banco informado.')
    parser.add_argument('--test-chat',action='store_true')
    parser.add_argument('--case',default='CASO-002',help='Caso sintético para testar o modelo local.')
    parser.add_argument('--no-llm',action='store_true',help='Desativa inferência, preservando a pesquisa por política local.')
    parser.add_argument('--prepare-dev',action='store_true',help='Instala Poetry isolado e prepara .venv com lockfile.')
    parser.add_argument('--dev-check',action='store_true',help='Valida o projeto e executa testes através do Poetry.')
    parser.add_argument('--serve-dev',action='store_true',help='Inicia o painel com o Python da .venv gerenciada pelo Poetry.')
    parser.add_argument('--dev-smoke',action='store_true',help='Testa o modelo local através do ambiente Poetry.')
    parser.add_argument('--environment',action='store_true')
    parser.add_argument('--check-containers',action='store_true')
    parser.add_argument('--pin-images',action='store_true')
    args=parser.parse_args()
    if args.secure:
        from poc.access import init_secret
        os.environ['FAROL_ACCESS_TOKEN_FILE']=str(init_secret())
        os.environ['FAROL_REQUIRE_AUTH']='1'
    if args.init_security:
        from poc.access import init_secret
        init_secret();return
    if args.prepare_dev or args.dev_check or args.environment or args.serve_dev or args.dev_smoke or args.check_containers or args.pin_images:
        from poc.dev_setup import prepare,run_poetry,diagnose
        if args.prepare_dev:prepare()
        elif args.environment:print(jsondump(diagnose()))
        elif args.check_containers:
            from poc.dev_setup import check_containers
            check_containers()
        elif args.pin_images:
            from poc.dev_setup import pin_images
            pin_images()
        elif args.serve_dev:run_poetry(['run','python','run.py','--port',str(args.port)])
        elif args.dev_smoke:
            run_poetry(['run','python','run.py','--test-chat'])
            run_poetry(['run','python','run.py','--test-agent'])
        else:
            run_poetry(['check','--lock'])
            run_poetry(['run','pytest','-q'])
        return
    if args.ollama_status or args.install_ollama or args.serve_ollama or args.pull_model:
        from poc.local_runtime import status, install, serve, pull
        try:
            if args.ollama_status: print(jsondump(status()))
            elif args.install_ollama: install()
            elif args.serve_ollama: serve()
            else: pull()
        except Exception as exc:
            print('Ollama local: '+str(exc),flush=True)
            raise SystemExit(1)
        return
    if args.test_chat:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from poc.corpus import import_pdf
        from poc.chat import create_conversation,send_question,process_chat_one
        results=[]
        with TemporaryDirectory() as tmp:
            test_db=Path(tmp)/'chat-smoke.sqlite3'
            init(test_db);import_pdf(test_db)
            for mode,case,question in [('geral',None,'Responda apenas com uma saudação curta em português.'),('processo','CASO-003','O histórico de inscrições está disponível nos documentos fornecidos?'),('processo','CASO-001','Quais pedidos aparecem na petição inicial?'),('acervo',None,'O que a tese 7 diz sobre inscrição anterior legítima?')]:
                cid=create_conversation(mode,case,path=test_db)
                tid=send_question(cid,question,secrets.token_urlsafe(24),path=test_db)
                process_chat_one(test_db)
                with connect(test_db) as con:turn=dict(con.execute('SELECT * FROM chat_turns WHERE id=?',(tid,)).fetchone())
                print(mode,turn['status'],turn['answer'] or turn['error'],flush=True)
                if turn['status']!='concluida':raise SystemExit('Teste local do chat falhou.')
                results.append({'mode':mode,'answer':turn['answer'],'sources':json.loads(turn['sources']),'metrics':json.loads(turn['metrics'])})
        Path('docs/validacao_chat_local.json').write_text(jsondump({'scope':'Smoke test com modelo local e casos sintéticos; sem validação jurídica.','runs':results}))
        return
    if args.test_agent:
        from poc.corpus import import_pdf
        from poc.local_agent import run_agent
        init(args.db); import_pdf(args.db)
        with connect(args.db) as con:
            row=con.execute("SELECT body FROM documents WHERE case_id=? AND kind='evento'",(args.case,)).fetchone()
        if not row: raise SystemExit('Caso inexistente')
        result=run_agent(args.case,row[0],args.db)
        from pathlib import Path
        Path('data/agent_validation.json').write_text(jsondump(result))
        print(jsondump({k:v for k,v in result.items() if k not in ('trace','retrieved')}),flush=True)
        print('Ferramentas:',[t['tool'] for t in result['trace']])
        print('Teses:',[r['id'] for r in result['retrieved']])
        return
    if args.check_chat_http:
        from poc.http_probe import check_chat_http
        check_chat_http(args.port)
        return
    if args.check_http:
        from poc.http_probe import check_pages
        check_pages(args.port)
        return
    init(args.db)
    # Abas abertas continuam válidas após reinícios do servidor local.
    global TOKEN
    TOKEN=csrf_token(args.db,TOKEN)
    from poc.corpus import import_pdf
    try:
        print('Acervo PDF:',jsondump(import_pdf(args.db)),flush=True)
    except Exception as exc:
        print('Acervo não importado:',str(exc),flush=True)
    if args.no_llm:
        os.environ.pop('POC_OLLAMA_MODEL',None)
        os.environ['POC_DISABLE_LLM']='1'
    else:
        os.environ.pop('POC_DISABLE_LLM',None)
        from poc.local_runtime import status,MODEL
        local=status()
        if local['available'] and MODEL in local['models']:
            os.environ.setdefault('POC_OLLAMA_MODEL',MODEL)
    print('Pesquisa:',os.environ.get('POC_OLLAMA_MODEL','política local sem LLM'),flush=True)
    if args.compare_demo:
        from poc.demo_operations import compare_pending
        if args.case not in {c[0] for c in CASES}:raise SystemExit('Processo sintético inválido.')
        with connect(args.db) as con:
            con.execute("INSERT OR REPLACE INTO settings VALUES('comparison_pending',?)",(args.case,))
        compare_pending(args.db)
        with connect(args.db) as con:report=json.loads(con.execute("SELECT value FROM settings WHERE key='comparison_report'").fetchone()[0])
        print(jsondump({k:report[k] for k in ('case','native_agent','limitation')}))
        for mode in ('fixed','agent'):print(mode,jsondump({k:v for k,v in report[mode].items() if k not in ('trace','gaps')}))
        return
    if args.host!='127.0.0.1' and not (os.environ.get('FAROL_CONTAINER')=='1' and args.host=='0.0.0.0'):
        raise SystemExit('A escuta fora de loopback é permitida somente na configuração explícita do container.')
    access_secret=load_access_secret()
    server=Server((args.host,args.port),Handler)
    server.access_secret=access_secret
    server.user_auth=True
    server.db_path=args.db
    stop=threading.Event()
    thread=threading.Thread(target=worker,args=(stop,args.db),daemon=True)
    thread.start()
    print(f'\nAmoras Jurídicas disponível em http://127.0.0.1:{server.server_address[1]}\nDados sintéticos · Sem serviços pagos · Ctrl+C para encerrar\n',flush=True)
    def shutdown_signal(signum,frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,shutdown_signal)
    try:
        server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set(); thread.join(timeout=15); server.server_close()

if __name__=='__main__': main()
