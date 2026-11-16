#!/usr/bin/python3
# Porta de entrada CGI do login dos vendedores. Vai para public_html/conta.py (chmod 755).
# O código fica em ~/mdtech_app e os dados em /var/lib/mdtech, FORA da pasta pública.
# Quando o servidor tiver mod_wsgi ou proxy, este arquivo deixa de existir: serve-se mdtech_conta.app.app_do_servidor(HOME).
import sys
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent          # public_html/.. = pasta do usuário
sys.path.insert(0, str(HOME / "mdtech_app"))

from wsgiref.handlers import CGIHandler                 # noqa: E402
from mdtech_conta.app import app_do_servidor            # noqa: E402

CGIHandler().run(app_do_servidor(HOME))
