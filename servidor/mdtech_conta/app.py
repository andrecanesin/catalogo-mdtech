"""App WSGI do login dos vendedores (só biblioteca padrão).

Hoje roda por CGI (public_html/conta.py); depois pode ir para mod_wsgi ou proxy sem reescrever: basta servir `criar_app(...)`.
Endereços (PATH_INFO, porque o servidor não tem mod_rewrite):
  GET  /conta.py/eu             quem está conectado          200 | 401
  POST /conta.py/entrar         {email, senha}               200 {trocar_senha} | 401 | 429
  POST /conta.py/trocar-senha   {senha_atual, nova}          200 | 400 | 401
  POST /conta.py/sair                                        200
  GET  /conta.py/precos         preços reais (só com sessão) 200 | 401 | 403 (falta trocar a senha inicial)
  Gestão dos vendedores (só administrador, já com a senha própria; ver gestao.py):
  GET  /conta.py/admin/vendedores · GET /conta.py/admin/historico
  POST /conta.py/admin/{adicionar, convite, desativar, reativar, desbloquear, admin, nome}   {email, ...}
  Link de convite / nova senha (entrar.html#convite=CÓDIGO; o código vai depois do # e não chega aos logs nem à pré-visualização):
  POST /conta.py/convite/ver {convite} · POST /conta.py/convite/usar {convite, nova}  -> entra direto
Todo POST exige corpo JSON (application/json): um formulário de outro site não consegue enviar isso sem permissão (CSRF).
"""
import json
import os
from http.cookies import SimpleCookie
from pathlib import Path

from . import banco as B
from . import gestao as G
from . import senhas as S

COOKIE = "mdtech_sessao"
MARCA = "mdtech_vendedor"     # sem segredo, legível pelo JS: só diz ao site "consulte /precos" (clientes nunca acionam o CGI)
_STATUS = {200: "200 OK", 400: "400 Bad Request", 401: "401 Unauthorized", 403: "403 Forbidden",
           404: "404 Not Found", 405: "405 Method Not Allowed", 413: "413 Payload Too Large",
           415: "415 Unsupported Media Type", 429: "429 Too Many Requests", 500: "500 Internal Server Error"}


# operações da tela: "convite" serve para o 1º acesso e para "esqueci a senha" (link de uso único, 7 dias)
_OPERACOES = {"adicionar": None, "convite": None, "desativar": G.desativar, "reativar": None,
              "desbloquear": G.desbloquear, "admin": None, "nome": None}


class Resposta:
    def __init__(self, codigo, corpo, cookies=()):
        self.codigo, self.corpo, self.cookies = codigo, corpo, list(cookies)


def _cookies_sessao(token, seguro, apagar=False):
    def um(nome, valor, http_only):
        partes = [f"{nome}={'' if apagar else valor}", "Path=/", "SameSite=Lax"]
        partes.append("Max-Age=0" if apagar else f"Max-Age={B.SESSAO_DIAS * 86400}")
        if http_only:
            partes.append("HttpOnly")
        if seguro:
            partes.append("Secure")
        return "; ".join(partes)
    return [um(COOKIE, token, True), um(MARCA, "1", False)]


