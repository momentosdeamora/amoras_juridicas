"""Gera diagramas C4 do protótipo em SVG com Inter incorporada.
Requer a fonte Inter instalada; exportação PNG opcional com rsvg-convert.
"""
from pathlib import Path
from html import escape
import base64
import shutil
import subprocess
from functools import lru_cache

try:
    from PIL import ImageFont
except ImportError:
    ImageFont=None

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'static'/'img'
INK='#19414a';PAPER='#efeee9'

FONT_PATHS={}

def font(weight):
    name='Inter:style=Bold' if weight==700 else 'Inter:style=Regular'
    path=Path(subprocess.check_output(['fc-match','-f','%{file}',name],text=True))
    if 'inter' not in path.name.lower():raise RuntimeError('Instale a fonte Inter para gerar os diagramas.')
    FONT_PATHS[weight]=path
    data=base64.b64encode(path.read_bytes()).decode()
    return f"@font-face{{font-family:InterEmbedded;src:url(data:font/otf;base64,{data}) format('opentype');font-weight:{weight};}}"
STYLE=font(400)+font(700)

def text(x,y,lines,size=20,color=INK,weight=400,anchor='start',gap=None):
    gap=gap or size*1.5
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else gap}">{escape(line)}</tspan>' for i,line in enumerate(lines))+'</text>'

@lru_cache(maxsize=256)
def measure(value,size,weight=400):
    if ImageFont:
        font=ImageFont.truetype(str(FONT_PATHS[weight]),size)
        return font.getlength(value)
    # Margem conservadora para ambientes sem Pillow.
    return len(value)*size*.85


def wrap(lines,width,size,weight=400):
    result=[]
    for line in lines:
        current=''
        for word in line.split():
            candidate=(current+' '+word).strip()
            if current and measure(candidate,size,weight)>width:
                result.append(current);current=word
            else:current=candidate
        if current:result.append(current)
    return result


def box(x,y,w,h,title,kind,lines,dark=False,person=False):
    bg,fg=(INK,PAPER) if dark else (PAPER,INK)
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{bg}" stroke="{INK}" stroke-width="2"/>'
    if person:
        s+=f'<circle cx="{x+36}" cy="{y+30}" r="9" fill="{INK}"/><path d="M{x+21} {y+52} q0 -19 15 -19 q15 0 15 19" fill="{INK}"/>'
        tx=x+65
    else:tx=x+24
    title_size=24
    while measure(title,title_size,700)>x+w-24-tx:title_size-=1
    assert title_size>=16, title
    s+=text(tx,y+37,[title],title_size,fg,700)
    kind_lines=wrap([kind],w-48,15)
    s+=text(x+24,y+68,kind_lines,15,fg,gap=21)
    body_y=y+105+(len(kind_lines)-1)*21
    size=18
    while True:
        body=wrap(lines,w-48,size)
        gap=size*1.5
        if body_y+(len(body)-1)*gap+size*.3<=y+h-20:break
        size-=1
        assert size>=15, title
    assert all(measure(line,size)<=w-48 for line in body),title
    s+=text(x+24,body_y,body,size,fg,gap=gap)
    return s


def arrow(path,label,x,y):
    s=f'<path d="{path}" fill="none" stroke="{INK}" stroke-width="2" marker-end="url(#arrow)"/>'
    if label:
        lines=label.split('\n');w=max(measure(l,16) for l in lines)+20;h=len(lines)*24+8
        s+=f'<rect x="{x-w/2}" y="{y-18}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>'
        s+=text(x,y,lines,16,anchor='middle',gap=24)
    return s

def frame(title,subtitle,h):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="{h}" viewBox="0 0 1600 {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc><defs><style>{STYLE}text{{font-family:InterEmbedded,Inter,sans-serif}}</style><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="{INK}"/></marker></defs><rect width="1600" height="{h}" fill="{PAPER}"/>'''+text(60,65,[title],35,weight=700)+text(60,105,[subtitle],19)

def write(name,svg):
    (OUT/(name+'.svg')).write_text(svg+'</svg>')
    if shutil.which('rsvg-convert'):
        subprocess.run(['rsvg-convert','-w','3200',str(OUT/(name+'.svg')),'-o',str(OUT/(name+'.png'))],check=True)

