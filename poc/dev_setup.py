"""Bootstrap explícito de ferramentas abertas, isoladas no workspace."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse

ROOT=Path(__file__).resolve().parent.parent
TOOLS=ROOT/'.tools'
POETRY_VERSION='2.2.1'


def tooling_env():
    env=os.environ.copy()
    env.update({'POETRY_VIRTUALENVS_IN_PROJECT':'true','POETRY_CACHE_DIR':str(TOOLS/'cache'),'POETRY_CONFIG_DIR':str(TOOLS/'config'),'POETRY_DATA_DIR':str(TOOLS/'data'),'VIRTUALENV_OVERRIDE_APP_DATA':str(TOOLS/'virtualenv-data'),'PIP_CACHE_DIR':str(TOOLS/'pip-cache'),'PYTHON_KEYRING_BACKEND':'keyring.backends.null.Keyring'})
    return env


def prepare():
    TOOLS.mkdir(exist_ok=True)
    pyz=TOOLS/'virtualenv.pyz'
    if not pyz.exists():
        print('Baixando virtualenv da distribuição oficial PyPA.',flush=True)
        with urllib.request.urlopen('https://bootstrap.pypa.io/virtualenv.pyz',timeout=30) as r:pyz.write_bytes(r.read(25_000_000))
    env=tooling_env();python=TOOLS/'poetry-env'/'bin'/'python'
    if not python.exists():subprocess.run([sys.executable,str(pyz),str(TOOLS/'poetry-env')],env=env,cwd=ROOT,check=True)
    poetry=TOOLS/'poetry-env'/'bin'/'poetry'
    if not poetry.exists():subprocess.run([str(python),'-m','pip','install',f'poetry=={POETRY_VERSION}'],env=env,cwd=ROOT,check=True)
    # Completar também os scripts de ativação da venv parcial criada sem ensurepip.
    if not (ROOT/'.venv'/'bin'/'activate').exists():subprocess.run([sys.executable,str(pyz),str(ROOT/'.venv')],env=env,cwd=ROOT,check=True)
    subprocess.run([str(poetry),'env','use',sys.executable],env=env,cwd=ROOT,check=True)
    subprocess.run([str(poetry),'lock'],env=env,cwd=ROOT,check=True)
    subprocess.run([str(poetry),'install','--no-interaction'],env=env,cwd=ROOT,check=True)
    print('Poetry e .venv preparados. Use .tools/poetry-env/bin/poetry run python run.py',flush=True)


def run_poetry(arguments):
    executable=TOOLS/'poetry-env'/'bin'/'poetry'
    if not executable.exists():raise RuntimeError('Execute python3 run.py --prepare-dev primeiro.')
    subprocess.run([str(executable),*arguments],cwd=ROOT,env=tooling_env(),check=True)


def diagnose():
    return {'python':sys.version.split()[0],'poetry':str(TOOLS/'poetry-env'/'bin'/'poetry') if (TOOLS/'poetry-env'/'bin'/'poetry').exists() else shutil.which('poetry'),'docker':shutil.which('docker'),'podman':shutil.which('podman'),'docker_socket':Path('/var/run/docker.sock').exists(),'rootlesskit':shutil.which('rootlesskit'),'newuidmap':shutil.which('newuidmap'),'venv':str(ROOT/'.venv')}


def check_containers():
    import hashlib
    import urllib.parse
    TOOLS.mkdir(exist_ok=True)
    executable=TOOLS/'docker-compose'
    if not executable.exists():
        url='https://github.com/docker/compose/releases/download/v2.40.3/docker-compose-linux-x86_64'
        print('Baixando Compose standalone do repositório oficial para validar a configuração.',flush=True)
        with urllib.request.urlopen(url,timeout=30) as r:data=r.read(120_000_000)
        with urllib.request.urlopen(url+'.sha256',timeout=30) as r:expected=r.read().decode().split()[0]
        if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Checksum do Compose não confere.')
        executable.write_bytes(data);executable.chmod(0o755)
    subprocess.run([str(executable),'version'],cwd=ROOT,check=True)
    subprocess.run([str(executable),'--profile','setup','config','--quiet'],cwd=ROOT,check=True)
    print('Compose validado. A execução dos containers ainda exige Docker Engine.',flush=True)


def pin_images():
    """Resolver somente imagens públicas do registry oficial; não usa credenciais do usuário."""
    items=[]
    for repository,tag,filename in [('library/python','3.14-slim','docker/Dockerfile.app'),('ollama/ollama','0.40.16','docker/Dockerfile.ollama')]:
        query=urllib.parse.urlencode({'service':'registry.docker.io','scope':f'repository:{repository}:pull'})
        with urllib.request.urlopen('https://auth.docker.io/token?'+query,timeout=20) as response:token=json.load(response)['token']
        req=urllib.request.Request(f'https://registry-1.docker.io/v2/{repository}/manifests/{tag}',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json'})
        with urllib.request.urlopen(req,timeout=20) as response:
            body=response.read();digest=response.headers.get('Docker-Content-Digest')
        import hashlib
        if digest!='sha256:'+hashlib.sha256(body).hexdigest():raise RuntimeError('Digest do manifesto não confere.')
        image=('python' if repository=='library/python' else repository)+':'+tag
        path=ROOT/filename;text=path.read_text()
        import re
        text=re.sub(r'(?m)^FROM '+re.escape(image)+r'(?:@sha256:[0-9a-f]+)?',f'FROM {image}@{digest}',text)
        path.write_text(text);items.append({'image':image,'digest':digest})
        print('Imagem fixada:',image,digest,flush=True)
    (ROOT/'docs'/'container_images.json').write_text(json.dumps(items,indent=2))
