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


def adicionar(db, email, nome="", autor="terminal", convite=False):
    """convite=True (tela): devolve o código do link para o vendedor criar a senha; a senha sorteada nunca é mostrada.
    convite=False (terminal): devolve uma senha inicial."""
    email = B.normalizar_email(email)
    if not EMAIL_OK.match(email) or len(email) > 200:
        raise GestaoErro("E-mail inválido.")
    if db.usuario(email):
        raise GestaoErro(f"{email} já está cadastrado. Use \"Enviar convite\" ou \"Enviar link de nova senha\".")
    senha = S.senha_inicial()
    db.criar_usuario(email, S.gerar_hash(senha), (nome or "").strip()[:100])
    db.registrar_evento(autor, "cadastrou", email)
    if convite:
        return convidar(db, email, autor)[0]
    return senha


def convidar(db, email, autor="terminal"):
    """Link de uso único (7 dias) para criar a senha: 'convite' para quem nunca criou, 'nova senha' para quem esqueceu.
    A senha atual continua valendo até o link ser usado. Devolve (código, tipo)."""
    u = _usuario(db, email)
    if not u["ativo"]:
        raise GestaoErro(f"{u['email']} está desativado. Use \"Reativar\".")
    tipo = "convite" if u["trocar_senha"] else "nova senha"
    token = db.criar_convite(u["id"])
    db.registrar_evento(autor, "enviou convite para" if tipo == "convite" else "enviou link de nova senha para", u["email"])
    return token, tipo


def ver_convite(db, token):
    u = db.convite(token)
    if not u:
        raise GestaoErro("Este link expirou ou já foi usado. Peça um novo ao marketing.")
    return {"email": u["email"], "nome": u["nome"], "tipo": "convite" if u["trocar_senha"] else "nova senha",
            "expira": u["convite_expira"]}


def usar_convite(db, token, nova):
    """O vendedor cria a senha pelo link: grava, apaga o link, desconecta os outros aparelhos e zera o bloqueio."""
    u = db.convite(token)
    if not u:
        raise GestaoErro("Este link expirou ou já foi usado. Peça um novo ao marketing.")
    problema = S.problema_nova_senha(nova, u["email"])
    if problema:
        raise GestaoErro(problema)
    db.definir_senha(u["id"], S.gerar_hash(nova), trocar_senha=False)
    db.apagar_convites(u["id"])
    db.encerrar_sessoes(u["id"])
    db.limpar_falhas_email(u["email"])
    db.registrar_evento(u["email"], "criou a senha pelo link", u["email"])
    return u


def redefinir(db, email, autor="terminal"):
    """Nova senha inicial (esqueceu a senha): desconecta os aparelhos, zera o bloqueio e obriga a trocar no próximo acesso."""
    u = _usuario(db, email)
    senha = S.senha_inicial()
    db.definir_senha(u["id"], S.gerar_hash(senha), trocar_senha=True)
    db.encerrar_sessoes(u["id"])
    db.limpar_falhas_email(u["email"])
    db.registrar_evento(autor, "gerou nova senha para", u["email"])
    return senha


def desativar(db, email, autor="terminal"):
    u = _usuario(db, email)
    if B.normalizar_email(autor) == u["email"]:
        raise GestaoErro("Você não pode desativar a sua própria conta.")
    db.definir_ativo(u["id"], False)
    db.registrar_evento(autor, "desativou", u["email"])


def reativar(db, email, autor="terminal", convite=False):
    """Volta a valer com senha nova (a antiga pode ter ficado com quem saiu). convite=True devolve o código do link."""
    u = _usuario(db, email)
    senha = S.senha_inicial()
    db.definir_senha(u["id"], S.gerar_hash(senha), trocar_senha=True)
    db.definir_ativo(u["id"], True)
    db.limpar_falhas_email(u["email"])
    db.registrar_evento(autor, "reativou", u["email"])
    if convite:
        return convidar(db, email, autor)[0]
    return senha


def desbloquear(db, email, autor="terminal"):
    u = _usuario(db, email)
    db.limpar_falhas_email(u["email"])
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
        espera = db.espera("email:" + u["email"], B.INICIO_EMAIL)
        out.append({"email": u["email"], "nome": u["nome"], "ativo": bool(u["ativo"]), "admin": bool(u["admin"]),
                    "trocar_senha": bool(u["trocar_senha"]), "ultimo_login": u["ultimo_login"], "criado": u["criado"],
                    "bloqueado": espera > 0, "convite_expira": db.convite_pendente(u["id"])})
    return out


def historico(db, limite=50):
    return [{"quando": e["quando"], "autor": e["autor"], "acao": e["acao"], "alvo": e["alvo"]} for e in db.eventos(limite)]
