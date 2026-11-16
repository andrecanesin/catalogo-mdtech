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

    def test_permissao_do_banco(self):
        self.assertEqual(self.banco.stat().st_mode & 0o777, 0o660)   # www-data + grupo catalogo_mdtech (pasta 2770), ver deploy.sh


if __name__ == "__main__":
    unittest.main()
