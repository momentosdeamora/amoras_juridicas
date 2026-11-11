"""Instalação portátil e diagnóstico de Ollama. Cloud desabilitada no processo local."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent.parent
RUNTIME=ROOT/'.runtime'
MODEL='qwen3:1.7b'
def backend_url():
    value=os.environ.get('FAROL_OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
    parsed=urlsplit(value)
    names={'127.0.0.1','localhost'}
    if os.environ.get('FAROL_CONTAINER')=='1':names.add('ollama')
    if parsed.scheme!='http' or parsed.hostname not in names or parsed.port!=11434 or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Backend deve ser o Ollama local ou o serviço interno ollama:11434.')
    return value

BASE=backend_url()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirecionamento proibido na API local')


def local_request(endpoint, body=None, timeout=3):
    if endpoint not in {'/api/tags','/api/version','/api/chat','/api/show','/api/pull','/api/ps'}:
        raise ValueError('Endpoint local não permitido')
    data=json.dumps(body).encode() if body is not None else None
    request=urllib.request.Request(BASE+endpoint,data=data,headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(request,timeout=timeout) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError('Resposta local excede o limite')
    return json.loads(raw)


def status():
    try:
        version=local_request('/api/version')
        models=local_request('/api/tags')
        return {'available':True,'version':version.get('version'),'models':[m['name'] for m in models.get('models',[])],'endpoint':BASE,'cloud_policy':'A aplicação recusa nomes cloud e só chama loopback. O launcher próprio define OLLAMA_NO_CLOUD=1.'}
    except Exception as exc:
        return {'available':False,'error':str(exc)[:240],'models':[],'endpoint':BASE}


def install():
    """Download do fornecedor oficial para o workspace; sem sudo ou serviço global."""
    binary=RUNTIME/'ollama'/'bin'/'ollama'
    if binary.exists():
        print('Ollama portátil já instalado:',binary,flush=True)
        return binary
    if os.uname().machine!='x86_64': raise RuntimeError('Instalador portátil suporta somente Linux x86_64 neste projeto.')
    dest=RUNTIME/'ollama'; dest.mkdir(parents=True,exist_ok=True)
    archive=RUNTIME/'ollama-linux-amd64.tar.zst'
    url='https://ollama.com/download/ollama-linux-amd64.tar.zst'
    print('Baixando distribuição oficial do Ollama para .runtime/ (sem sudo).',flush=True)
    request=urllib.request.Request(url,headers={'User-Agent':'FarolLocal/1.0'})
    total=0; last=time.monotonic(); sha=hashlib.sha256()
    with urllib.request.urlopen(request,timeout=30) as response, archive.open('wb') as output:
        while chunk:=response.read(1024*1024):
            output.write(chunk);sha.update(chunk);total+=len(chunk)
            if total>5_000_000_000: raise RuntimeError('Distribuição excedeu 5 GB; instalação interrompida.')
            if time.monotonic()-last>10:
                print(f'Download Ollama: {total/1_000_000:.0f} MB',flush=True);last=time.monotonic()
    print(f'Arquivo recebido: {total/1_000_000:.0f} MB. Extraindo...',flush=True)
    try:
        with tarfile.open(archive,'r:*') as tar:
            tar.extractall(dest,filter='data')
    except (tarfile.ReadError,TypeError):
        raise RuntimeError('É necessário Python com suporte zstd e filtro seguro de extração (Python 3.14 recomendado).')
    if not binary.exists(): raise RuntimeError('Distribuição não contém bin/ollama')
    binary.chmod(0o755)
    (RUNTIME/'download_manifest.json').write_text(json.dumps({'url':url,'sha256':sha.hexdigest(),'bytes':total},indent=2))
    archive.unlink()
    print('Instalado em',binary,flush=True)
    return binary


def serve():
    binary=shutil.which('ollama') or str(RUNTIME/'ollama'/'bin'/'ollama')
    if not Path(binary).exists(): raise RuntimeError('Ollama não instalado. Execute python3 run.py --install-ollama')
    env=os.environ.copy()
    env.update({'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_NO_CLOUD':'1','OLLAMA_MODELS':str(RUNTIME/'models'),'OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1','OLLAMA_CONTEXT_LENGTH':'4096'})
    print('Ollama local: cloud desabilitada, modelos no workspace.',flush=True)
    subprocess.run([binary,'serve'],env=env,check=True)


def pull():
    """Apenas download do modelo público fixado; nenhuma inferência remota."""
    print(f'Baixando {MODEL} (~1,4 GB) pelo Ollama local. Sem inferência em nuvem.',flush=True)
    req=urllib.request.Request(BASE+'/api/pull',data=json.dumps({'model':MODEL,'stream':True}).encode(),headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    last=0
    with opener.open(req,timeout=60) as response:
        for line in response:
            row=json.loads(line)
            if row.get('error'): raise RuntimeError(row['error'])
            completed=row.get('completed',0); total=row.get('total',0)
            if time.monotonic()-last>8 or row.get('status')=='success':
                print(row.get('status'),f'{completed/total:.0%}' if total else '',flush=True);last=time.monotonic()
    print('Download concluído. Inferência será local.',flush=True)
