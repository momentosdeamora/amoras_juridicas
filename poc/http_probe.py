"""Verifica os formulários reais do chat em localhost, sem imprimir tokens."""
from html.parser import HTMLParser
import time
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request

class Forms(HTMLParser):
    def __init__(self):
        super().__init__();self.forms=[];self.current=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='form':
            self.current={'fields':{},'method':attrs.get('method','get'),'action':attrs.get('action','')};self.forms.append(self.current)
        elif tag=='input' and self.current is not None and attrs.get('name'):
            self.current['fields'][attrs['name']]=attrs.get('value','')
    def handle_endtag(self,tag):
        if tag=='form':self.current=None
    def find(self,action):
        return next((f['fields'].copy() for f in self.forms if f['fields'].get('action')==action),None)


def check_chat_http(port):
    base=f'http://127.0.0.1:{port}'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    policy=None
    def fetch(path,fields=None):
        nonlocal policy
        headers={'Content-Type':'application/x-www-form-urlencoded'}
        if fields:
            # Form POST sob no-referrer serializa Origin como null no navegador.
            headers['Origin']='null' if policy=='no-referrer' else base
        req=urllib.request.Request(base+path,data=urllib.parse.urlencode(fields).encode() if fields else None,headers=headers)
        try:
            with opener.open(req,timeout=10) as r:
                policy=r.headers.get('Referrer-Policy')
                return r.read().decode()
        except urllib.error.HTTPError as exc:
            page=exc.read().decode()
            reason='Token inválido' if 'Token inválido' in page else 'Origem não permitida' if 'Origem não permitida' in page else 'Acesso negado'
            raise RuntimeError(f'HTTP {exc.code}: {reason}') from exc
    html=fetch('/?page=chat&profile=gestor');p=Forms();p.feed(html)
    fields=p.find('chat_new')
    if not fields:
        login=next((f['fields'].copy() for f in p.forms if f['action']=='/login'),None)
        if login is not None:
            import secrets
            login.update({'username':'probe-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),'role':'gestor'})
            fetch('/register',login)
            html=fetch('/?page=chat&profile=gestor');p=Forms();p.feed(html);fields=p.find('chat_new')
    if not fields:raise RuntimeError('Formulário Nova conversa não encontrado')
    fields.update({'mode':'acervo','case':''})
    html=fetch('/action',fields);p=Forms();p.feed(html);fields=p.find('chat_send')
    if not fields:raise RuntimeError('Conversa criada, mas formulário de mensagem não encontrado')
    conversation=fields['conversation']
    print('Conversa de verificação criada pelo formulário real:',conversation,flush=True)
    fields['question']='O que a tese 7 diz sobre inscrição anterior legítima?'
    html=fetch('/action',fields)
    for _ in range(55):
        if 'Resposta não concluída' in html:raise RuntimeError('A conversa abriu, mas a resposta falhou. Consulte o histórico da conversa '+conversation)
        if 'Pensando em uma resposta' not in html and 'chat-message assistant' in html:
            print('Mensagem enviada, resposta recebida e histórico exibido. Fluxo HTTP completo OK.',flush=True)
            confirmation=fetch('/?'+urllib.parse.urlencode({'page':'chat','profile':'gestor','conversation':conversation,'delete':conversation}))
            parser=Forms();parser.feed(confirmation);delete_fields=parser.find('chat_delete')
            if not delete_fields:raise RuntimeError('Formulário de exclusão não encontrado.')
            delete_fields['confirm']='excluir'
            result=fetch('/action',delete_fields)
            if 'Conversa excluída.' not in result:raise RuntimeError('Exclusão da conversa de teste não confirmada.')
            print('Conversa de verificação excluída pelo formulário de confirmação.',flush=True)
            return
        time.sleep(1)
        html=fetch('/?'+urllib.parse.urlencode({'page':'chat','profile':'gestor','conversation':conversation}))
    raise RuntimeError('A conversa foi criada, mas não houve resposta no período de verificação.')


def check_pages(port):
    import json
    from .access import load_access_secret
    base=f'http://127.0.0.1:{port}'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with opener.open(base+'/',timeout=5) as response:
        body=response.read().decode();needs_login=urllib.parse.urlsplit(response.geturl()).path=='/login'
    if needs_login:
        import secrets
        parser=Forms();parser.feed(body)
        fields=next(f['fields'].copy() for f in parser.forms if f['action']=='/login')
        fields.update({'username':'probe-'+secrets.token_hex(8),'password':secrets.token_urlsafe(24),'role':'gestor'})
        req=urllib.request.Request(base+'/register',data=urllib.parse.urlencode(fields).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':base})
        with opener.open(req,timeout=5) as response:response.read()
    for page in ('','?page=processos','?page=simulador','?page=avaliacao','?page=arquitetura','?page=economia','?page=seguranca','?page=auditoria','?page=acervo','?page=chat','?page=comercial','?page=financeiro','?page=como_usar','?page=minha_conta','corpus.pdf','health'):
        with opener.open(base+'/'+page,timeout=5) as response:
            data=response.read()
            assert response.status==200 and data and urllib.parse.urlsplit(response.geturl()).path!='/login'
            if page=='corpus.pdf':assert data.startswith(b'%PDF-')
            print(f'HTTP {response.status} {page or "/"}: {len(data)} bytes',flush=True)
            if page=='health':print('Runtime:',json.loads(data),flush=True)
