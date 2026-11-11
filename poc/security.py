"""Controles determinísticos de fronteira para a IA; detecção heurística não é garantia."""
import base64
import hashlib
import html
import re
import unicodedata
from urllib.parse import unquote

class SecurityViolation(ValueError):
    pass


def normalized(text):
    value=str(text)
    for _ in range(2):value=unquote(html.unescape(value))
    value=''.join(c for c in unicodedata.normalize('NFKC',value) if unicodedata.category(c)!='Cf')
    value=''.join(c for c in unicodedata.normalize('NFKD',value.lower()) if not unicodedata.combining(c))
    return value

RULES=[
 ('override',r'(?:^|[\n.!?:;]\s*|por favor,?\s+|please\s+)(?:ignore|disregard|forget|esqueca|desconsidere|nao siga|ignorar)\b.{0,100}(?:instructions|instrucoes|regras|system|prompt|previous|anteriores|above|acima)'),
 ('role_spoof',r'<\|(?:im_start|system|developer|endoftext)[^>]*\|>|\[/?(?:inst|sys)\]|<<\s*/?sys\s*>>|(?:^|\n)\s*(?:system|developer|sistema|desenvolvedor)\s*:'),
 ('secret_request',r'\b(?:revele|mostre|imprima|exiba|reveal|print|dump|show)\b.{0,80}(?:system prompt|prompt (?:do )?sistema|api.?key|csrf|access.?token|senha|segredo|secret|credencia)'),
 ('code_execution',r'(?:os\.system|subprocess\.(?:run|popen)|eval\(|exec\(|__import__\(|/etc/shadow|/proc/self/environ|\.secrets/|id_ed25519)'),
 ('exfiltration',r'(?:envie|transmita|upload|send|exfiltrat|poste).{0,100}(?:segredo|secret|token|senha|credencia|chave|api.?key|documentos).{0,100}(?:https?://|webhook|servidor externo)'),
 ('secret_assignment',r'(?:farol_access_token|csrf_token|internal_secret|api_key)\s*[:=]\s*[^\s]{8,}'),
]


def injection_signals(text):
    value=normalized(text)
    found=[name for name,pattern in RULES if re.search(pattern,value,re.S)]
    # Inspeção limitada de um payload explicitamente apresentado para decodificação.
    if re.search(r'\b(?:decode|decodifi|base64)',value):
        for token in re.findall(r'[A-Za-z0-9+/]{24,}={0,2}',str(text))[:3]:
            if len(token)>4096:continue
            try:
                decoded=base64.b64decode(token,validate=True).decode('utf-8')
                if any(re.search(pattern,normalized(decoded),re.S) for _,pattern in RULES):found.append('encoded_instruction')
            except (ValueError,UnicodeError):pass
    return sorted(set(found))


def require_safe(text,label='entrada'):
    risks=injection_signals(text)
    from .access import load_access_secret
    secret=load_access_secret()
    if secret and secret in str(text):risks.append('credencial_local')
    if risks:raise SecurityViolation(f'{label}: instruções suspeitas bloqueadas ({", ".join(risks)}).')


def quarantine(sources):
    accepted=[];blocked=[]
    from .access import load_access_secret
    secret=load_access_secret()
    for source in sources:
        content=' '.join(str(source.get(k,'')) for k in ('title','body','origin','precedents'))
        risks=injection_signals(content)
        if secret and secret in content:risks.append('credencial_local')
        if risks:blocked.append({'id':source.get('id'),'rules':risks})
        else:accepted.append(source)
    return accepted,blocked


def untrusted_context(sources):
    """Envelope de dados separado do papel system; tamanho e IDs controlados pelo servidor."""
    import json
    return 'DADOS_NAO_CONFIAVEIS_JSON\n'+json.dumps({'fontes':[{'id':s['id'],'titulo':s['title'],'texto':s['body'],'limite':s['origin']} for s in sources]},ensure_ascii=False)


def safe_history(history,max_turns=6):
    # Um ataque persistido não ganha autoridade por aparecer como memória da conversa.
    from .access import load_access_secret
    secret=load_access_secret()
    return [t for t in history[-max_turns:] if not injection_signals(t.get('question','')) and not injection_signals(t.get('answer','')) and not (secret and secret in t.get('question','')+t.get('answer',''))]
