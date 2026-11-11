"""Contas abertas de demonstração com papéis e carteira fictícia atribuída."""
import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie, CookieError
from .store import connect

COOKIE='amoras_session'

def register(username,password,path,role="advogado",persona="ana",display_name=""):
    from .roles import ROLES
    if role not in ROLES or persona not in {"ana","bruno"}:raise ValueError("Perfil inválido.")
    username=username.strip().casefold()
    display_name=(display_name.strip() or username)
    if len(display_name)>100:raise ValueError("O nome deve ter até 100 caracteres.")
    if not username or len(username)>80 or not password or len(password)>256:
        raise ValueError('Informe um login (até 80 caracteres) e uma senha (até 256).')
    salt=secrets.token_hex(16)
    hashed=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    with connect(path) as con:
        import sqlite3
        try:con.execute('INSERT INTO users(username,salt,password_hash,role,persona,display_name) VALUES(?,?,?,?,?,?)',(username,salt,hashed,role,persona,display_name))
        except sqlite3.IntegrityError:raise ValueError('Login já cadastrado. Entre com sua senha.') from None
    return username

def login(username,password,path):
    with connect(path) as con:row=con.execute('SELECT * FROM users WHERE username=?',(username.strip().casefold(),)).fetchone()
    # Derivar mesmo quando a conta não existe para reduzir diferenças de tempo.
    salt=row['salt'] if row else '00'*16
    candidate=hashlib.scrypt(password[:257].encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    if not row or not hmac.compare_digest(candidate,row['password_hash']):return None
    token=secrets.token_urlsafe(32)
    with connect(path) as con:
        con.execute('DELETE FROM user_sessions WHERE expires<?',(time.time(),))
        con.execute('INSERT INTO user_sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),row['id'],time.time()+28800))
    return f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'

def token_hash(cookie):
    try:
        jar=SimpleCookie();jar.load(cookie or '')
        return hashlib.sha256(jar[COOKIE].value.encode()).hexdigest()
    except (KeyError,CookieError):return ''

def current_user(cookie,path):
    with connect(path) as con:
        row=con.execute('SELECT u.id,u.username,u.display_name,u.role,u.persona FROM user_sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',(token_hash(cookie),time.time())).fetchone()
    return dict(row) if row else None

def logout(cookie,path):
    with connect(path) as con:con.execute('DELETE FROM user_sessions WHERE token_hash=?',(token_hash(cookie),))
    return f'{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'


def update_account(cookie,name,current_password,new_password,confirmation,path):
    name=name.strip()
    if not 1<=len(name)<=100:raise ValueError('Informe um nome de 1 a 100 caracteres.')
    with connect(path) as con:
        con.execute('BEGIN IMMEDIATE')
        user=con.execute('SELECT u.* FROM users u JOIN user_sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>?',(token_hash(cookie),time.time())).fetchone()
        if not user:raise ValueError('Sessão expirada. Entre novamente.')
        if new_password or confirmation:
            if not 1<=len(new_password)<=256 or new_password!=confirmation:raise ValueError('A nova senha e a confirmação devem coincidir (até 256 caracteres).')
            candidate=hashlib.scrypt(current_password[:257].encode(),salt=bytes.fromhex(user['salt']),n=16384,r=8,p=1).hex()
            if not hmac.compare_digest(candidate,user['password_hash']):raise ValueError('A senha atual está incorreta.')
            salt=secrets.token_hex(16)
            hashed=hashlib.scrypt(new_password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
            con.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,user['id']))
            con.execute('DELETE FROM user_sessions WHERE user_id=?',(user['id'],))
        con.execute('UPDATE users SET display_name=? WHERE id=?',(name,user['id']))
        from .store import audit
        audit(con,'conta_atualizada','Nome atualizado'+(' e senha alterada; sessões anteriores revogadas.' if new_password else '.'),actor=user['username'])
    return login(user['username'],new_password,path) if new_password else None
