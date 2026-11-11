"""Gráficos SVG locais gerados por Python. Sem JS ou bibliotecas externas."""
import html
import math

INK='#19414a'
PAPER='#efeee9'
PALETTE=['#19414a','#47717a','#78979d','#aabec0','#c9d5d4','#dce3df']

def e(value): return html.escape(str(value),quote=True)
def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) else 0
    except (TypeError,ValueError): return 0

def svg(content,width,height,title,cls='chart'):
    return f'<svg class="{cls}" viewBox="0 0 {width} {height}" role="img" aria-label="{e(title)}" xmlns="http://www.w3.org/2000/svg"><title>{e(title)}</title>{content}</svg>'

def bars(items,title,unit='',maximum=None):
    """(rótulo, valor), barras horizontais com origem em zero."""
    if not items: return '<div class="chart-empty">Sem medições</div>'
    vals=[max(0,number(v)) for _,v in items]
    top=max(vals+[number(maximum),1]); width=520;height=len(items)*49+28
    content=''
    for i,((label,_),v) in enumerate(zip(items,vals)):
        y=17+i*49; w=250*v/top
        shown=f'{v:g}{unit}'
        content+=f'<text x="0" y="{y+13}" class="chart-label">{e(label)}</text><rect x="170" y="{y}" width="250" height="20" rx="4" fill="#e4e8e3"/><rect x="170" y="{y}" width="{w:.3f}" height="20" rx="4" fill="{PALETTE[i%3]}"/><text x="435" y="{y+14}" class="chart-value">{e(shown)}</text>'
    return svg(content,width,height,title)

def donut(items,title,center=None,caption='total'):
    vals=[max(0,number(v)) for _,v in items];total=sum(vals)
    circumference=2*math.pi*63;offset=0
    parts='<circle cx="96" cy="96" r="63" fill="none" stroke="#e4e8e3" stroke-width="23"/>'
    for i,((label,_),v) in enumerate(zip(items,vals)):
        if not total or not v: continue
        length=v/total*circumference
        parts+=f'<circle cx="96" cy="96" r="63" fill="none" stroke="{PALETTE[i%len(PALETTE)]}" stroke-width="23" stroke-dasharray="{length:.4f} {circumference-length:.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 96 96)"><title>{e(label)}: {v:g}</title></circle>'
        offset+=length
    parts+=f'<text x="96" y="98" text-anchor="middle" class="donut-number">{e(center if center is not None else f"{total:g}")}</text><text x="96" y="119" text-anchor="middle" class="donut-caption">{e(caption)}</text>'
    legends=''
    for i,((label,_),v) in enumerate(zip(items,vals)):
        y=34+i*34
        legends+=f'<rect x="218" y="{y-9}" width="9" height="9" rx="2" fill="{PALETTE[i%len(PALETTE)]}"/><text x="240" y="{y}" class="chart-label">{e(label)}</text><text x="435" y="{y}" text-anchor="end" class="chart-value">{v:g}</text>'
    return svg(parts+legends,455,max(195,38+34*len(items)),title,'chart donut')

def matrix(rows,labels,title):
    """Matriz de confusão: linhas esperadas, colunas preditas."""
    size=55;left=135;top=40;peak=max([max(r) for r in rows]+[1]);c=''
    for i,label in enumerate(labels):
        c+=f'<text x="{left+i*size+size/2}" y="22" text-anchor="middle" class="chart-label">{e(label)}</text><text x="{left-12}" y="{top+i*size+32}" text-anchor="end" class="chart-label">{e(label)}</text>'
        for j,value in enumerate(rows[i]):
            fill=PALETTE[0] if value else '#e6e9e3';color=PAPER if value else '#71898c'
            c+=f'<rect x="{left+j*size}" y="{top+i*size}" width="{size-5}" height="{size-5}" rx="6" fill="{fill}"/><text x="{left+j*size+25}" y="{top+i*size+31}" text-anchor="middle" fill="{color}" font-size="17" font-weight="650">{value}</text>'
    c+=f'<text x="{left}" y="{top+len(labels)*size+20}" class="chart-footnote">Linhas: esperado · colunas: classificado</text>'
    return svg(c,430,top+len(labels)*size+40,title)