def _minutos(segundos):
    if segundos < 60:
        return f"{max(1, segundos)} segundos"
    m = max(1, (segundos + 59) // 60)
    return f"{m} minuto{'s' if m > 1 else ''}"


def criar_app(caminho_banco, caminho_precos, cookie_seguro=True):
    caminho_precos = Path(caminho_precos)

    def app(environ, start_response):
        try:
            r = _rotear(environ)
        except Exception:                       # nunca mostrar detalhes do erro ao navegador
            import traceback
            traceback.print_exc(file=environ.get("wsgi.errors"))
            r = Resposta(500, {"erro": "Erro no servidor. Tente de novo em instantes."})
        corpo = json.dumps(r.corpo, ensure_ascii=False).encode("utf-8")
        cab = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(corpo))),
               ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
               ("Referrer-Policy", "same-origin"), ("X-Frame-Options", "DENY")]
        cab += [("Set-Cookie", c) for c in r.cookies]
        start_response(_STATUS.get(r.codigo, f"{r.codigo} Erro"), cab)
        return [corpo]

    def _token(environ):
        c = SimpleCookie()
        try:
            c.load(environ.get("HTTP_COOKIE", ""))
        except Exception:
            return None
        return c[COOKIE].value if COOKIE in c else None

    def _ler_json(environ):
        tipo = environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower()
        if tipo != "application/json":
            return Resposta(415, {"erro": "Envio inválido."})
        origem = environ.get("HTTP_ORIGIN")
        host = environ.get("HTTP_HOST", "")
        if origem and origem.split("://", 1)[-1] != host:
            return Resposta(403, {"erro": "Origem não permitida."})
        try:
            tam = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            tam = 0
        if tam > 10_000:
            return Resposta(413, {"erro": "Envio grande demais."})
        try:
            dados = json.loads(environ["wsgi.input"].read(tam) or b"{}")
        except (ValueError, UnicodeDecodeError):
            return Resposta(400, {"erro": "Envio inválido."})
        return dados if isinstance(dados, dict) else Resposta(400, {"erro": "Envio inválido."})

    def _rotear(environ):
        metodo = environ.get("REQUEST_METHOD", "GET")
        rota = environ.get("PATH_INFO", "").rstrip("/") or "/"
        rotas = {"/eu": ("GET", _eu), "/precos": ("GET", _precos), "/entrar": ("POST", _entrar),
                 "/trocar-senha": ("POST", _trocar), "/sair": ("POST", _sair),
                 "/admin/vendedores": ("GET", _adm_lista), "/admin/historico": ("GET", _adm_historico)}
        rotas.update({"/admin/" + op: ("POST", _adm_op) for op in _OPERACOES})
        rotas.update({"/convite/ver": ("POST", _convite_ver), "/convite/usar": ("POST", _convite_usar)})
        if rota not in rotas:
            return Resposta(404, {"erro": "Endereço não encontrado."})
        esperado, func = rotas[rota]
        if metodo != esperado:
            return Resposta(405, {"erro": "Método não permitido."})
        dados = None
        if metodo == "POST":
            dados = _ler_json(environ)
            if isinstance(dados, Resposta):
                return dados
        db = B.Banco(caminho_banco)
        try:
            return func(db, environ, dados)
        finally:
            db.fechar()

    # ---------- rotas ----------
    def _eu(db, environ, _):
        u = db.sessao(_token(environ))
        if not u:
            return Resposta(401, {"erro": "Não conectado."})
        return Resposta(200, {"email": u["email"], "nome": u["nome"], "trocar_senha": bool(u["trocar_senha"]),
                              "admin": bool(u["admin"])})

    def _entrar(db, environ, dados):
        email = B.normalizar_email(str(dados.get("email", "")))[:200]
        senha = str(dados.get("senha", ""))[:200]
        if not email or not senha:
            return Resposta(400, {"erro": "Informe o e-mail e a senha."})
        ip = environ.get("REMOTE_ADDR", "?")
        k_email, k_ip, k_par = "email:" + email, "ip:" + ip, f"par:{email}|{ip}"
        n, falta = db.falhas(k_ip)
        if n >= B.MAX_POR_IP:
            return Resposta(429, {"erro": f"Muitas tentativas erradas. Tente de novo em {_minutos(falta)}."})
        # atraso progressivo: pesa mais no IP que errou do que no e-mail, para ninguém travar o vendedor de fora
        falta = max(db.espera(k_par, B.INICIO_PAR), db.espera(k_email, B.INICIO_EMAIL))
        if falta:
            return Resposta(429, {"erro": f"Muitas tentativas erradas. Tente de novo em {_minutos(falta)}."})
        u = db.usuario(email)
        ok = S.conferir(senha, u["hash"]) if u else S.conferir_falso(senha)
        if not ok or not u["ativo"]:
            db.registrar_falha(k_email, k_ip, k_par)
            msg = "E-mail ou senha incorretos."
            falta = db.espera(k_par, B.INICIO_PAR)
            if falta:
                msg += f" Aguarde {_minutos(falta)} antes de tentar de novo."
            return Resposta(401, {"erro": msg})
        db.limpar_falhas(k_par)
        db.marcar_login(u["id"])
        token = db.criar_sessao(u["id"])
        return Resposta(200, {"email": u["email"], "nome": u["nome"], "trocar_senha": bool(u["trocar_senha"])},
                        _cookies_sessao(token, cookie_seguro))

    def _trocar(db, environ, dados):
        token = _token(environ)
        u = db.sessao(token)
        if not u:
            return Resposta(401, {"erro": "Sua sessão expirou. Entre de novo."})
        atual = str(dados.get("senha_atual", ""))[:200]
        nova = str(dados.get("nova", ""))[:201]
        k_email, k_par = "email:" + u["email"], f"par:{u['email']}|{environ.get('REMOTE_ADDR', '?')}"
        falta = max(db.espera(k_par, B.INICIO_PAR), db.espera(k_email, B.INICIO_EMAIL))
        if falta:
            return Resposta(429, {"erro": f"Muitas tentativas erradas. Tente de novo em {_minutos(falta)}."})
        if not S.conferir(atual, u["hash"]):
            db.registrar_falha(k_email, k_par)
            return Resposta(400, {"erro": "A senha atual não confere."})
        problema = S.problema_nova_senha(nova, u["email"], atual)
        if problema:
            return Resposta(400, {"erro": problema})
        db.definir_senha(u["id"], S.gerar_hash(nova), trocar_senha=False)
        db.encerrar_sessoes(u["id"], exceto_token=token)     # sai dos outros aparelhos
        return Resposta(200, {"ok": True})

    def _sair(db, environ, _):
        db.encerrar_sessao(_token(environ))
        return Resposta(200, {"ok": True}, _cookies_sessao("", cookie_seguro, apagar=True))

    def _precos(db, environ, _):
        u = db.sessao(_token(environ))
        if not u:
            return Resposta(401, {"erro": "Não conectado."})
        if u["trocar_senha"]:
            return Resposta(403, {"erro": "Troque a senha inicial para ver os preços."})
        try:
            dados = json.loads(caminho_precos.read_text(encoding="utf-8"))
        except FileNotFoundError:
            dados = {"precos": {}, "atualizado": None}
        return Resposta(200, {**dados, "email": u["email"], "admin": bool(u["admin"])})

    # ---------- link de convite / nova senha ----------
    def _limite_convite(db, environ):
        n, falta = db.falhas("ip:" + environ.get("REMOTE_ADDR", "?"))
        if n >= B.MAX_POR_IP:
            return Resposta(429, {"erro": f"Muitas tentativas. Tente de novo em {_minutos(falta)}."})
        return None

    def _convite_ver(db, environ, dados):
        bloq = _limite_convite(db, environ)
        if bloq:
            return bloq
        try:
            return Resposta(200, G.ver_convite(db, str(dados.get("convite", ""))[:100]))
        except G.GestaoErro as e:
            db.registrar_falha("ip:" + environ.get("REMOTE_ADDR", "?"))
            return Resposta(400, {"erro": str(e)})

    def _convite_usar(db, environ, dados):
        bloq = _limite_convite(db, environ)
        if bloq:
            return bloq
        token = str(dados.get("convite", ""))[:100]
        if not db.convite(token):
            db.registrar_falha("ip:" + environ.get("REMOTE_ADDR", "?"))
        try:
            u = G.usar_convite(db, token, str(dados.get("nova", ""))[:201])
        except G.GestaoErro as e:
            return Resposta(400, {"erro": str(e)})
        db.marcar_login(u["id"])
        sessao = db.criar_sessao(u["id"])
        return Resposta(200, {"email": u["email"], "nome": u["nome"], "trocar_senha": False, "admin": bool(u["admin"])},
                        _cookies_sessao(sessao, cookie_seguro))

    # ---------- gestão dos vendedores (tela vendedores.html) ----------
    def _admin(db, environ):
        u = db.sessao(_token(environ))
        if not u:
            return Resposta(401, {"erro": "Sua sessão expirou. Entre de novo."})
        if not u["admin"]:
            return Resposta(403, {"erro": "Só administradores acessam a gestão dos vendedores."})
        if u["trocar_senha"]:
            return Resposta(403, {"erro": "Troque a senha inicial antes de gerenciar os vendedores."})
        return u

    def _adm_lista(db, environ, _):
        u = _admin(db, environ)
        if isinstance(u, Resposta):
            return u
        return Resposta(200, {"vendedores": G.listar(db), "eu": u["email"]})

    def _adm_historico(db, environ, _):
        u = _admin(db, environ)
        if isinstance(u, Resposta):
            return u
        return Resposta(200, {"historico": G.historico(db)})

    def _adm_op(db, environ, dados):
        u = _admin(db, environ)
        if isinstance(u, Resposta):
            return u
        op = environ.get("PATH_INFO", "").rstrip("/").rsplit("/", 1)[-1]
        email = str(dados.get("email", ""))[:200]
        autor = u["email"]
        try:
            convite = None
            if op == "adicionar":
                convite = G.adicionar(db, email, str(dados.get("nome", "")), autor, convite=True); senha = None
            elif op == "convite":
                convite = G.convidar(db, email, autor)[0]; senha = None
            elif op == "reativar":
                convite = G.reativar(db, email, autor, convite=True); senha = None
            elif op == "admin":
                G.definir_admin(db, email, bool(dados.get("admin")), autor); senha = None
            elif op == "nome":
                G.definir_nome(db, email, str(dados.get("nome", "")), autor); senha = None
            else:
                senha = _OPERACOES[op](db, email, autor=autor)
        except G.GestaoErro as e:
            return Resposta(400, {"erro": str(e)})
        corpo = {"ok": True, "email": B.normalizar_email(email)}
        if convite:
            corpo["convite"] = convite        # vira o link entrar.html#convite=...; no banco só existe o hash
            corpo["validade_dias"] = B.CONVITE_DIAS
        if senha:
            corpo["senha"] = senha            # mostrada UMA vez na tela; no banco só existe o hash
        return Resposta(200, corpo)

    return app


DADOS_SERVIDOR = Path("/var/lib/mdtech")


def app_do_servidor(home=None):
    """Caminhos no servidor: dados em /var/lib/mdtech (fora da pasta pública). Não pode ser em /home: o serviço do Apache
    roda com ProtectHome=read-only (o CGI lê /home, mas não grava). A pasta é www-data:catalogo_mdtech, modo 2770."""
    dados = Path(os.environ.get("MDTECH_DADOS") or DADOS_SERVIDOR)
    return criar_app(dados / "usuarios.sqlite", dados / "precos.json",
                     cookie_seguro=os.environ.get("MDTECH_COOKIE_INSEGURO") != "1")
