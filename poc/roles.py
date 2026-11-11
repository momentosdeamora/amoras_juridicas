"""Matriz de acesso da demonstração, aplicada no servidor."""
ROLES={'gestor':'Gestor / CEO','advogado':'Advogado','comercial':'Comercial','financeiro':'Financeiro','ti':'TI'}
PAGES={
 'advogado':{'processos','acervo'},
 'comercial':{'comercial'},
 'financeiro':{'financeiro','economia'},
}

def can_page(role,page):return role in ROLES and page in {'como_usar','minha_conta'} or role in {'gestor','ti'} or page in PAGES.get(role,set())
def home(role):return {'advogado':'processos','comercial':'comercial','financeiro':'financeiro'}.get(role,'inicio')
def demo_profile(account):return 'gestor' if account['role'] in {'gestor','ti'} else account['persona'] if account['role']=='advogado' else account['role']
def can_action(role,action):return role in ROLES and action=='account_update' or role in {'gestor','ti'} or role=='advogado' and action in {'ingest','review','reprocess'}
