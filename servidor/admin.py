#!/usr/bin/python3
"""Gestão dos vendedores pelo terminal (roda NO SERVIDOR, por SSH). O dia a dia é pela tela "Vendedores" do site
(menu da conta, só para administradores); este script serve para o 1º administrador e para emergências.

  python3 ~/mdtech_app/admin.py adicionar email@empresa.com.br [email2 ...]   cria e mostra a senha inicial
  python3 ~/mdtech_app/admin.py convite email@empresa.com.br                  link (7 dias, uso único) para criar a senha
  python3 ~/mdtech_app/admin.py redefinir email@empresa.com.br                nova senha inicial (esqueceu a senha)
  python3 ~/mdtech_app/admin.py desativar email@empresa.com.br                saiu da empresa: bloqueia e desconecta
  python3 ~/mdtech_app/admin.py reativar email@empresa.com.br                 volta a valer (com senha nova)
  python3 ~/mdtech_app/admin.py desbloquear email@empresa.com.br              zera as tentativas erradas
  python3 ~/mdtech_app/admin.py tornar-admin email@empresa.com.br             dá acesso à tela "Vendedores"
  python3 ~/mdtech_app/admin.py listar
  python3 ~/mdtech_app/admin.py nomes < deploy/vendedores.txt                 preenche o nome de quem está sem nome
                                                                             (linhas "email Nome Sobrenome"; aceita ; , ou tab)
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mdtech_conta import banco as B, gestao as G      # noqa: E402

LINK = "https://catalogo.mdtechsm.com.br/entrar.html#convite="
COMANDOS = {"nomes", "convite", "adicionar", "redefinir", "desativar", "reativar", "desbloquear", "tornar-admin", "listar"}


def main(argv, caminho=None):
    if len(argv) < 1 or argv[0] not in COMANDOS:
        print(__doc__)
        return 1
    cmd, emails = argv[0], [B.normalizar_email(e) for e in argv[1:] if e.strip()]
    if cmd == "nomes":
        return nomes(sys.stdin.read(), caminho)
    if cmd != "listar" and not emails:
        print("Informe o e-mail."); return 1
    db = B.Banco(caminho or Path("/var/lib/mdtech") / "usuarios.sqlite")
    erro = 0
    try:
        if cmd == "listar":
            for u in G.listar(db):
                ult = time.strftime("%d/%m/%Y %H:%M", time.localtime(u["ultimo_login"])) if u["ultimo_login"] else "nunca entrou"
                est = "ATIVO" if u["ativo"] else "desativado"
                extra = (" · admin" if u["admin"] else "") + (" · falta trocar a senha inicial" if u["trocar_senha"] else "") \
                    + (" · BLOQUEADO" if u["bloqueado"] else "")
                print(f"{u['email']:<40} {est:<11} último acesso: {ult}{extra}")
            return 0
        for email in emails:
            try:
                if cmd == "adicionar":
                    print(f"{email}\tsenha inicial: {G.adicionar(db, email)}")
                elif cmd == "convite":
                    print(f"{email}\t{LINK}{G.convidar(db, email)[0]}")
                elif cmd == "redefinir":
                    print(f"{email}\tnova senha inicial: {G.redefinir(db, email)}")
                elif cmd == "reativar":
                    print(f"{email}\tnova senha inicial: {G.reativar(db, email)}")
                elif cmd == "desativar":
                    G.desativar(db, email); print(f"{email}: desativado e desconectado de todos os aparelhos")
                elif cmd == "desbloquear":
                    G.desbloquear(db, email); print(f"{email}: tentativas zeradas")
                elif cmd == "tornar-admin":
                    G.definir_admin(db, email, True); print(f"{email}: agora é administrador (tela Vendedores)")
            except G.GestaoErro as e:
                print(f"{email}: {e}"); erro = 1
    finally:
        db.fechar()
    return erro


def ler_nomes(texto):
    """'email Nome Sobrenome' (ou separado por ; , tab), uma pessoa por linha; # comenta. Devolve {email: nome}."""
    out = {}
    for linha in texto.splitlines():
        linha = linha.strip().lstrip("\ufeff")
        if not linha or linha.startswith("#"):
            continue
        partes = [p for p in re.split(r"[\s;,]+", linha) if p]
        email = next((p for p in partes if "@" in p), None)
        if not email:
            continue
        nome = " ".join(p for p in partes if p != email).strip(" \"'-")
        if nome:
            out[B.normalizar_email(email)] = nome[:100]
    return out


def nomes(texto, caminho=None):
    db = B.Banco(caminho or Path("/var/lib/mdtech") / "usuarios.sqlite")
    try:
        lidos = ler_nomes(texto)
        for email, nome in lidos.items():
            u = db.usuario(email)
            if not u:
                print(f"{email}: não cadastrado (ignorado)")
            elif u["nome"]:
                print(f"{email}: já tem nome ({u['nome']}), mantido")
            else:
                G.definir_nome(db, email, nome)
                print(f"{email}: {nome}")
        if not lidos:
            print("Nenhum nome encontrado (formato: e-mail e nome na mesma linha).")
    finally:
        db.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
