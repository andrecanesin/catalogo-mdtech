#!/usr/bin/env python3
"""Teste local do login (sem Apache): serve site/ e o app em /conta.py, como no servidor.
  python servidor/dev.py                         http://127.0.0.1:8900/entrar.html
  python servidor/admin.py ... não serve aqui: use  python servidor/dev.py adicionar email@x.com
Os dados ficam em saida/dev_conta/ (fora do git). O cookie sai sem 'Secure' só aqui (http local)."""
import mimetypes
import os
import sys
from pathlib import Path
from wsgiref.simple_server import make_server

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "servidor"))
from mdtech_conta.app import criar_app   # noqa: E402

DADOS = RAIZ / "saida" / "dev_conta"
SITE = RAIZ / "site"

if len(sys.argv) > 1:                      # atalho para o admin com o banco local
    import admin
    sys.exit(admin.main(sys.argv[1:], DADOS / "usuarios.sqlite"))

conta = criar_app(DADOS / "usuarios.sqlite", DADOS / "precos.json", cookie_seguro=False)


def app(environ, start_response):
    caminho = environ.get("PATH_INFO", "/")
    if caminho == "/conta.py" or caminho.startswith("/conta.py/"):
        environ["PATH_INFO"] = caminho[len("/conta.py"):]
        return conta(environ, start_response)
    arq = (SITE / caminho.lstrip("/")).resolve()
    if arq.is_dir():
        arq = arq / "index.html"
    if SITE.resolve() not in arq.parents or not arq.is_file():
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"404"]
    start_response("200 OK", [("Content-Type", mimetypes.guess_type(arq.name)[0] or "application/octet-stream")])
    return [arq.read_bytes()]


if __name__ == "__main__":
    porta = int(os.environ.get("PORTA", 8900))
    print(f"http://127.0.0.1:{porta}/entrar.html  (Ctrl+C para parar)")
    make_server("127.0.0.1", porta, app).serve_forever()
