"""Apresentação visual do laboratório. Dados e ações usam os serviços existentes."""
from collections import Counter
import json
import math
from statistics import median
from urllib.parse import urlencode
from . import charts
from .store import connect,allowed
from .ui import esc,badge,date,card,table,empty


def fold(title,body,opened=False):
    return f'<details class="fold" {"open" if opened else ""}><summary>{esc(title)}</summary><div class="fold-body">{body}</div></details>'


def metrics(items):
    return '<div class="metrics">'+''.join(f'<div class="metric"><p>{esc(title)}</p><strong>{esc(value)}</strong><span>{esc(note)}</span></div>' for title,value,note in items)+'</div>'


def head(title,note='',action=''):
    return f'<div class="section-head"><div><h2>{esc(title)}</h2>{f"<p>{esc(note)}</p>" if note else ""}</div><div class="actions">{action}</div></div>'


class DashboardMixin:
    def construcao(self):
        illustration=charts.svg('<rect x="32" y="32" width="116" height="89" rx="10" fill="none" stroke="#19414a" stroke-width="3"/><path d="M32 56h116M51 44h2m9 0h2m9 0h2M67 77l-12 11 12 11m46-22 12 11-12 11M97 72l-14 32" fill="none" stroke="#19414a" stroke-width="3" stroke-linecap="round"/><circle cx="142" cy="118" r="28" fill="#efeee9" stroke="#19414a" stroke-width="3"/><path d="M142 102v17l10 6" fill="none" stroke="#19414a" stroke-width="3" stroke-linecap="round"/>',185,165,'Página em preparação','construction-icon')
        return f'<section class="card construction-panel">{illustration}<span class="eyebrow">EM BREVE</span><h2>Estamos preparando esta página.</h2><p>Esta página está em construção. Volte mais tarde.</p><a class="button primary" href="{esc(self.url("inicio"))}">Voltar ao painel</a></section>'

    def chat(self):
        if self.profile!='gestor':return empty('Conversa disponível somente ao gestor.')
        import secrets
        from .chat import MODES
        with connect(self.path) as con:
            sessions=[dict(r) for r in con.execute('SELECT * FROM conversations ORDER BY updated DESC,id DESC LIMIT 60')]
            try:selected=int(self.q.get('conversation',sessions[0]['id'] if sessions else 0))
            except (TypeError,ValueError):selected=0
            session=con.execute('SELECT * FROM conversations WHERE id=?',(selected,)).fetchone()
            turns=[dict(r) for r in con.execute('SELECT * FROM chat_turns WHERE conversation_id=? ORDER BY id',(selected,))] if session else []
        if session:self.q['conversation']=str(selected)
        if session and self.q.get('delete')==str(selected):
            form='<p>Excluir esta conversa e todas as mensagens? A ação não pode ser desfeita.</p><label><input type="checkbox" name="confirm" value="excluir" required> Confirmo a exclusão da conversa.</label><button class="primary">Excluir definitivamente</button>'
            return card('Excluir conversa',self.fullform('chat_delete',form,{'conversation':selected,'page':'chat'})+f'<a class="button secondary" href="{esc(self.url("chat",conversation=selected))}">Cancelar</a>')
        fields='<label>Sobre o que deseja conversar?<select name="mode" required><option value="" selected disabled>Escolha o assunto</option><option value="acervo">Sobre o acervo</option><option value="processo">Sobre um ou mais processos</option><option value="ambos">Sobre o acervo e os processos</option></select></label><div class="chat-case-picker"><strong>Selecione os processos</strong><div class="chat-case-options">'+''.join(f'<label><input type="checkbox" name="cases" value="{r["id"]}"><span>{r["id"]} · {esc(r["title"])}</span></label>' for r in self.case_rows())+'</div></div><button class="primary">Nova conversa</button>'
        create='<div class="chat-create">'+self.fullform('chat_new',fields)+'</div>'
        history='<div class="chat-session-list">'+''.join(f'<a class="chat-session {"selected" if r["id"]==selected else ""}" href="{esc(self.url("chat",conversation=r["id"]))}"><strong>{esc(r["title"])}</strong><small>{esc(MODES["ambos" if r.get("include_acervo") else r["mode"]])}</small></a>' for r in sessions)+'</div>'
        bulk=''.join(f'<label class="chat-bulk-option"><input type="checkbox" name="conversation_ids" value="{r["id"]}"><span>{esc(r["title"])}</span></label>' for r in sessions)
        bulk=self.fullform('chat_delete_many',bulk+'<label class="chat-bulk-option"><input type="checkbox" name="confirm" value="excluir" required><span>Confirmo a exclusão definitiva das conversas selecionadas e suas mensagens.</span></label><button class="secondary">Excluir selecionadas</button>',{'page':'chat'}) if sessions else ''
        left=card('Conversas',create+fold('Histórico local',history or '<p>Nenhuma conversa ainda.</p>',opened=True)+(fold('Excluir várias conversas',bulk) if bulk else ''))
        if not session:
            welcome='<div class="chat-welcome"><span class="chat-orb">◌</span><h2>Converse com a Amoras Jurídicas</h2><p>Escolha um modo e crie uma conversa.</p><div class="chat-capabilities"><span>Acervo jurídico</span><span>Contexto do processo</span><span>Teses com página</span></div></div>'
            return '<div class="state-banner">Exclusivo do gestor de demonstração · Ollama local · sem alterações nos processos</div><div class="chat-layout">'+left+card('Assistente local',welcome)+'</div>'
        stream=''
        for turn in turns:
            stream+=f'<article class="chat-message user"><div class="chat-author">Você <time>{date(turn["created"])}</time></div><div class="chat-text">{esc(turn["question"])}</div></article>'
            if turn['status']=='concluida':
                sources=json.loads(turn['sources']);measure=json.loads(turn['metrics'])
                sourcecards=''.join(f'<div class="chat-source"><a href="{esc(r["url"])}" target="_blank" rel="noopener">[{esc(r["id"])}] {esc(r["title"])} ↗</a>{fold("Conferir trecho",f"<blockquote>{esc(r['body'])}</blockquote><p>{esc(r['origin'])}</p>")}</div>' for r in sources)
                foot=f'{measure.get("duration_ms",0)/1000:.2f} s · {measure.get("input_tokens",0)} / {measure.get("output_tokens",0)} tokens' if measure.get('llm_used') else 'Instrução suspeita bloqueada' if measure.get('reason')=='prompt_injection_bloqueada' else 'Demonstração estruturada · fontes identificadas' if measure.get('reason')=='demonstracao_estruturada' else 'Inventário conferido no banco' if measure.get('reason')=='inventario_verificado_no_banco' else 'Sem inferência: contexto não encontrado'
                stream+=f'<article class="chat-message assistant"><div class="chat-author">Amoras Jurídicas <span>{esc(foot)}</span></div><div class="chat-text">{esc(turn["answer"])}</div><div class="chat-references">{sourcecards or "<small>Sem fontes documentais declaradas nesta resposta.</small>"}</div></article>'
            elif turn['status']=='falhou':
                stream+=f'<article class="chat-message assistant"><div class="chat-author">Resposta não concluída</div><p class="error">{esc(turn["error"])}</p>{self.form("chat_retry","Tentar novamente",{"turn":turn["id"],"page":"chat"},"secondary")}</article>'
            else:
                stream+='<article class="chat-message assistant waiting" role="status"><span class="chat-orb">◌</span><span>Pensando em uma resposta…</span></article>'
        waiting=any(t['status'] in ('pendente','executando') for t in turns)
        if waiting:
            composer='<div class="chat-composer"><span class="panel-note">Aguarde a resposta. Esta conversa atualiza automaticamente.</span></div>'
        else:
            composer='<label for="chat-question">Sua mensagem<textarea id="chat-question" name="question" required maxlength="2000" rows="3" placeholder="Faça uma pergunta sobre este contexto…"></textarea></label><div class="chat-compose-actions"><span class="panel-note">Até 2.000 caracteres · histórico local</span><button class="primary">Enviar mensagem →</button></div>'
            composer='<div class="chat-composer">'+self.fullform('chat_send',composer,{'conversation':selected,'request_key':secrets.token_urlsafe(24),'page':'chat'})+'</div>'
            if session['mode']=='processo':
                from .chat_demonstrations import EXAMPLES
                shortcuts=''.join(self.form('chat_send',title,{'conversation':selected,'question':question,'request_key':secrets.token_urlsafe(24),'page':'chat'},'secondary') for title,question in EXAMPLES)
                composer=card('Exemplos de demonstração',shortcuts+'<p class="hint">Respostas estruturadas por roteiro local com fontes; sem geração livre de peça jurídica.</p>')+composer

        from .chat import session_cases
        label=MODES['ambos' if session['include_acervo'] else session['mode']]+(' · '+', '.join(session_cases(session)) if session['case_id'] else '')
        if not stream:
            examples={'geral':'Ex.: explique a diferença entre busca textual e semântica.','processo':'Ex.: quais documentos estão faltando neste caso?','acervo':'Ex.: o que a tese 7 diz sobre inscrição anterior?'}
            stream=f'<div class="chat-welcome"><span class="chat-orb">◌</span><h2>Como posso ajudar?</h2><p>{esc(examples[session["mode"]])}</p></div>'
        limits=fold('Contexto e limites','<p>O contexto fica fixo no modo e nos processos escolhidos. Em perguntas sobre vários processos, indique quais deseja comparar; as fontes identificam o processo de origem. A conversa geral não consulta documentos. O modo processo lê somente os processos selecionados; o modo acervo recupera trechos do PDF local; o modo combinado usa os dois conjuntos de fontes. O histórico é persistente, mas apenas interações recentes entram no contexto limitado do modelo.</p><p>Nos modos processo e acervo, o modelo seleciona trechos e o Python confere sua correspondência com as fontes; paráfrases jurídicas livres não são publicadas. Resumos, preparação de peça, triagem e conferência documental usam roteiros locais identificados com fontes do processo. Perguntas sobre disponibilidade de histórico são respondidas pelo banco. A conferência textual não valida relevância ou aplicabilidade jurídica. A compilação é de 2016. As mensagens não alteram processos, dossiês ou revisões.</p>')
        rename=fold('Renomear conversa',self.fullform('chat_rename',f'<label>Nome da conversa<input name="title" value="{esc(session["title"])}" required maxlength="100"></label><button class="secondary">Salvar nome</button>',{'conversation':selected,'page':'chat'}))
        panel='<section class="card chat-panel">'+head('Assistente local',label,'<span class="badge muted">Qwen3 1.7B</span>'+f'<a class="button secondary" href="{esc(self.url("chat",conversation=selected,delete=selected))}">Excluir conversa</a>')+rename+'<div class="chat-stream">'+stream+'</div>'+composer+limits+'</section>'
        return '<div class="state-banner">Exclusivo do gestor de demonstração · inferência local · respostas exigem conferência</div><div class="chat-layout">'+left+panel+'</div>'

    def latest_model_runs(self):
        ids={r['id'] for r in self.case_rows()}
        with connect(self.path) as con:
            rows=con.execute('SELECT case_id,event_id,body FROM dossiers ORDER BY event_id DESC').fetchall()
        found={}
        for row in rows:
            if row['case_id'] not in ids or row['case_id'] in found:continue
            d=json.loads(row['body'])
            if d.get('llm'):
                found[row['case_id']]={**d['llm'],'case':row['case_id'],'event':row['event_id'],'error':d.get('llm_error')}
        return sorted(found.values(),key=lambda r:r['case'])

    def inicio(self):
        cases=self.case_rows();ids={r['id'] for r in cases}
        with connect(self.path) as con:
            events=[dict(r) for r in con.execute('SELECT * FROM events ORDER BY id DESC') if r['case_id'] in ids]
            alerts=[dict(r) for r in con.execute('SELECT * FROM alerts') if r['case_id'] in ids]
            ds=[dict(r) for r in con.execute('SELECT * FROM dossiers') if r['case_id'] in ids]
            sources=[dict(r) for r in con.execute('SELECT * FROM sources')]
            tasks=[dict(r) for r in con.execute('SELECT t.*,e.case_id FROM tasks t JOIN events e ON e.id=t.event_id') if r['case_id'] in ids]
        publications=[r for r in events if r['source']=='DJEN simulado'];counts=Counter(r['category'] for r in publications)
        models=self.latest_model_runs();pending=sum(a['status']=='pendente' for a in alerts)
        top=metrics([('Processos',len(cases),'carteira sintética'),('Publicações',len(publications),'DJEN simulado'),('Para revisar',pending,'tarefas humanas'),('Dossiês',len(ds),'com evidências')])
        action=self.form('seed','Receber eventos',{'page':'inicio'}) if self.profile=='gestor' else self.link('Abrir carteira','processos')
        toolbar=head('Operação em um olhar','Fontes simuladas · modelo e pesquisa locais',action)
        items=[('Sentenças',counts['sentenca']),('Decisões',counts['decisao']),('Ordinárias',counts['ordinaria']),('A revisar',counts['incerto']),('Na fila',counts['pendente'])]
        items=[p for p in items if p[1]] or [('Sem publicações',0)]
        distribution=card('Triagem das publicações',charts.donut(items,'Distribuição das publicações por categoria',caption='publicações')+'<span class="panel-note">Metadados DataJud não entram nesta contagem.</span>')
        stages=[('Recebidas',len(publications)),('Classificadas',sum(r['category']!='pendente' for r in publications)),('Dossiês',len(ds)),('Pesquisa LLM',len(models)),('Revisadas',sum(a['status']=='revisado' for a in alerts))]
        funnel=card('Etapas do processamento',charts.bars(stages,'Quantidade de registros por etapa do processamento',maximum=max(1,len(publications))))
        lat=card('Tempo do modelo por processo',charts.bars([(r['case'],round(r['duration_ms']/1000,2)) for r in models],'Latência da última pesquisa local por processo',' s')+'<span class="panel-note">Último dossiê com modelo · medição local.</span>')
        state=Counter(r['status'] for r in tasks)
        queue=card('Fila de processamento',charts.donut([('Concluídas',state['concluida']),('Pendentes',state['pendente']),('Em execução',state['executando']),('Com falha',state['falhou'])],'Estado das tarefas persistidas',caption='tarefas'))
        sourcebody=''.join(f'<div class="source-row"><div><strong>{esc(s["name"])}</strong><small>{date(s["last_success"])}</small></div>{badge(s["status"])}</div>' for s in sources)
        recent=table(['Processo','Tipo','Versão'],[[self.link(r['case_id'],'processos',case=r['case_id']),badge(r['category']),f'v{r["version"]}'] for r in publications[:5]])
        return toolbar+top+'<div class="grid">'+distribution+funnel+lat+queue+'</div><div class="grid">'+card('Saúde das fontes',sourcebody)+card('Últimas publicações',recent)+'</div>'

    def processos(self):
        cases=self.case_rows();selected=self.q.get('case',cases[0]['id'] if cases else '')
        with connect(self.path) as con:
            if not allowed(con,selected,self.profile):return empty('Processo inexistente ou fora da carteira.')
            c=dict(con.execute('SELECT * FROM cases WHERE id=?',(selected,)).fetchone())
            docs=[dict(r) for r in con.execute('SELECT * FROM documents WHERE case_id=? ORDER BY kind',(selected,))]
            events=[dict(r) for r in con.execute('SELECT e.*,t.status task_status,t.error,a.status alert_status,a.note,a.reviewer FROM events e JOIN tasks t ON t.event_id=e.id LEFT JOIN alerts a ON a.event_id=e.id WHERE e.case_id=? ORDER BY e.id DESC',(selected,))]
            dossiers={r['event_id']:json.loads(r['body']) for r in con.execute('SELECT * FROM dossiers WHERE case_id=?',(selected,))}
        chips='<div class="case-list">'+''.join(f'<a class="case-chip {"selected" if r["id"]==selected else ""}" href="{esc(self.url("processos",case=r["id"]))}"><small>{esc(r["id"])}</small><strong>{esc(r["title"])}</strong><span>{r["pending"]} para revisar</span></a>' for r in cases)+'</div>'
        actions=self.form('ingest','Receber publicação',{'case':selected,'page':'processos'})+self.form('ingest','Sincronizar metadados',{'case':selected,'source':'DataJud simulado','page':'processos'},'secondary')
        title=head(c['title'],f'{selected} · {c["owner"]} · TJ-DEMO',actions)
        overview=metrics([('Documentos',len(docs),'na carteira'),('Eventos',len(events),'versões preservadas'),('Dossiês',len(dossiers),'rastreáveis'),('Revisão',sum(r['alert_status']=='pendente' for r in events),'pendências')])
        body=''
        for ev in events:
            meta=f'<div class="event-meta">{badge(ev["category"])} {badge(ev["task_status"])} <span>{esc(ev["source"])} · v{ev["version"]} · {date(ev["at"])}</span></div>'
            content=meta+fold('Publicação e classificação',f'<blockquote>{esc(ev["body"])}</blockquote><p>{esc(ev["reason"])}</p>')
            from .demo_operations import operational_triage
            triage=operational_triage(ev['category'],c['owner'])
            content+=card(triage['status'],f'<strong>Responsável: {esc(triage["owner"])}</strong><p>{esc(triage["checklist"])}</p><small>{esc(triage["notice"])}</small>')
            if ev['error']:content+=f'<p class="error">{esc(ev["error"])}</p>'
            if ev['id'] in dossiers:
                content+=self.dossier(dossiers[ev['id']],selected,ev['id'])
                content+=self.form('reprocess','Refazer pesquisa',{'event':ev['id'],'case':selected,'page':'processos'},'secondary')
            if ev['alert_status']:
                content+=f'<div class="review-status">Revisão {badge(ev["alert_status"])} <span>{esc(ev["note"])}</span></div>'
            if ev['alert_status'] and ev['alert_status']!='superado':
                form='<label>Registro da revisão<textarea name="note" required maxlength="1200" placeholder="Validação e próximo encaminhamento"></textarea></label><label>Estado<select name="status"><option value="revisado">Revisado pelo responsável</option><option value="pendente">Manter pendente</option></select></label><button class="primary">Salvar revisão</button>'
                content+=fold('Registrar revisão humana',self.fullform('review',form,{'event':ev['id'],'case':selected,'page':'processos'}))
            body+=card(f'Evento {ev["id"]:02d}',content)
        doclist=''.join(fold(d['title'],f'<p>{esc(d["body"])}</p><small>{esc(d["origin"])} · v{d["version"]} · SHA-256 {esc(d["hash"])}</small>') for d in docs)
        return chips+title+overview+(body or empty('Receba uma publicação para começar.'))+card('Documentos',doclist)

    def dossier(self,d,cid,eid):
        native=d.get('llm');checks=d['checks'];ok=sum(bool(r['supported']) for r in checks)
        tiles=metrics([('Evidências',len(d['evidence']),'snapshots'),('Âncoras',f'{ok}/{len(checks)}','correspondência textual'),('Teses',len(d.get('jurisprudence',[])),'recuperadas do PDF'),('Pesquisa',f'{d["duration_ms"]/1000:.2f} s','tempo total')])
        modeltools=[r for r in d['trace'] if r['reason'].startswith('Tool calling nativo')]
        toolnames={'consultar_documentos':'Ler documentos','pesquisar_jurisprudencia':'Buscar teses','concluir_pesquisa':'Encerrar pesquisa'}
        if modeltools:
            steps=[(toolnames.get(r['tool'],r['tool']),('consulta local' if r['tool']=='pesquisar_jurisprudencia' else 'carteira autorizada' if r['tool']=='consultar_documentos' else 'revisão humana')) for r in modeltools]
            visual=charts.flow(steps,'Ferramentas executadas pelo modelo, em ordem')
        else:
            visual=f'<div class="state-banner">{esc(d["mode"])}</div>'
        issues=''.join(f'<li>{esc(g)}</li>' for g in d['gaps']) or '<li>Nenhuma lacuna detectada automaticamente. Revisão jurídica permanece necessária.</li>'
        gaps=f'<div class="dossier-alert">{badge(d["status"])} <span>{len(d["gaps"])} pendência(s) / limite(s)</span></div>'+fold('Conferir pendências e limites','<ul>'+issues+'</ul>')
        findings=''.join(fold(f['claim'],f'<blockquote>{esc(f["quote"])}</blockquote><a href="#ev-{eid}-{esc(f["evidence"])}">Abrir evidência {esc(f["evidence"])}</a>') for f in d['findings'])
        legal=''.join(f'<div class="citation-tile"><div><strong>Tese {r["thesis"]:02d}</strong><span>STJ · edição 59 · p. {r["page"]}</span></div><a class="button secondary" href="{esc(r["url"])}" target="_blank" rel="noopener">PDF ↗</a>{fold("Trecho e precedentes",f"<blockquote>{esc(r['body'])}</blockquote><p>{esc(r['precedents'])}</p>")}</div>' for r in d.get('jurisprudence',[]))
        refs=''.join(fold(r['title'],f'<p>{esc(r["body"])}</p><a href="{esc(r["url"])}" target="_blank" rel="noreferrer noopener">Fonte oficial ↗</a><p class="hint">Paráfrase editorial.</p>') for r in d['references'])
        evidence=''.join(f'<div id="ev-{eid}-{esc(r["id"])}">'+fold(r['title'],f'<p>{esc(r["text"])}</p><small>{esc(r["source"])}</small>')+'</div>' for r in d['evidence'])
        trace=table(['Etapa','Ferramenta','Argumentos / resultado'],[[r['step'],esc(r['tool']),esc(json.dumps(r.get('arguments',{}),ensure_ascii=False))+'<br>'+esc(r['result'])] for r in d['trace']])
        if native:trace+=f'<p>Modelo: {esc(native["model"])} · prompt: {esc(native["prompt_version"])} · tokens: {native["input_tokens"]} entrada / {native["output_tokens"]} saída.</p>'
        export=f'<a class="button secondary" href="/export?{esc(urlencode({"event":eid,"profile":self.profile}))}">Exportar JSON ↓</a>'
        return f'<div class="dossier">{head("Dossiê de apoio",d["mode"],export)}{tiles}{visual}{gaps}{fold("Fatos e evidências",findings)}<h3>Teses recuperadas</h3><span class="panel-note">Compilação de 2016 · conferir atualidade e aplicabilidade.</span><div class="citation-grid">{legal or "Nenhuma tese recuperada."}</div>{fold("Referências editoriais",refs)}{fold("Snapshots das evidências",evidence)}{fold("Inspecionar execução",trace)}<p class="panel-note">Âncoras textuais não comprovam validade jurídica.</p></div>'

    def simulador(self):
        if self.profile!='gestor':return empty('Laboratório disponível no perfil Gestor.')
        with connect(self.path) as con:
            tasks=[dict(r) for r in con.execute('SELECT t.*,e.case_id,e.version FROM tasks t JOIN events e ON e.id=t.event_id ORDER BY t.id DESC')]
            sources=[dict(r) for r in con.execute('SELECT * FROM sources')]
            paused=con.execute("SELECT value FROM settings WHERE key='worker_paused'").fetchone()[0]=='1'
            duplicates=con.execute("SELECT count(*) FROM audit WHERE action='duplicata_ignorada'").fetchone()[0]
        counts=Counter(r['status'] for r in tasks)
        top=metrics([('Na fila',counts['pendente'],'persistidas'),('Em execução',counts['executando'],'trabalhador local'),('Falhas',counts['falhou'],'retomada manual'),('Duplicatas',duplicates,'ignoradas na ingestão')])
        scenarios=[('01','Ciclo completo','Seis casos → coleta → dossiês','seed','Receber eventos',{}),('02','Duplicidade','Mesmo evento → nenhuma duplicação','ingest','Reenviar CASO-001',{'case':'CASO-001'}),('03','Retificação','Nova versão → nova revisão','ingest','Criar versão 2',{'case':'CASO-002','correction':'1'}),('04','Interrupção','Próxima tarefa → falha controlada','fault','Armar falha',{}),('05','Retomada','Tarefas com falha → fila','retry','Retomar tarefas',{}),('06','Trabalhador','Controlar execução da fila','pause','Retomar' if paused else 'Pausar',{})]
        cards='<div class="three">'+''.join(f'<section class="card scenario"><span class="scenario-num">{n}</span><h2>{esc(t)}</h2><div class="scenario-path">{esc(note)}</div>{self.form(action,button,{"page":"simulador",**fields})}</section>' for n,t,note,action,button,fields in scenarios)+'</div>'
        src=''.join(f'<div class="source-row"><div><strong>{esc(s["name"])}</strong><small>{badge(s["status"])}</small></div>{self.form("source","Restaurar" if s["status"]=="indisponível" else "Interromper",{"source":s["name"],"page":"simulador"},"secondary")}</div>' for s in sources)
        fields='<label>Processo<select name="case">'+''.join(f'<option value="{r["id"]}">{r["id"]}</option>' for r in self.case_rows())+'</select></label><label>Fonte<select name="source"><option>DJEN simulado</option><option>DataJud simulado</option></select></label><button class="primary">Coletar</button>'
        tasktable=table(['Tarefa','Processo','Versão','Estado','Tentativas','Erro'],[[r['id'],esc(r['case_id']),r['version'],badge(r['status']),r['attempts'],esc(r['error'] or '—')] for r in tasks[:30]])
        queue=charts.bars([('Concluídas',counts['concluida']),('Pendentes',counts['pendente']),('Em execução',counts['executando']),('Com falha',counts['falhou'])],'Estado real da fila de tarefas')
        return self.collector_panel()+top+cards+'<div class="grid">'+card('Fila persistente',queue+badge('Pausado' if paused else 'Ativo'))+card('Fontes',src)+'</div><div class="grid">'+card('Coleta direcionada',self.fullform('ingest',fields,{'page':'simulador'}))+card('Evidência ausente','<div class="scenario-path">Histórico CASO-002 ⇄ retirar / restaurar</div>'+self.form('document','Alternar histórico',{'case':'CASO-002','page':'simulador'})+fold('Como validar','<p>Refaça a pesquisa e confira as pendências. Snapshots anteriores são preservados.</p>'))+'</div>'+card('Tarefas',fold('Abrir registros da fila',tasktable))

    def avaliacao(self):
        with connect(self.path) as con:row=con.execute('SELECT * FROM evaluations ORDER BY id DESC LIMIT 1').fetchone()
        toolbar=self.agent_comparison()+head('Qualidade em cenários controlados','Regressão sintética · não mede qualidade jurídica',self.form('evaluate','Executar avaliação',{'page':'avaliacao'}))
        if not row:return toolbar+empty('Execute a avaliação para gerar os gráficos.')+self.model_metrics()
        r=json.loads(row['body'])
        top=metrics([('Exemplos',r['n'],'sintéticos conhecidos'),('Acurácia',f'{r["accuracy"]:.0%}','triagem contextual'),('Recall',f'{r["recall"]:.0%}','decisões relevantes'),('Precisão',f'{r["precision"]:.0%}','decisões relevantes')])
        comparison=charts.bars([('Regra ingênua',round(r['baseline_accuracy']*100,1)),('Contextual',round(r['accuracy']*100,1))],'Comparação de acurácia nos exemplos conhecidos','%',100)
        labels=['sentenca','decisao','ordinaria','incerto'];short=['Sentença','Decisão','Ordinária','Revisão']
        confusion=[[sum(x['expected']==a and x['actual']==b for x in r['rows']) for b in labels] for a in labels]
        recovery=[]
        for c in r['comparisons']:
            recovery.extend([(c['case_id']+' · fixa',len(c['fixed']['required_found'])),(c['case_id']+' · adapt.',len(c['adaptive']['required_found']))])
        chartsbody='<div class="grid">'+card('Acurácia da classificação',comparison)+card('Matriz de confusão',charts.matrix(confusion,short,'Matriz de confusão da triagem contextual'))+'</div>'
        rec=card('Referências esperadas recuperadas',charts.bars(recovery,'Referências esperadas recuperadas por pesquisa fixa e adaptativa',maximum=max(c['adaptive']['required_total'] for c in r['comparisons']))+'<span class="panel-note">Comparação de políticas determinísticas · não compara LLMs.</span>')
        rows=table(['Texto','Esperado','Ingênua','Contextual'],[[esc(x['text']),badge(x['expected']),badge(x['baseline']),badge(x['actual'])] for x in r['rows']])
        return toolbar+top+chartsbody+rec+self.model_metrics()+card('Método e amostra',fold('Abrir resultados por exemplo',rows)+fold('Limites da avaliação',f'<p>{esc(r["limitation"])}</p><p>Executado em {date(r["at"])} · {r["duration_ms"]} ms.</p>'))

    def model_metrics(self):
        runs=self.latest_model_runs()
        if not runs:return card('Modelo local',empty('Nenhuma execução registrada.'))
        ms=[r['duration_ms'] for r in runs]
        headline=metrics([('Execuções',len(runs),'último dossiê por processo'),('Mediana',f'{median(ms)/1000:.2f} s','tempo do modelo'),('Ferramentas',sum(r['calls'] for r in runs),'chamadas registradas'),('Tokens',sum(r['input_tokens']+r['output_tokens'] for r in runs),'entrada + saída')])
        latency=charts.bars([(r['case'],round(r['duration_ms']/1000,2)) for r in runs],'Duração do modelo por processo',' s')
        tokenchart=charts.tokens([(r['case'],r['input_tokens'],r['output_tokens']) for r in runs],'Tokens de entrada e saída por processo')
        return head('Modelo local','Qwen3 1.7B · medições observadas, não benchmark')+headline+'<div class="grid">'+card('Latência',latency)+card('Tokens por execução',tokenchart)+'</div>'

    def acervo(self):
        from .corpus import search,WARNING
        with connect(self.path) as con:
            try:
                meta=con.execute('SELECT * FROM corpus_documents LIMIT 1').fetchone()
                rows=[dict(r) for r in con.execute('SELECT * FROM corpus_chunks ORDER BY thesis')]
            except Exception:return empty('Acervo ainda não importado.')
        if not meta:return empty('Acervo ainda não importado.')
        total=len(rows);inscope=sum(r['in_scope'] for r in rows);pages=Counter(r['page'] for r in rows)
        query=self.q.get('query','').strip()[:240]
        displayed=search(query,self.path,20,self.q.get('outside')=='1') if query else rows if self.q.get('outside')=='1' else [r for r in rows if r['in_scope']]
        top=metrics([('Teses',total,'extraídas do PDF'),('No recorte',inscope,'candidatas à pesquisa'),('Páginas',meta['pages'],'origem verificável'),('Publicação','2016','compilação histórica')])
        form=f'<form method="get" class="search-form"><input type="hidden" name="page" value="acervo"><input type="hidden" name="profile" value="{self.profile}"><label>Termos<input name="query" value="{esc(query)}" maxlength="240" placeholder="Súmula 385, inscrição anterior..."></label><label>Escopo<select name="outside"><option value="0">No recorte</option><option value="1" {"selected" if self.q.get("outside")=="1" else ""}>Todas as teses</option></select></label><button class="primary">Pesquisar</button></form>'
        chart=card('Cobertura temática',charts.donut([('No recorte',inscope),('Outras teses',total-inscope)],'Seleção temática das teses importadas',caption='teses'))
        bypage=card('Teses por página',charts.bars([(f'Página {p}',pages[p]) for p in range(1,meta['pages']+1)],'Distribuição das teses nas páginas do PDF'))
        provenance=f'<p>{esc(meta["title"])} · {total} teses · {meta["pages"]} páginas.</p><p>Publicação: {esc(meta["published"])} · corte declarado: {esc(meta["declared_cutoff"])}.</p><p>SHA-256: {esc(meta["hash"])}</p><p>{esc(WARNING)}</p><p>A tese 8 cita DJe de 16/05/2016, posterior ao corte declarado de 29/04/2016. Datas preservadas sem presumir uniformidade temporal.</p>'
        chunks='<div class="thesis-grid">'+''.join(f'<section class="card thesis-card"><span class="eyebrow">TESE {r["thesis"]:02d} / P. {r["page"]}</span><h3>{esc(r["body"][:105])}{"…" if len(r["body"])>105 else ""}</h3>{fold("Ler tese e precedentes",f"<blockquote>{esc(r['body'])}</blockquote><p>{esc(r['precedents'])}</p><small>Precedentes citados; inteiro teor não importado.</small>")}<a href="/corpus.pdf#page={r["page"]}" target="_blank" rel="noopener">Conferir PDF ↗</a></section>' for r in displayed)+'</div>'
        return top+'<div class="grid">'+chart+bypage+'</div>'+card('Pesquisar acervo',form)+'<p class="panel-note">Compilação histórica · não substitui acórdãos integrais ou revisão jurídica.</p>'+chunks+card('Proveniência',fold('Identificação, datas e limites',provenance)+'<a class="button secondary" href="/corpus.pdf" target="_blank" rel="noopener">Abrir PDF original ↗</a>')

    def arquitetura(self):
        nodes=[('Coleta simulada','DataJud + DJEN'),('Persistência','SQLite + documentos'),('Fila transacional','Trabalhador Python'),('Triagem','Regras + abstenção'),('Pesquisa local','Ollama + teses do STJ'),('Revisão humana','Alertas + evidências')]
        architecture=card('Do evento à revisão',charts.flow(nodes,'Arquitetura local: coleta, persistência, fila, triagem, pesquisa e revisão'))
        top=metrics([('Execução','Local','sem cloud'),('Modelo','1.7B','Qwen3 / Ollama'),('Ferramentas','≤ 6','por pesquisa do agente'),('Rodadas','≤ 4','limite do controlador')])
        loop=card('Ciclo do agente',charts.flow([('Consultar','documentos autorizados'),('Pesquisar','consultas ao acervo local'),('Encerrar','evidências → advogado')],'Ciclo de ferramentas do agente local'))
        components=table(['Módulo','Local','Evolução proposta / AWS'],[['Aplicação','Python HTTP','ECS/Fargate + FastAPI'],['Banco e busca','SQLite + FTS5','RDS PostgreSQL + pgvector'],['Fila','Tabela transacional','Outbox + SQS'],['Documentos','Snapshots locais','S3 + KMS'],['Modelo','Ollama Qwen3 1.7B','Avaliar local ou Bedrock'],['Fontes','Fixtures sintéticas','Validar DataJud / DJEN']])
        rules='<ul><li>Evento e tarefa na mesma transação; duplicatas por fonte, identificador e versão.</li><li>Pesquisa limitada ao processo autorizado; sem ferramentas de rede ou shell.</li><li>Ollama em loopback com cloud desabilitada no launcher.</li><li>Documento ilegível encaminhado à revisão sem inferência.</li><li>Falha do modelo aciona contingência explícita.</li></ul>'
        contract='<pre>'+esc(json.dumps({'source':'DJEN simulado','external_id':'CASO-001-PUBLICACAO','case_id':'CASO-001','version':1,'body':'Conteúdo sintético','hash':'SHA-256','at':'UTC'},indent=2,ensure_ascii=False))+'</pre><p>Contrato normalizado provisório, não payload oficial.</p>'
        return top+architecture+loop+card('Decisões técnicas',fold('Componentes e provedores',components)+fold('Regras de operação',rules)+fold('Contrato de evento',contract))

    def economia(self):
        def val(k,default,lo,hi):
            try:
                x=float(self.q.get(k,default));return min(hi,max(lo,x)) if math.isfinite(x) else default
            except (ValueError,TypeError):return default
        users=val('users',10,1,10000);minutes=val('minutes',45,0,480);rate=val('rate',120,0,10000);op=val('op',7300,0,1e8);initial=val('initial',60000,0,1e9)
        hours=users*22*minutes/60;benefit=hours*rate;net=benefit-op
        money=lambda v:'R$ '+f'{v:,.0f}'.replace(',','.')
        top=metrics([('Capacidade',f'{hours:.1f} h','liberada por mês'),('Benefício',money(benefit),'equivalente, não receita'),('Saldo',money(net),'benefício − operação'),('Retorno',f'{initial/net:.1f} meses' if net>0 else 'Sem retorno','se houver aproveitamento')])
        xmax=max(60,minutes);points=[(xmax*i/12,users*22*(xmax*i/12)/60*rate-op) for i in range(13)]
        curve=card('Saldo mensal × tempo poupado',charts.balance_curve(points,(minutes,net),'Sensibilidade do saldo econômico à economia líquida de minutos por advogado')+'<span class="panel-note">R$ por mês · minutos líquidos por advogado / dia · cenário fictício.</span>')
        breakdown=card('Operação mensal de referência',charts.donut([('Infraestrutura',2000),('IA e OCR',800),('Dados',1500),('Manutenção',3000)],'Composição hipotética do custo de produção',center='7,3 mil',caption='R$ / mês')+'<span class="panel-note">Referência de R$ 7.300; o cenário editável pode usar outro custo.</span>')
        fields=''.join(f'<label>{title}<input type="number" min="0" step="any" name="{key}" value="{v}"></label>' for key,title,v in [('users','Advogados',users),('minutes','Minutos líquidos / dia',minutes),('rate','Hora de capacidade (R$)',rate),('op','Operação mensal (R$)',op),('initial','Investimento inicial (R$)',initial)])
        form=f'<form method="get"><input type="hidden" name="page" value="economia"><input type="hidden" name="profile" value="{self.profile}"><div class="form-grid">{fields}</div><button class="primary">Recalcular gráficos</button></form>'
        point=op/(users*22*rate)*60 if rate else None
        assumptions='<p>22 dias úteis por mês. Tempo poupado já desconta revisão e correção. Valores fictícios, sem medição de produtividade humana.</p><p>Capacidade só vira resultado financeiro com demanda adicional rentável ou custo evitado. Implantação e adoção aumentam o prazo contado desde o início.</p>'
        return '<div class="state-banner">Simulação econômica · nenhum serviço contratado</div>'+top+'<div class="grid">'+curve+breakdown+'</div>'+card('Ajustar cenário',form)+card('Ponto de equilíbrio',f'<strong class="large-value">{f"{point:.1f} min/dia" if point is not None else "Sem equilíbrio com hora a R$ 0"}</strong>'+fold('Hipóteses e interpretação',assumptions))

    def seguranca(self):
        import os
        import sys
        secure=bool(os.environ.get('FAROL_ACCESS_TOKEN_FILE'))
        with connect(self.path) as con:
            blocked=con.execute("SELECT count(*) FROM audit WHERE action='seguranca_ia'").fetchone()[0] if self.profile=='gestor' else 0
            deleted=con.execute("SELECT count(*) FROM audit WHERE action='conversa_excluida'").fetchone()[0] if self.profile=='gestor' else 0
        top=metrics([('Acesso','Login e senha','contas no SQLite'),('Ambiente','.venv' if sys.prefix!=sys.base_prefix else 'Sistema','Python isolado' if sys.prefix!=sys.base_prefix else 'use Poetry'),('Eventos de IA',blocked,'bloqueios / quarentenas'),('Chats excluídos',deleted,'confirmações registradas')])
        controls=[('01','Contexto','Documentos fora do papel system'),('02','Entradas','Unicode, overrides e pedidos de segredo'),('03','Fontes','Quarentena antes da inferência'),('04','Ferramentas','Allowlist e argumentos vinculados ao caso'),('05','Saída','Trechos conferidos e conteúdo escapado'),('06','Operação','CSRF, origem, limites e auditoria')]
        tiles='<div class="three">'+''.join(f'<section class="card control-tile"><span class="control-check">✓</span><span class="eyebrow">{n}</span><h2>{t}</h2><span>{note}</span></section>' for n,t,note in controls)+'</div>'
        boundaries=charts.flow([('Dados não confiáveis','entrada + fontes + histórico'),('Controlador','inspeção + autorização'),('Modelo local','ferramentas de leitura')],'Fronteiras de segurança da entrada até a inferência')
        limits='<ul><li>Detecção textual é heurística: pode errar e não garante imunidade.</li><li>Contas são individuais; advogado usa a carteira fictícia Ana/Bruno. Cargos são escolhidos livremente apenas na demonstração.</li><li>Contas abertas protegem a entrada; MFA, recuperação de senha, TLS e autorização individual são melhorias futuras.</li><li>SQLite não é criptografado; secure_delete não elimina backups ou todo resíduo de WAL.</li><li>Compose validado; execução em containers depende de Docker Engine disponível.</li><li>Conferência textual não comprova aplicabilidade jurídica.</li></ul>'
        tests='<ol><li>Enviar uma instrução de ignorar regras e conferir bloqueio sem inferência.</li><li>Inserir instrução suspeita em um documento de teste e conferir quarentena.</li><li>Tentar ferramenta não permitida ou outro processo: o servidor deve rejeitar.</li><li>Excluir conversa em processamento: o resultado não pode recriá-la.</li></ol>'
        return top+tiles+card('Fronteiras do agente',boundaries)+card('Validação e limites',fold('Limites e execução',limits)+fold('Percurso de validação',tests))

    def auditoria(self):
        ids={r['id'] for r in self.case_rows()}
        with connect(self.path) as con:
            rows=[dict(r) for r in con.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200') if self.profile=='gestor' or r['case_id'] in ids]
        counts=Counter(r['action'] for r in rows)
        top=metrics([('Registros',len(rows),'janela de até 200'),('Recebidos',counts['evento_recebido'],'eventos'),('Duplicatas',counts['duplicata_ignorada'],'ignoradas'),('Revisões',counts['revisao'],'ações humanas')])
        chart=charts.bars(counts.most_common(7),'Ações mais frequentes na janela de auditoria')
        records=table(['UTC','Processo','Ação','Ator','Detalhe'],[[date(r['at']),esc(r['case_id'] or 'Global'),esc(r['action']),esc(r['actor']),esc(r['detail'])] for r in rows])
        return top+card('Distribuição das ações',chart)+card('Registros',fold('Abrir trilha detalhada',records))

    def collector_panel(self):
        with connect(self.path) as con:settings=dict(con.execute('SELECT key,value FROM settings'))
        enabled=settings.get('collector_enabled','1')=='1'
        return card('Coleta periódica simulada',metrics([('Intervalo','60 s','sem portais externos'),('Estado','Ativa' if enabled else 'Pausada','reconcilia versões'),('Último ciclo',date(settings.get('collector_last')) if settings.get('collector_last') else 'Aguardando','somente fixtures')])+self.form('collector','Pausar coleta' if enabled else 'Ativar coleta',{'page':'simulador'},'secondary')+'<small>Repete os mesmos snapshots: eventos novos entram uma vez. Retificações são criadas no laboratório.</small>')

    def agent_comparison(self):
        with connect(self.path) as con:settings=dict(con.execute('SELECT key,value FROM settings'))
        fields='<label>Mesmo processo para os dois modos<select name="case">'+''.join(f'<option value="{c["id"]}">{c["id"]}</option>' for c in self.case_rows())+'</select></label><button class="primary">Comparar fluxo fixo e agente</button>'
        body=self.fullform('compare_agent',fields,{'page':'avaliacao'})+f'<p>Estado: {esc(settings.get("comparison_state","não executado"))}</p>'
        if settings.get('comparison_report'):
            r=json.loads(settings['comparison_report']);f=r['fixed'];a=r['agent']
            body+=f'<strong>{esc(r["case"])} · {"Agente Ollama executado" if r["native_agent"] else "Contingência determinística; agente LLM não comprovado nesta execução"}</strong>'
            body+='<div class="grid">'+card('Duração observada',charts.bars([('Fixo',f['duration_ms']/1000),('Agente / política',a['duration_ms']/1000)],'Duração da execução',' s'))+card('Chamadas observadas',charts.bars([('Fixo',f['calls']),('Agente / política',a['calls'])],'Chamadas de ferramentas'))+'</div>'
            body+=table(['Modo','Referências','Teses','Lacunas'],[[esc(d['mode']),len(d['references']),len(d['theses']),len(d['gaps'])] for d in (f,a)])
            body+=fold('Inspecionar as duas execuções','<pre>'+esc(json.dumps(r,ensure_ascii=False,indent=2))+'</pre>')+f'<small>{esc(r["limitation"])}</small>'
        return card('Experimento: agente versus fluxo fixo',body)

    def comercial(self):
        return '<div class="state-banner">Demonstração comercial · valores fictícios · sem acesso a processos ou documentos</div>'+metrics([('Oportunidades',12,'simuladas'),('Propostas',5,'simuladas'),('Novos contratos',2,'simulados')])+card('Funil comercial',charts.bars([('Contato',12),('Qualificação',8),('Proposta',5),('Contrato',2)],'Funil fictício de vendas'))

    def financeiro(self):
        return '<div class="state-banner">Demonstração financeira · valores fictícios · sem acesso ao conteúdo processual</div>'+metrics([('Receita','R$ 45 mil','hipótese mensal'),('Despesas','R$ 30 mil','hipótese mensal'),('Saldo','R$ 15 mil','hipótese mensal')])+card('Cenário mensal',charts.bars([('Receita',45000),('Despesas',30000),('Saldo',15000)],'Valores fictícios',' R$'))

    def como_usar(self):
        from .roles import ROLES
        steps=[('Entre com sua conta','Seu perfil define as áreas disponíveis. Minha conta permite alterar nome e senha; o cargo permanece fixo.'),('Acompanhe as novidades','Gestor e TI podem acompanhar ou pausar a coleta simulada no laboratório. Advogados consultam a carteira atribuída em Processos.'),('Confira a triagem','Abra o evento, veja o responsável, o checklist e o dossiê. A atuação jurídica e os prazos exigem conferência humana.'),('Escolha o assunto do chat','Para gestor e TI: selecione acervo, processos ou ambos. Nos dois últimos, marque um ou mais processos antes de criar a conversa.'),('Confira as fontes','Leia os trechos e suas origens. O acervo atual é uma compilação histórica do STJ de 2016; não comprova entendimento vigente.'),('Organize suas conversas','Renomeie a conversa ou abra Excluir várias conversas, marque os históricos e confirme a exclusão definitiva.')]
        cards=''.join(card(title,f'<div class="help-step"><span class="help-number">{i}</span><span>{esc(text)}</span></div>') for i,(title,text) in enumerate(steps,1))
        examples=table(['Exemplo','Como usar'],[
            ['Resumir processo','Selecione CASO-002 e CASO-003 para conferir pedidos, defesa, decisão, divergências e histórico ausente com fontes por processo.'],
            ['Preparar uma peça','No CASO-002, confira o aviso sobre a sentença existente e a estrutura de trabalho com campos pendentes. Defina o objetivo da peça com o advogado.'],
            ['Conferir possível atuação','Selecione CASO-005 e CASO-006 para comparar movimentação ordinária e documento ilegível, com encaminhamento para revisão.'],
            ['Conferir documentos','Selecione CASO-002 e CASO-003 para conferir cronologia e documentos ausentes. Alterações no laboratório afetam as próximas respostas.'],
        ])
        instructions='<p>Gestor/CEO e TI: abra o chat, escolha processos ou ambos, marque os casos e crie uma conversa. Use os botões em Exemplos de demonstração e confira as fontes da resposta.</p>'
        limits='<p>Esses exemplos usam roteiros locais com documentos recuperados e fontes identificadas. A interface informa Demonstração estruturada. O conteúdo processual é sintético; a estrutura de peça contém campos a preencher e exige revisão jurídica. A análise de prazos e da necessidade de manifestação fica com o advogado.</p>'
        return '<div class="state-banner">Protótipo da arquitetura · processos fictícios · sem integração com tribunais</div><div class="three">'+cards+'</div>'+card('Exemplos de demonstração no chat',instructions+examples+limits)+card('Visões por perfil',table(['Perfil','Visão'],[[ROLES[r],text] for r,text in [('gestor','Todas as áreas'),('ti','Todas as áreas'),('advogado','Carteira atribuída e acervo'),('comercial','Funil comercial fictício'),('financeiro','Cenário financeiro e viabilidade')]]))

    def minha_conta(self):
        from .roles import ROLES
        if not self.q.get('_username'):return empty('Entre na sua conta para atualizar seu cadastro.')
        fields=f'<label>Nome<input name="display_name" required maxlength="100" autocomplete="name" value="{esc(self.q.get("_name",self.q["_username"]))}"></label><label>Login<input readonly value="{esc(self.q["_username"])}"></label><label>Cargo<input readonly value="{esc(ROLES[self.q["_role"]])}"></label>'
        fields+='<h3>Alterar senha</h3><p class="hint">Deixe os campos de senha vazios para atualizar somente o nome.</p><label>Senha atual<input type="password" name="current_password" maxlength="256" autocomplete="current-password"></label><label>Nova senha<input type="password" name="new_password" maxlength="256" autocomplete="new-password"></label><label>Confirmar nova senha<input type="password" name="confirm_password" maxlength="256" autocomplete="new-password"></label><button class="primary">Salvar cadastro</button>'
        return card('Meu cadastro','<div class="account-form">'+self.fullform('account_update',fields,{'page':'minha_conta'})+'</div><p class="hint">O login e o cargo não podem ser alterados aqui. A troca de senha encerra as sessões anteriores. MFA e recuperação de senha são melhorias futuras.</p>')
