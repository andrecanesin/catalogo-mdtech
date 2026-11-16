"""Gestão dos vendedores: usada pela tela de administração (app.py, /conta.py/admin/...) e pelo admin.py (terminal).
Cada operação grava no histórico (tabela eventos) quem fez o quê. Erros de uso viram GestaoErro com texto para a tela."""
import re

from . import banco as B
from . import senhas as S

EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GestaoErro(ValueError):
    pass


def _usuario(db, email):
    u = db.usuario(email)
    if not u:
        raise GestaoErro(f"{B.normalizar_email(email)} não está cadastrado.")
    return u


def adicionar(db, email, nome="", autor="terminal"):
    email = B.normalizar_email(email)
    if not EMAIL_OK.match(email) or len(email) > 200:
        raise GestaoErro("E-mail inválido.")
    if db.usuario(email):
        raise GestaoErro(f"{email} já está cadastrado. Use \"Nova senha\" se ele esqueceu a senha.")
    senha = S.senha_inicial()
    db.criar_usuario(email, S.gerar_hash(senha), (nome or "").strip()[:100])
    db.registrar_evento(autor, "cadastrou", email)
    return senha


def redefinir(db, email, autor="terminal"):
    """Nova senha inicial (esqueceu a senha): desconecta os aparelhos, zera o bloqueio e obriga a trocar no próximo acesso."""
    u = _usuario(db, email)
    senha = S.senha_inicial()
    db.definir_senha(u["id"], S.gerar_hash(senha), trocar_senha=True)
    db.encerrar_sessoes(u["id"])
    db.limpar_falhas("email:" + u["email"])
    db.registrar_evento(autor, "gerou nova senha para", u["email"])
    return senha


def desativar(db, email, autor="terminal"):
    u = _usuario(db, email)
    if B.normalizar_email(autor) == u["email"]:
        raise GestaoErro("Você não pode desativar a sua própria conta.")
    db.definir_ativo(u["id"], False)
    db.registrar_evento(autor, "desativou", u["email"])


def reativar(db, email, autor="terminal"):
    """Volta a valer com senha inicial nova (a antiga pode ter ficado com quem saiu)."""
    u = _usuario(db, email)
    senha = S.senha_inicial()
    db.definir_senha(u["id"], S.gerar_hash(senha), trocar_senha=True)
    db.definir_ativo(u["id"], True)
    db.limpar_falhas("email:" + u["email"])
    db.registrar_evento(autor, "reativou", u["email"])
    return senha


def desbloquear(db, email, autor="terminal"):
    u = _usuario(db, email)
    db.limpar_falhas("email:" + u["email"])
    db.registrar_evento(autor, "desbloqueou", u["email"])


def definir_admin(db, email, admin, autor="terminal"):
    u = _usuario(db, email)
    if not admin and B.normalizar_email(autor) == u["email"]:
        raise GestaoErro("Você não pode tirar o seu próprio acesso de administrador.")
    db.definir_admin(u["id"], admin)
    db.registrar_evento(autor, "tornou administrador" if admin else "tirou o acesso de administrador de", u["email"])


def definir_nome(db, email, nome, autor="terminal"):
    u = _usuario(db, email)
    db.definir_nome(u["id"], (nome or "").strip()[:100])
    db.registrar_evento(autor, "alterou o nome de", u["email"])


def listar(db):
    out = []
    for u in db.listar():
        n, _ = db.falhas("email:" + u["email"])
        out.append({"email": u["email"], "nome": u["nome"], "ativo": bool(u["ativo"]), "admin": bool(u["admin"]),
                    "trocar_senha": bool(u["trocar_senha"]), "ultimo_login": u["ultimo_login"], "criado": u["criado"],
                    "bloqueado": n >= B.MAX_POR_EMAIL})
    return out


def historico(db, limite=50):
    return [{"quando": e["quando"], "autor": e["autor"], "acao": e["acao"], "alvo": e["alvo"]} for e in db.eventos(limite)]
