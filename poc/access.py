"""Autenticação local opcional, obrigatória no Compose; sem dependência do modelo."""
from collections import deque
import hashlib
import hmac
from http.cookies import SimpleCookie,CookieError
import os
from pathlib import Path
import secrets
import threading
import time

COOKIE='farol_session'
_LOCK=threading.Lock()


def load_access_secret():
    filename=os.environ.get('FAROL_ACCESS_TOKEN_FILE')
    if not filename:
        if os.environ.get('FAROL_REQUIRE_AUTH')=='1':raise RuntimeError('FAROL_ACCESS_TOKEN_FILE é obrigatório neste ambiente.')
        return None
    value=Path(filename).read_text().strip()
    if len(value)<32:raise RuntimeError('Chave de acesso deve ter ao menos 32 caracteres.')
    return value


def issue_cookie(secret):
    payload=f'{int(time.time())}.{secrets.token_hex(16)}'
    signature=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return f'{COOKIE}={payload}.{signature}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'


def authenticated(cookie,secret):
    if not secret:return True
    try:
        parsed=SimpleCookie();parsed.load(cookie or '')
        value=parsed[COOKIE].value
        stamp,nonce,signature=value.split('.')
        age=time.time()-int(stamp)
        expected=hmac.new(secret.encode(),f'{stamp}.{nonce}'.encode(),hashlib.sha256).hexdigest()
        return 0<=age<28800 and hmac.compare_digest(signature,expected)
    except (ValueError,KeyError,CookieError):return False


def limited(server,key,limit=120,period=60):
    with _LOCK:
        if not hasattr(server,'rate_windows'):server.rate_windows={}
        window=server.rate_windows.setdefault(key,deque())
        current=time.monotonic()
        while window and window[0]<current-period:window.popleft()
        if len(window)>=limit:return True
        window.append(current)
        return False


def init_secret():
    root=Path(__file__).resolve().parent.parent/'.secrets'
    root.mkdir(mode=0o700,exist_ok=True)
    filename=root/'access_token'
    if not filename.exists():
        fd=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(48)+'\n')
    print('Chave local preparada em .secrets/access_token (não versionada).')
    return filename