def tokens(items,title):
    if not items:return '<div class="chart-empty">Nenhuma execução LLM</div>'
    maximum=max([number(a)+number(b) for _,a,b in items]+[1]);out=''
    for i,(label,a,b) in enumerate(items):
        a=max(0,number(a));b=max(0,number(b));y=18+i*42
        out+=f'<text x="0" y="{y+13}" class="chart-label">{e(label)}</text><rect x="105" y="{y}" width="{290*a/maximum:.2f}" height="20" rx="3" fill="{INK}"/><rect x="{105+290*a/maximum:.2f}" y="{y}" width="{290*b/maximum:.2f}" height="20" fill="#aabec0"/><text x="410" y="{y+14}" class="chart-value">{a+b:g}</text>'
    out+=f'<text x="105" y="{len(items)*42+35}" class="chart-footnote">Entrada: escuro · saída: claro · total à direita</text>'
    return svg(out,480,len(items)*42+55,title)

def balance_curve(points,selected,title):
    if not points:return ''
    width=620;height=240;left=68;right=570;top=22;bottom=192
    low=min(0,min(y for _,y in points));high=max(1,max(y for _,y in points));span=high-low
    xmin=min(x for x,_ in points);xmax=max(x for x,_ in points)
    xp=lambda x:left+(x-xmin)/(xmax-xmin or 1)*(right-left)
    yp=lambda y:bottom-(y-low)/span*(bottom-top)
    out=''
    for y in [low,0,high]:
        sy=yp(y)
        out+=f'<line x1="{left}" y1="{sy:.2f}" x2="{right}" y2="{sy:.2f}" stroke="#d3dbd5"/><text x="{left-10}" y="{sy+4:.2f}" text-anchor="end" class="chart-label">{y/1000:.1f} mil</text>'
    out+='<polyline fill="none" stroke="#19414a" stroke-width="3" points="'+' '.join(f'{xp(x):.2f},{yp(y):.2f}' for x,y in points)+'"/>'
    for x in [xmin,(xmin+xmax)/2,xmax]:
        out+=f'<text x="{xp(x):.2f}" y="216" text-anchor="middle" class="chart-label">{x:g} min</text>'
    x,y=selected
    if xmin<=x<=xmax:
        out+=f'<circle cx="{xp(x):.2f}" cy="{yp(y):.2f}" r="6" fill="#19414a" stroke="#efeee9" stroke-width="3"><title>Cenário selecionado: {x:g} minutos, saldo R$ {y:.2f}</title></circle>'
    return svg(out,width,height,title)

def flow(nodes,title):
    out='';w=760;columns=3;boxw=218;boxh=76
    for i,(label,sub) in enumerate(nodes):
        row=i//columns;col=i%columns
        # Percurso serpenteado liga a primeira linha à segunda sem cruzar caixas.
        if row%2:col=columns-1-col
        x=10+col*250;y=16+row*126
        out+=f'<rect x="{x}" y="{y}" width="{boxw}" height="{boxh}" rx="10" fill="#19414a"/><text x="{x+16}" y="{y+23}" fill="#aabec0" font-size="10">{i+1:02d}</text><text x="{x+16}" y="{y+43}" fill="#efeee9" font-size="13" font-weight="600">{e(label)}</text><text x="{x+16}" y="{y+61}" fill="#c9d5d4" font-size="10">{e(sub)}</text>'
        if i<len(nodes)-1:
            if i%3==2:
                ax=x+boxw/2;ay=y+boxh
                out+=f'<path d="M{ax} {ay} v40 l-5 -7 m5 7 l5 -7" fill="none" stroke="#78979d" stroke-width="2"/>'
            elif row%2==0:
                ax=x+boxw;ay=y+boxh/2
                out+=f'<path d="M{ax+3} {ay} h24 l-6 -5 m6 5 l-6 5" fill="none" stroke="#78979d" stroke-width="2"/>'
            else:
                ax=x;ay=y+boxh/2
                out+=f'<path d="M{ax-3} {ay} h-24 l6 -5 m-6 5 l6 5" fill="none" stroke="#78979d" stroke-width="2"/>'
    return svg(out,w,math.ceil(len(nodes)/3)*126-20,title)
