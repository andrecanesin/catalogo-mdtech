#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Painel local da MDTech: botões para rodar os geradores sem abrir terminal.

    python painel.py              # abre http://127.0.0.1:8800 no navegador
    python painel.py --porta 9000 --sem-navegador

Só usa a biblioteca padrão. Escuta apenas em 127.0.0.1 (nunca na rede) e só roda
as ações da lista ACOES abaixo — nada digitado no navegador vira comando.
O painel NÃO faz commit nem push: mostra o que mudou (git status) e lembra de publicar.
"""
import argparse, json, subprocess, sys, threading, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent
SITE = RAIZ / "site"
SAIDA = RAIZ / "saida"
GERAR = str(RAIZ / "gerar.py")

# nome -> (rótulo, descrição, [passos]); cada passo = argumentos do gerar.py
ACOES = {
    "conferir":  ("Conferir pendências", "Fotos casadas × faltantes e painel de pendências (dashboard).",
                  [["checklist"], ["dashboard"]]),
    "fichas":    ("Gerar fichas técnicas", "1 PDF por código (é o que o botão do site usa).",
                  [["fichas", "--separados"]]),
    "catalogos": ("Gerar catálogos (PDF)", "Um PDF por especialidade + completo. Pesado (130 MB+), nunca vai pro git.",
                  [["catalogo", "--todos", "--perfil", "digital"]]),
    "site":      ("Atualizar dados do site", "produtos.json, fotos e fichas dentro de site/ (rode as fichas antes).",
                  [["site"]]),
    "preparar":  ("Preparar site para conferir", "Fichas + dados do site, na ordem certa. Depois abra o site local.",
                  [["fichas", "--separados"], ["site"]]),
    "tudo":      ("Gerar tudo (local)", "Checklist, dashboard, catálogos e fichas — como `gerar.py tudo`.",
                  [["tudo"]]),
}

_lock = threading.Lock()
_job = {"acao": None, "rodando": False, "linhas": [], "codigo": None}


def _rodar(acao):
    rotulo, _, passos = ACOES[acao]
    try:
        for args in passos:
            _job["linhas"].append(f"$ python gerar.py {' '.join(args)}")
            p = subprocess.Popen([sys.executable, "-u", GERAR, *args], cwd=str(RAIZ),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace",
                                 env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
            for ln in p.stdout:
                _job["linhas"].append(ln.rstrip("\n"))
            _job["codigo"] = p.wait()
            if _job["codigo"] != 0:
                _job["linhas"].append(f"✘ falhou (código {_job['codigo']}) — passos seguintes cancelados.")
                return
        _job["linhas"].append("✔ concluído.")
    except Exception as e:  # noqa: BLE001 — qualquer erro deve aparecer no log do painel
        _job["codigo"] = -1
        _job["linhas"].append(f"✘ erro ao rodar: {e}")
    finally:
        _job["rodando"] = False


def iniciar(acao):
    with _lock:
        if _job["rodando"]:
            return False
        _job.update(acao=acao, rodando=True, linhas=[], codigo=None)
    threading.Thread(target=_rodar, args=(acao,), daemon=True).start()
    return True


def _contar(pasta, padrao):
    return len(list(pasta.glob(padrao))) if pasta.exists() else 0


def estado():
    meta = {}
    try:
        meta = json.loads((SITE / "meta.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    try:
        git = subprocess.run(["git", "status", "--short"], cwd=str(RAIZ), capture_output=True,
                             text=True, encoding="utf-8", timeout=10).stdout.splitlines()
    except Exception:  # noqa: BLE001
        git = None
    return {
        "site": {"produtos": meta.get("total"), "com_foto": meta.get("com_foto"),
                 "fichas": _contar(SITE / "fichas", "*.pdf"),
                 "catalogos": _contar(SITE / "catalogos", "*.pdf")},
        "saida_pdfs": _contar(SAIDA, "*.pdf"),
        "git": git,
    }


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def log_message(self, *a):
        pass

    def _host_ok(self):
        return (self.headers.get("Host") or "").split(":")[0] in ("127.0.0.1", "localhost")

    def _json(self, obj, status=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._host_ok():
            return self.send_error(403)
        u = urlparse(self.path)
        if u.path == "/":
            b = PAGINA.replace("__ACOES__", json.dumps(
                {k: {"rotulo": v[0], "desc": v[1]} for k, v in ACOES.items()}, ensure_ascii=False)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/api/estado":
            return self._json({**estado(), "job": {"acao": _job["acao"], "rodando": _job["rodando"],
                                                    "codigo": _job["codigo"], "linhas": _job["linhas"][:]}})
        if u.path.startswith("/site/") or u.path == "/site":
            self.path = self.path[len("/site"):] or "/"   # serve a pasta site/ para conferir
            return super().do_GET()
        self.send_error(404)

    def do_POST(self):
        # cabeçalho próprio: um formulário de outro site não consegue enviá-lo
        if not self._host_ok() or self.headers.get("X-Painel") != "1":
            return self.send_error(403)
        u = urlparse(self.path)
        if u.path == "/api/rodar":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                acao = json.loads(self.rfile.read(n) or b"{}").get("acao")
            except ValueError:
                acao = None
            if acao not in ACOES:
                return self._json({"erro": "ação desconhecida"}, 400)
            if not iniciar(acao):
                return self._json({"erro": "já existe uma execução em andamento"}, 409)
            return self._json({"ok": True})
        self.send_error(404)


PAGINA = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Painel MDTech</title>
<style>
:root{--navy:#193C6C;--ciano:#36A9E1;--ink:#232D3C;--cinza:#606C7E;--painel:#F4F7FB;--linha:#DFE6EF;--ok:#2FA9A2;--erro:#E06666}
*{box-sizing:border-box}body{margin:0;font-family:Poppins,system-ui,sans-serif;color:var(--ink);background:var(--painel)}
header{background:var(--navy);color:#fff;padding:16px 20px;border-bottom:4px solid var(--ciano)}
header b{font-size:18px}header small{display:block;opacity:.75;font-size:12px}
main{max-width:980px;margin:0 auto;padding:20px;display:grid;gap:20px}
h2{font-size:14px;margin:0 0 10px;color:var(--navy);text-transform:uppercase;letter-spacing:.04em}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.n{background:#fff;border:1px solid var(--linha);border-radius:10px;padding:12px}.n b{font-size:22px;color:var(--navy);display:block}.n span{font-size:12px;color:var(--cinza)}
.acoes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
button.a{display:flex;flex-direction:column;justify-content:flex-start;text-align:left;background:#fff;border:1px solid var(--linha);border-radius:10px;padding:14px;cursor:pointer;font:inherit;min-height:44px}
button.a:hover:not(:disabled){border-color:var(--ciano)}button.a:focus-visible{outline:3px solid var(--ciano)}
button.a:disabled{opacity:.5;cursor:not-allowed}button.a b{display:block;color:var(--navy)}button.a span{font-size:12px;color:var(--cinza)}
pre{background:#101a2b;color:#d9e4f2;border-radius:10px;padding:14px;margin:0;max-height:360px;overflow:auto;font:12px/1.5 "IBM Plex Mono",ui-monospace,monospace;white-space:pre-wrap}
.s{font-size:13px;margin:8px 0;color:var(--cinza)}.s.ok{color:var(--ok)}.s.erro{color:var(--erro)}
.git{background:#fff;border:1px solid var(--linha);border-radius:10px;padding:12px;font:12px/1.6 "IBM Plex Mono",ui-monospace,monospace;white-space:pre-wrap}
a.l{color:var(--navy);font-weight:600}
</style></head><body>
<header><b>Painel MDTech</b><small>Gera fichas, catálogos e dados do site · só nesta máquina</small></header>
<main>
<section><h2>Situação atual</h2><div class="cards" id="cards"></div></section>
<section><h2>Ações</h2><div class="acoes" id="acoes"></div>
<p class="s">Para conferir: <a class="l" href="/site/index.html" target="_blank">abrir o site local</a> (usa o que está em <code>site/</code>).</p></section>
<section><h2>Execução</h2><div class="s" id="st">Nada em execução.</div><pre id="log" aria-live="polite">Aguardando…</pre></section>
<section><h2>Pendente de publicar (git status)</h2><div class="git" id="git">…</div>
<p class="s">O painel não faz commit nem push. Para publicar: <code>git add</code>, <code>git commit</code>, <code>git push origin main</code> e acompanhar a aba Actions.</p></section>
</main>
<script>
const ACOES=__ACOES__, $=s=>document.querySelector(s);
const hd={"X-Painel":"1","Content-Type":"application/json"};
$("#acoes").innerHTML=Object.entries(ACOES).map(([k,v])=>`<button class="a" data-a="${k}"><b>${v.rotulo}</b><span>${v.desc}</span></button>`).join("");
document.querySelectorAll("button.a").forEach(b=>b.onclick=async()=>{
  const r=await fetch("/api/rodar",{method:"POST",headers:hd,body:JSON.stringify({acao:b.dataset.a})});
  if(!r.ok){const e=await r.json();$("#st").className="s erro";$("#st").textContent=e.erro||"erro";}
  atualizar();});
async function atualizar(){
  const d=await (await fetch("/api/estado")).json(), j=d.job, s=d.site;
  $("#cards").innerHTML=[["Produtos no site",s.produtos??"—"],["Com foto",s.com_foto??"—"],["Fichas em site/",s.fichas],["Catálogos em site/",s.catalogos],["PDFs em saida/",d.saida_pdfs]]
    .map(([k,v])=>`<div class="n"><b>${v}</b><span>${k}</span></div>`).join("");
  document.querySelectorAll("button.a").forEach(b=>b.disabled=j.rodando);
  const st=$("#st");
  if(j.rodando){st.className="s";st.textContent="Executando: "+ACOES[j.acao].rotulo+"…";}
  else if(j.acao){const ok=j.codigo===0;st.className="s "+(ok?"ok":"erro");st.textContent=(ok?"Concluído: ":"Falhou: ")+ACOES[j.acao].rotulo;}
  const log=$("#log"), fim=log.scrollTop+log.clientHeight>=log.scrollHeight-8;
  if(j.acao){log.textContent=j.linhas.join("\\n");if(fim)log.scrollTop=log.scrollHeight;}
  $("#git").textContent=d.git===null?"git indisponível nesta máquina.":(d.git.length?d.git.join("\\n"):"Nada pendente: tudo já está commitado.");
}
atualizar();setInterval(atualizar,1500);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Painel local MDTech")
    ap.add_argument("--porta", type=int, default=8800)
    ap.add_argument("--sem-navegador", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.porta), H)
    url = f"http://127.0.0.1:{a.porta}/"
    print(f"Painel MDTech em {url}  (Ctrl+C para sair)")
    if not a.sem_navegador:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    main()