s=frame('Amoras Jurídicas | C4 • Nível 1','Contexto do sistema • protótipo local implementado',1060)
s+=box(550,385,500,240,'Amoras Jurídicas','[Sistema de software]', ['Centraliza novidades simuladas,','organiza documentos e evidências','e apoia a revisão jurídica.'],dark=True)
s+=box(60,175,350,185,'Gestor / CEO','[Pessoa]', ['Acompanha carteira, indicadores','e pendências de toda a operação.'],person=True)
s+=box(60,440,350,185,'Advogado','[Pessoa]', ['Consulta a carteira atribuída','e registra revisão dos eventos.'],person=True)
s+=box(60,705,350,185,'Comercial','[Pessoa]', ['Consulta o funil comercial','com dados demonstrativos.'],person=True)
s+=box(1190,300,350,185,'TI','[Pessoa]', ['Acompanha a operação e acessa','as áreas administrativas.'],person=True)
s+=box(1190,615,350,185,'Financeiro','[Pessoa]', ['Consulta cenários financeiros','e hipóteses econômicas.'],person=True)
s+=arrow('M410 270 H480 V430 H550','Acompanha\na operação',480,320)
s+=arrow('M410 530 H550','Consulta\ne revisa',480,510)
s+=arrow('M410 795 H480 V580 H550','Consulta\no funil',480,685)
s+=arrow('M1190 390 H1120 V455 H1050','Administra\ne monitora',1120,345)
s+=arrow('M1190 710 H1120 V565 H1050','Consulta\ncenários',1120,660)
s+=text(60,950,['Legenda: pessoa = perfil de usuário | caixa escura = sistema em escopo | seta = uso do sistema'],17)
s+=text(60,990,['Fontes judiciais são simuladas; não há sistema de tribunal conectado neste protótipo.'],18)
write('c4_contexto',s)

s=frame('Amoras Jurídicas | C4 • Nível 2','Containers do sistema • unidades de execução e armazenamento',1160)
s+=f'<rect x="390" y="170" width="1150" height="805" rx="22" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="9 7"/>'
s+=text(420,210,['Amoras Jurídicas • limite do sistema'],20,weight=700)
s+=box(40,430,300,210,'Usuário autorizado','[Pessoa]', ['Utiliza as áreas permitidas','ao cargo e à carteira','por navegador local.'],person=True)
s+=box(440,390,520,300,'Aplicação web Python','[Container: Python / HTTP / HTML / CSS]', ['Login, autorização, painéis e chat.','Inclui trabalhador em thread, triagem,','agente e roteiros demonstrativos.','Fila de tarefas persistida no SQLite.'],dark=True)
s+=box(1110,245,380,175,'Banco de dados','[Container: SQLite / FTS5]', ['Contas, processos, tarefas,','dossiês, conversas e auditoria.'])
s+=box(1110,490,380,175,'Inferência local','[Container: Ollama / Qwen3 1.7B]', ['Solicita ferramentas e seleciona','trechos em respostas estruturadas.'])
s+=box(1110,770,380,165,'Arquivos locais','[Container: sistema de arquivos]', ['PDF histórico do STJ','e pesos do modelo local.'])
s+=arrow('M340 535 H440','Acessa\nHTTP',390,493)
s+=arrow('M960 440 H1020 V330 H1110','Persiste e consulta\nSQL / sqlite3',1008,275)
s+=arrow('M960 550 H1110','Solicita\ninferência\nHTTP / JSON',1035,485)
s+=arrow('M820 690 V850 H1110','Lê o PDF\nSistema de arquivos',950,803)
s+=arrow('M1300 665 V770','Carrega pesos',1390,714)
s+=text(60,1020,['Legenda: caixa escura = aplicação principal | caixa clara = pessoa ou container | tracejado = limite do sistema'],17)
s+=text(60,1060,['O trabalhador executa em uma thread da aplicação Python; não é um serviço independente.'],18)
s+=text(60,1095,['Container C4 representa uma aplicação ou armazenamento; não implica execução em Docker.'],18)
write('c4_containers',s)
print('Gerados c4_contexto e c4_containers em SVG e PNG.')
