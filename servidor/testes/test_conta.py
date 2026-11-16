"""Testes do login dos vendedores. Rodar: python -m unittest discover -s servidor/testes"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from mdtech_conta import app as A, banco as B, senhas as S   # noqa: E402
import admin                                                 # noqa: E402


class Cliente:
    def __init__(self, app):
        self.app, self.cookie = app, None

    def req(self, metodo, rota, corpo=None, tipo="application/json", origem=None, ip="1.2.3.4"):
        dados = json.dumps(corpo).encode() if corpo is not None else b""
        env = {"REQUEST_METHOD": metodo, "PATH_INFO": rota, "CONTENT_TYPE": tipo, "CONTENT_LENGTH": str(len(dados)),
               "wsgi.input": io.BytesIO(dados), "wsgi.errors": io.StringIO(), "HTTP_HOST": "catalogo.exemplo",
               "REMOTE_ADDR": ip}
        if origem:
            env["HTTP_ORIGIN"] = origem
        if self.cookie:
            env["HTTP_COOKIE"] = f"{A.COOKIE}={self.cookie}"
        res = {}
        def sr(status, cab):
            res["status"], res["cab"] = int(status.split()[0]), cab
        corpo_r = b"".join(self.app(env, sr))
        for k, v in res["cab"]:
            if k == "Set-Cookie" and v.startswith(A.COOKIE + "="):
                val = v.split(";")[0].split("=", 1)[1]
                self.cookie = val or None
        return res["status"], json.loads(corpo_r), dict((k, v) for k, v in res["cab"] if k != "Set-Cookie"), res["cab"]


class TesteConta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.banco, self.precos = d / "dados" / "usuarios.sqlite", d / "dados" / "precos.json"
        self.app = A.criar_app(self.banco, self.precos)
        self.c = Cliente(self.app)
        out = io.StringIO()
        sys.stdout, velho = out, sys.stdout
        try:
            admin.main(["adicionar", "Vendedor@MDTech.com.br"], self.banco)
        finally:
            sys.stdout = velho
        self.senha0 = out.getvalue().split("senha inicial: ")[1].strip()

    def tearDown(self):
        self.tmp.cleanup()

    def entrar(self, senha=None, email="vendedor@mdtech.com.br", **kw):
        return self.c.req("POST", "/entrar", {"email": email, "senha": senha or self.senha0}, **kw)

    def test_fluxo_completo(self):
        self.assertEqual(self.c.req("GET", "/eu")[0], 401)
        self.assertEqual(self.c.req("GET", "/precos")[0], 401)
        st, corpo, cab, brutos = self.entrar()
        self.assertEqual(st, 200)
        self.assertTrue(corpo["trocar_senha"])
        ck = [v for k, v in brutos if k == "Set-Cookie" and v.startswith(A.COOKIE)][0]
        for attr in ("HttpOnly", "Secure", "SameSite=Lax", "Path=/"):
            self.assertIn(attr, ck)
        marca = [v for k, v in brutos if k == "Set-Cookie" and v.startswith(A.MARCA)][0]
        self.assertNotIn("HttpOnly", marca)
        self.assertNotIn(ck.split(";")[0].split("=")[1], marca)
        self.assertEqual(cab["Cache-Control"], "no-store")
        # antes de trocar a senha inicial, sem preço
        self.assertEqual(self.c.req("GET", "/precos")[0], 403)
        self.assertEqual(self.c.req("POST", "/trocar-senha", {"senha_atual": self.senha0, "nova": "curta"})[0], 400)
        self.assertEqual(self.c.req("POST", "/trocar-senha", {"senha_atual": "errada", "nova": "umaSenhaBoa123"})[0], 400)
        st, corpo, *_ = self.c.req("POST", "/trocar-senha", {"senha_atual": self.senha0, "nova": "umaSenhaBoa123"})
        self.assertEqual(st, 200, corpo)
        self.assertFalse(self.c.req("GET", "/eu")[1]["trocar_senha"])
        st, corpo, *_ = self.c.req("GET", "/precos")
        self.assertEqual((st, corpo["precos"]), (200, {}))
        self.precos.write_text(json.dumps({"precos": {"A153": 123.45}, "atualizado": "2026-11-16"}))
        self.assertEqual(self.c.req("GET", "/precos")[1]["precos"]["A153"], 123.45)
        # sair
        self.assertEqual(self.c.req("POST", "/sair", {})[0], 200)
        self.assertIsNone(self.c.cookie)
        self.assertEqual(self.c.req("GET", "/precos")[0], 401)
        # senha antiga não vale; nova vale
        self.assertEqual(self.entrar()[0], 401)
        self.assertEqual(self.entrar("umaSenhaBoa123")[0], 200)

    def test_cookie_falso_e_email_inexistente(self):
        self.c.cookie = "inventado"
        self.assertEqual(self.c.req("GET", "/eu")[0], 401)
        st, corpo, *_ = self.entrar(email="ninguem@x.com")
        self.assertEqual(st, 401)
        self.assertEqual(corpo["erro"], "E-mail ou senha incorretos.")

    def test_bloqueio_por_tentativas(self):
        for _ in range(B.MAX_POR_EMAIL):
            self.assertEqual(self.entrar("errada123")[0], 401)
        st, corpo, *_ = self.entrar()                  # até a senha certa fica bloqueada
        self.assertEqual(st, 429)
        self.assertIn("15 minutos", corpo["erro"])
        out = io.StringIO(); sys.stdout, velho = out, sys.stdout
        try:
            admin.main(["desbloquear", "vendedor@mdtech.com.br"], self.banco)
        finally:
            sys.stdout = velho
        self.assertEqual(self.entrar()[0], 200)

    def test_bloqueio_por_ip(self):
        for i in range(B.MAX_POR_IP):
            self.entrar("x", email=f"n{i}@x.com")
        self.assertEqual(self.entrar()[0], 429)
        self.assertEqual(self.entrar(ip="5.6.7.8")[0], 200)

    def test_csrf_e_metodos(self):
        self.assertEqual(self.c.req("POST", "/entrar", {"email": "a", "senha": "b"}, tipo="application/x-www-form-urlencoded")[0], 415)
        self.assertEqual(self.entrar(origem="https://site-malicioso.com")[0], 403)
        self.assertEqual(self.entrar(origem="https://catalogo.exemplo")[0], 200)
        self.assertEqual(self.c.req("GET", "/entrar")[0], 405)
        self.assertEqual(self.c.req("GET", "/nada")[0], 404)

    def test_redefinir_desconecta_e_desativar(self):
        self.assertEqual(self.entrar()[0], 200)
        out = io.StringIO(); sys.stdout, velho = out, sys.stdout
        try:
            admin.main(["redefinir", "vendedor@mdtech.com.br"], self.banco)
            nova = out.getvalue().split("nova senha inicial: ")[1].strip()
            self.assertEqual(self.c.req("GET", "/eu")[0], 401)       # sessão antiga caiu
            self.assertEqual(self.entrar(nova)[1]["trocar_senha"], True)
            admin.main(["desativar", "vendedor@mdtech.com.br"], self.banco)
        finally:
            sys.stdout = velho
        self.assertEqual(self.c.req("GET", "/eu")[0], 401)
        self.assertEqual(self.entrar(nova)[0], 401)

    def test_troca_desconecta_outros_aparelhos(self):
        outro = Cliente(self.app)
        self.entrar()
        outro.req("POST", "/entrar", {"email": "vendedor@mdtech.com.br", "senha": self.senha0})
        self.c.req("POST", "/trocar-senha", {"senha_atual": self.senha0, "nova": "umaSenhaBoa123"})
        self.assertEqual(self.c.req("GET", "/eu")[0], 200)
        self.assertEqual(outro.req("GET", "/eu")[0], 401)

    def test_hash(self):
        h = S.gerar_hash("abc")
        self.assertTrue(h.startswith("scrypt$"))
        self.assertTrue(S.conferir("abc", h))
        self.assertFalse(S.conferir("abd", h))
        self.assertFalse(S.conferir("abc", "lixo"))
        self.assertIsNotNone(S.problema_nova_senha("aaaaaaaaaaaa"))
        self.assertIsNotNone(S.problema_nova_senha("vendedor2026!", "vendedor@x.com"))
        self.assertIsNone(S.problema_nova_senha("cirurgia-laparo-26"))

    def _admin_pronto(self):
        """Entra como vendedor@ (já com senha própria) e vira administrador pelo terminal."""
        self.entrar()
        self.c.req("POST", "/trocar-senha", {"senha_atual": self.senha0, "nova": "umaSenhaBoa123"})
        out = io.StringIO(); sys.stdout, velho = out, sys.stdout
        try:
            admin.main(["tornar-admin", "vendedor@mdtech.com.br"], self.banco)
        finally:
            sys.stdout = velho

    def test_gestao_so_admin(self):
        self.assertEqual(self.c.req("GET", "/admin/vendedores")[0], 401)
        self.entrar()
        self.assertEqual(self.c.req("GET", "/admin/vendedores")[0], 403)      # não é admin
        self.assertEqual(self.c.req("POST", "/admin/adicionar", {"email": "x@y.com"})[0], 403)
        out = io.StringIO(); sys.stdout, velho = out, sys.stdout
        try:
            admin.main(["tornar-admin", "vendedor@mdtech.com.br"], self.banco)
        finally:
            sys.stdout = velho
        self.assertEqual(self.c.req("GET", "/admin/vendedores")[0], 403)      # admin, mas falta trocar a senha inicial
        self.c.req("POST", "/trocar-senha", {"senha_atual": self.senha0, "nova": "umaSenhaBoa123"})
        st, corpo, *_ = self.c.req("GET", "/admin/vendedores")
        self.assertEqual(st, 200)
        self.assertTrue(corpo["vendedores"][0]["admin"])
        self.assertTrue(self.c.req("GET", "/eu")[1]["admin"])

    def test_gestao_fluxo(self):
        self._admin_pronto()
        st, corpo, *_ = self.c.req("POST", "/admin/adicionar", {"email": " Novo@MDTech.com.br ", "nome": "Novo"})
        self.assertEqual(st, 200, corpo)
        self.assertNotIn("senha", corpo)                      # a tela não mostra mais senha: só o link
        conv = corpo["convite"]
        self.assertEqual(corpo["validade_dias"], 7)
        self.assertEqual(self.c.req("POST", "/admin/adicionar", {"email": "novo@mdtech.com.br"})[0], 400)   # repetido
        self.assertEqual(self.c.req("POST", "/admin/adicionar", {"email": "sem-arroba"})[0], 400)
        # o vendedor abre o link: vê o e-mail; cria a senha e já entra
        novo = Cliente(self.app)
        st, d, *_ = novo.req("POST", "/convite/ver", {"convite": conv})
        self.assertEqual((st, d["email"], d["tipo"]), (200, "novo@mdtech.com.br", "convite"))
        self.assertEqual(novo.req("POST", "/convite/usar", {"convite": conv, "nova": "curta"})[0], 400)   # regra da senha
        st, d, *_ = novo.req("POST", "/convite/usar", {"convite": conv, "nova": "cirurgia-laparo-26"})
        self.assertEqual(st, 200, d)
        self.assertEqual(novo.req("GET", "/precos")[0], 200)        # já entrou, sem trocar senha de novo
        self.assertEqual(novo.req("POST", "/convite/usar", {"convite": conv, "nova": "outra-senha-boa"})[0], 400)  # uso único
        # esqueci a senha: link novo; a senha atual vale até o link ser usado; ao usar, os aparelhos saem
        conv2 = self.c.req("POST", "/admin/convite", {"email": "novo@mdtech.com.br"})[1]["convite"]
        self.assertEqual(Cliente(self.app).req("POST", "/convite/ver", {"convite": conv2})[1]["tipo"], "nova senha")
        self.assertEqual(novo.req("GET", "/eu")[0], 200)
        conv3 = self.c.req("POST", "/admin/convite", {"email": "novo@mdtech.com.br"})[1]["convite"]
        self.assertEqual(Cliente(self.app).req("POST", "/convite/ver", {"convite": conv2})[0], 400)       # o novo cancela o anterior
        outro = Cliente(self.app)
        self.assertEqual(outro.req("POST", "/convite/usar", {"convite": conv3, "nova": "nova-senha-2026"})[0], 200)
        self.assertEqual(novo.req("GET", "/eu")[0], 401)
        self.assertEqual(outro.req("POST", "/entrar", {"email": "novo@mdtech.com.br", "senha": "nova-senha-2026"})[0], 200)
        # desativar apaga o link; reativar devolve um link novo
        conv4 = self.c.req("POST", "/admin/convite", {"email": "novo@mdtech.com.br"})[1]["convite"]
        self.assertEqual(self.c.req("POST", "/admin/desativar", {"email": "novo@mdtech.com.br"})[0], 200)
        self.assertEqual(outro.req("GET", "/eu")[0], 401)
        self.assertEqual(Cliente(self.app).req("POST", "/convite/ver", {"convite": conv4})[0], 400)
        self.assertEqual(self.c.req("POST", "/admin/convite", {"email": "novo@mdtech.com.br"})[0], 400)  # desativado
        conv5 = self.c.req("POST", "/admin/reativar", {"email": "novo@mdtech.com.br"})[1]["convite"]
        self.assertEqual(outro.req("POST", "/convite/usar", {"convite": conv5, "nova": "volta-pra-casa-26"})[0], 200)
        # bloqueio aparece na lista e o desbloqueio funciona
        for _ in range(B.MAX_POR_EMAIL):
            Cliente(self.app).req("POST", "/entrar", {"email": "novo@mdtech.com.br", "senha": "errada"}, ip="9.9.9.9")
        lista = {v["email"]: v for v in self.c.req("GET", "/admin/vendedores")[1]["vendedores"]}
        self.assertTrue(lista["novo@mdtech.com.br"]["bloqueado"])
        self.c.req("POST", "/admin/desbloquear", {"email": "novo@mdtech.com.br"})
        self.assertEqual(outro.req("POST", "/entrar", {"email": "novo@mdtech.com.br", "senha": "volta-pra-casa-26"})[0], 200)
        # admin: dar e tirar; não pode se rebaixar nem se desativar
        self.assertEqual(self.c.req("POST", "/admin/admin", {"email": "novo@mdtech.com.br", "admin": True})[0], 200)
        self.assertEqual(self.c.req("POST", "/admin/admin", {"email": "vendedor@mdtech.com.br", "admin": False})[0], 400)
        self.assertEqual(self.c.req("POST", "/admin/desativar", {"email": "vendedor@mdtech.com.br"})[0], 400)
        self.assertEqual(self.c.req("POST", "/admin/nome", {"email": "novo@mdtech.com.br", "nome": "Fulano"})[0], 200)
        self.assertEqual(self.c.req("POST", "/admin/convite", {"email": "ninguem@x.com"})[0], 400)
        # histórico
        hist = self.c.req("GET", "/admin/historico")[1]["historico"]
        trio = [(h["autor"], h["acao"], h["alvo"]) for h in hist]
        self.assertIn(("vendedor@mdtech.com.br", "desativou", "novo@mdtech.com.br"), trio)
        self.assertIn(("vendedor@mdtech.com.br", "enviou link de nova senha para", "novo@mdtech.com.br"), trio)
        self.assertIn(("novo@mdtech.com.br", "criou a senha pelo link", "novo@mdtech.com.br"), trio)

    def test_convite_expirado_e_falso(self):
        self._admin_pronto()
        conv = self.c.req("POST", "/admin/adicionar", {"email": "x@mdtech.com.br"})[1]["convite"]
        db = B.Banco(self.banco)
        db.con.execute("UPDATE convites SET expira = 1")          # simula 7 dias depois
        db.fechar()
        self.assertEqual(Cliente(self.app).req("POST", "/convite/ver", {"convite": conv})[0], 400)
        self.assertEqual(Cliente(self.app).req("POST", "/convite/usar", {"convite": conv, "nova": "senha-boa-2026"})[0], 400)
        lista = {v["email"]: v for v in self.c.req("GET", "/admin/vendedores")[1]["vendedores"]}
        self.assertIsNone(lista["x@mdtech.com.br"]["convite_expira"])
        # chutar códigos bloqueia o IP
        cli = Cliente(self.app)
        for i in range(B.MAX_POR_IP):
            cli.req("POST", "/convite/ver", {"convite": f"falso{i}"}, ip="7.7.7.7")
        self.assertEqual(cli.req("POST", "/convite/ver", {"convite": "qualquer"}, ip="7.7.7.7")[0], 429)

    def test_banco_antigo_ganha_coluna_admin(self):
        import sqlite3
        caminho = Path(self.tmp.name) / "antigo.sqlite"
        con = sqlite3.connect(caminho)
        con.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, nome TEXT NOT NULL DEFAULT '', "
                    "hash TEXT NOT NULL, trocar_senha INTEGER NOT NULL DEFAULT 1, ativo INTEGER NOT NULL DEFAULT 1, "
                    "criado INTEGER NOT NULL, atualizado INTEGER NOT NULL, ultimo_login INTEGER)")
        con.execute("INSERT INTO usuarios (email, hash, criado, atualizado) VALUES ('a@b.com', 'x', 1, 1)")
        con.commit(); con.close()
        db = B.Banco(caminho)
        self.assertEqual(db.usuario("a@b.com")["admin"], 0)
        db.fechar()

    def test_permissao_do_banco(self):
        self.assertEqual(self.banco.stat().st_mode & 0o777, 0o660)   # www-data + grupo catalogo_mdtech (pasta 2770), ver deploy.sh


if __name__ == "__main__":
    unittest.main()
