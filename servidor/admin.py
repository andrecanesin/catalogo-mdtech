#!/usr/bin/python3
"""Cadastro dos vendedores (roda NO SERVIDOR, por SSH). A senha inicial aparece uma única vez: envie ao vendedor.
No 1º acesso o site obriga a trocar por uma senha dele.

  python3 ~/mdtech_app/admin.py adicionar email@empresa.com.br [email2 ...]   cria e mostra a senha inicial
  python3 ~/mdtech_app/admin.py redefinir email@empresa.com.br                nova senha inicial (esqueceu a senha)
  python3 ~/mdtech_app/admin.py desativar email@empresa.com.br                saiu da empresa: bloqueia e desconecta
  python3 ~/mdtech_app/admin.py reativar email@empresa.com.br                 volta a valer (com senha nova)
  python3 ~/mdtech_app/admin.py desbloquear email@empresa.com.br              zera as tentativas erradas
  python3 ~/mdtech_app/admin.py listar
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mdtech_conta import banco as B, senhas as S      # noqa: E402

EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main(argv, caminho=None):
    if len(argv) < 1 or argv[0] not in {"adicionar", "redefinir", "desativar", "reativar", "desbloquear", "listar"}:
        print(__doc__)
        return 1
    cmd, emails = argv[0], [B.normalizar_email(e) for e in argv[1:]]
    if cmd != "listar" and not emails:
        print("Informe o e-mail."); return 1
    db = B.Banco(caminho or Path("/var/lib/mdtech") / "usuarios.sqlite")
    erro = 0
    try:
        if cmd == "listar":
            for u in db.listar():
                ult = time.strftime("%d/%m/%Y %H:%M", time.localtime(u["ultimo_login"])) if u["ultimo_login"] else "nunca entrou"
                est = "ATIVO" if u["ativo"] else "desativado"
                pend = " · falta trocar a senha inicial" if u["trocar_senha"] else ""
                print(f"{u['email']:<40} {est:<11} último acesso: {ult}{pend}")
            return 0
        for email in emails:
            u = db.usuario(email)
            if cmd == "adicionar":
                if not EMAIL_OK.match(email):
                    print(f"{email}: e-mail inválido"); erro = 1; continue
                if u:
                    print(f"{email}: já existe (use 'redefinir' para nova senha)"); erro = 1; continue
                senha = S.senha_inicial()
                db.criar_usuario(email, S.gerar_hash(senha))
                print(f"{email}\tsenha inicial: {senha}")
            elif not u:
                print(f"{email}: não cadastrado"); erro = 1
            elif cmd in ("redefinir", "reativar"):
                senha = S.senha_inicial()
                db.definir_senha(u["id"], S.gerar_hash(senha), trocar_senha=True)
                db.encerrar_sessoes(u["id"])
                db.definir_ativo(u["id"], True)
                db.limpar_falhas("email:" + email)
                print(f"{email}\tnova senha inicial: {senha}")
            elif cmd == "desativar":
                db.definir_ativo(u["id"], False)
                print(f"{email}: desativado e desconectado de todos os aparelhos")
            elif cmd == "desbloquear":
                db.limpar_falhas("email:" + email)
                print(f"{email}: tentativas zeradas")
    finally:
        db.fechar()
    return erro


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
