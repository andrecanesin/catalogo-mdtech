#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Painel local da MDTech (uso do marketing, só nesta máquina).

    python painel.py              # abre http://127.0.0.1:8800 no navegador
    python painel.py --porta 9000 --sem-navegador

Faz só duas coisas:
  1) mostrar o que falta de informação (ANVISA, NCM, foto) e abrir o painel completo de pendências;
  2) gerar o material IMPRESSO (catálogos e propostas; foto original, páginas casadas) em saida/impresso/. Sempre liberado (dá para gerar
     testes); enquanto faltar ANVISA/NCM, o painel só avisa que esses itens saem como "em registro".
Fichas, catálogos digitais, propostas digitais e o site NÃO ficam aqui: o GitHub gera e publica tudo isso sozinho,
e o site é a fonte única (evita duas versões diferentes).

Só usa a biblioteca padrão (lê a planilha pelo núcleo do projeto). Escuta apenas em 127.0.0.1 e só roda as ações
da lista abaixo — nada digitado no navegador vira comando. Não faz commit nem push.
"""
import argparse, json, os, subprocess, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
SAIDA = RAIZ / "saida"
IMPRESSO = SAIDA / "impresso"
GERAR = str(RAIZ / "gerar.py")

# montagem do catálogo impresso -> flag de paridade do gerar.py
MONTAGENS = {
    "par":   ("Separado", "capa + miolo + contracapa (miolo com páginas PAR)"),
    "impar": ("Unificado", "capas das linhas no meio (miolo com páginas ÍMPAR)"),
    "mult4": ("Caderno", "total de páginas múltiplo de 4"),
}

_lock = threading.Lock()
_job = {"acao": None, "rodando": False, "linhas": [], "codigo": None}


# ---------------------------------------------------------------- pendências (lidas da planilha)
def pendencias():
    """SKUs únicos com informação faltando, por campo. Lê a base pelo núcleo do projeto.
    Só campos que todo item deve ter (Ø e comprimento ficam de fora: há itens que não têm essas medidas)."""
    from mdtech import base as B, fotos as F
    itens = B.carregar()
    por = {}
    for it in itens:
        por.setdefault(it["codigo"], []).append(it)
    vazio = lambda it, k: not str(it.get(k) or "").strip()
    campos = {
        "anvisa":      lambda its: any(vazio(i, "anvisa") for i in its),
        "foto":        lambda its: F.buscar(its[0]["codigo"]) is None,
        "ncm":         lambda its: any(vazio(i, "ncm") for i in its),
    }
    return {"total": len(por),
            "faltando": {c: sorted(cod for cod, its in por.items() if f(its)) for c, f in campos.items()}}


# ---------------------------------------------------------------- execução de comandos
def _rodar(passos):
    try:
        for args in passos:
            _job["linhas"].append(f"$ python gerar.py {' '.join(args)}")
            p = subprocess.Popen([sys.executable, "-u", GERAR, *args], cwd=str(RAIZ),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace",
                                 env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            for ln in p.stdout:
                _job["linhas"].append(ln.rstrip("\n"))
            _job["codigo"] = p.wait()
            if _job["codigo"] != 0:
                _job["linhas"].append(f"✘ falhou (código {_job['codigo']}).")
                return
        _job["linhas"].append("✔ concluído. Os PDFs estão em saida/impresso/ (botão \"Abrir pasta\").")
    except Exception as e:  # noqa: BLE001 — qualquer erro deve aparecer no log do painel
        _job["codigo"] = -1
        _job["linhas"].append(f"✘ erro ao rodar: {e}")
    finally:
        _job["rodando"] = False


def iniciar(nome, passos):
    with _lock:
        if _job["rodando"]:
            return False
        _job.update(acao=nome, rodando=True, linhas=[], codigo=None)
    threading.Thread(target=_rodar, args=(passos,), daemon=True).start()
    return True


def abrir_pasta():
    IMPRESSO.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(IMPRESSO))                      # noqa: S606 — pasta fixa do projeto
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(IMPRESSO)])
    else:
        subprocess.Popen(["xdg-open", str(IMPRESSO)])


def estado():
    pdfs = sorted(IMPRESSO.glob("*.pdf")) if IMPRESSO.exists() else []
    return {"impresso_pdfs": [p.name for p in pdfs],
            "job": {"acao": _job["acao"], "rodando": _job["rodando"],
                    "codigo": _job["codigo"], "linhas": _job["linhas"][:]}}


# ---------------------------------------------------------------- servidor
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_ok(self):
        return (self.headers.get("Host") or "").split(":")[0] in ("127.0.0.1", "localhost")

    def _send(self, body, tipo, status=200):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, obj, status=200):
        self._send(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", status)

    def do_GET(self):
        if not self._host_ok():
            return self.send_error(403)
        u = urlparse(self.path).path
        if u == "/":
            return self._send(PAGINA.replace("__MONTAGENS__", json.dumps(
                {k: {"nome": v[0], "desc": v[1]} for k, v in MONTAGENS.items()}, ensure_ascii=False)),
                "text/html; charset=utf-8")
        if u == "/api/estado":
            return self._json(estado())
        if u == "/api/pendencias":
            try:
                p = pendencias()
                return self._json(p)
            except Exception as e:  # noqa: BLE001
                return self._json({"erro": f"não consegui ler a planilha: {e}"}, 500)
        if u == "/pendencias":          # painel completo (HTML do dashboard), regerado a cada abertura
            r = subprocess.run([sys.executable, GERAR, "dashboard"], cwd=str(RAIZ), capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            arq = SAIDA / "Dashboard_Pendencias_MDTech.html"
            if r.returncode != 0 or not arq.exists():
                return self._send("Não consegui gerar o painel de pendências.\n" + (r.stdout + r.stderr)[-800:],
                                  "text/plain; charset=utf-8", 500)
            return self._send(arq.read_bytes(), "text/html; charset=utf-8")
        self.send_error(404)

    def do_POST(self):
        # cabeçalho próprio: um formulário de outro site não consegue enviá-lo
        if not self._host_ok() or self.headers.get("X-Painel") != "1":
            return self.send_error(403)
        u = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            dados = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            dados = {}
        if u == "/api/catalogo-impresso":
            modo = dados.get("modo")
            if modo not in MONTAGENS:
                return self._json({"erro": "montagem desconhecida"}, 400)
            ok = iniciar(f"Catálogos impressos · {MONTAGENS[modo][0]}",
                         [["catalogo", "--todos", "--perfil", "impressao", "--paridade", modo]])
            return self._json({"ok": True}) if ok else self._json({"erro": "já existe uma execução em andamento"}, 409)
        if u == "/api/propostas-impressas":
            modo = dados.get("modo")
            if modo not in MONTAGENS:
                return self._json({"erro": "montagem desconhecida"}, 400)
            ok = iniciar(f"Propostas impressas · {MONTAGENS[modo][0]}",
                         [["kits", "--perfil", "impressao", "--paridade", modo]])
            return self._json({"ok": True}) if ok else self._json({"erro": "já existe uma execução em andamento"}, 409)
        if u == "/api/abrir-pasta":
            abrir_pasta()
            return self._json({"ok": True})
        self.send_error(404)


PAGINA = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Painel MDTech</title>
<style>
:root{--navy:#193C6C;--ciano:#36A9E1;--ink:#232D3C;--cinza:#606C7E;--painel:#F4F7FB;--linha:#DFE6EF;--ok:#2FA9A2;--erro:#C62828;--amb:#F5A623}
*{box-sizing:border-box}body{margin:0;font-family:Poppins,system-ui,sans-serif;color:var(--ink);background:var(--painel)}
header{background:var(--navy);color:#fff;padding:16px 20px;border-bottom:4px solid var(--ciano)}
header b{font-size:18px}header small{display:block;opacity:.75;font-size:12px}
main{max-width:900px;margin:0 auto;padding:20px;display:grid;gap:22px}
h2{font-size:14px;margin:0 0 10px;color:var(--navy);text-transform:uppercase;letter-spacing:.04em;display:flex;align-items:center;gap:12px}
h2 button{margin-left:auto;font:inherit;font-size:12px;border:1px solid var(--linha);background:#fff;border-radius:8px;padding:6px 12px;cursor:pointer;color:var(--navy)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.n{background:#fff;border:1px solid var(--linha);border-left:5px solid var(--ok);border-radius:10px;padding:12px}
.n.falta{border-left-color:var(--erro)}.n b{font-size:26px;color:var(--ok);display:block;line-height:1.1}.n.falta b{color:var(--erro)}
.n span{font-size:12px;color:var(--cinza)}
details{background:#fff;border:1px solid var(--linha);border-radius:10px;padding:8px 14px;margin-top:8px;font-size:13px}
summary{cursor:pointer;font-weight:600;color:var(--navy)}details p{margin:8px 0 2px;font:12px/1.7 "IBM Plex Mono",ui-monospace,monospace;color:var(--cinza)}
.s{font-size:13px;margin:10px 0 0;color:var(--cinza)}.s a{color:var(--navy);font-weight:600}
.gate{border-radius:10px;padding:12px 14px;font-size:13px;margin-bottom:12px}
.gate.aviso{background:#fff4e0;border:1px solid var(--amb);color:#7a4b00}.gate.ok{background:#e6f6f4;border:1px solid var(--ok);color:#16615c}
.imp{background:#fff;border:1px solid var(--linha);border-radius:10px;padding:14px;display:grid;gap:12px}
.imp label{font-size:12px;color:var(--cinza);display:block;margin-bottom:4px}
select{font:inherit;font-size:14px;padding:9px 10px;border:1px solid var(--linha);border-radius:8px;width:100%;background:#fff}
.btns{display:flex;gap:10px;flex-wrap:wrap}
button.p{font:inherit;font-size:14px;font-weight:600;border:0;border-radius:9px;padding:12px 18px;cursor:pointer;background:var(--navy);color:#fff;min-height:44px}
button.p.sec{background:#fff;color:var(--navy);border:1px solid var(--linha)}
button.p:disabled{opacity:.45;cursor:not-allowed}button.p:focus-visible,select:focus-visible{outline:3px solid var(--ciano)}
pre{background:#101a2b;color:#d9e4f2;border-radius:10px;padding:14px;margin:0;max-height:300px;overflow:auto;font:12px/1.5 "IBM Plex Mono",ui-monospace,monospace;white-space:pre-wrap}
.st{font-size:13px;margin:0 0 8px;color:var(--cinza)}.st.ok{color:var(--ok)}.st.erro{color:var(--erro)}
</style></head><body>
<header><b>Painel MDTech</b><small>Marketing · uso interno, só nesta máquina</small></header>
<main>
<section><h2>O que falta de informação <button id="atualizar">Atualizar</button></h2>
  <div class="cards" id="cards">Lendo a planilha…</div><div id="listas"></div>
  <p class="s"><a href="/pendencias" target="_blank">Abrir o painel completo de pendências</a> (lista por produto e fornecedor, com exportação CSV).</p></section>
<section><h2>Impresso · foto original, só nesta máquina</h2>
  <div class="gate aviso" id="gate">Verificando…</div>
  <div class="imp">
    <div><label for="modo">Montagem (páginas casadas para a gráfica) — vale para catálogos e propostas</label><select id="modo"></select></div>
    <div class="btns"><button class="p" id="gerar">Gerar catálogos impressos</button>
      <button class="p" id="gerar-prop">Gerar propostas impressas</button>
      <button class="p sec" id="pasta">Abrir pasta dos impressos</button></div>
    <p class="s" id="pdfs" style="margin:0"></p>
  </div></section>
<section><h2>Execução</h2><p class="st" id="st">Nada em execução.</p><pre id="log">Aguardando…</pre></section>
</main>
<script>
const M=__MONTAGENS__, $=s=>document.querySelector(s), hd={"X-Painel":"1","Content-Type":"application/json"};
const ROT={anvisa:"Registro ANVISA",ncm:"NCM",foto:"Foto"};
$("#modo").innerHTML=Object.entries(M).map(([k,v])=>`<option value="${k}">${v.nome} — ${v.desc}</option>`).join("");
async function pend(){
  $("#cards").textContent="Lendo a planilha…";
  const r=await fetch("/api/pendencias"),d=await r.json();
  if(d.erro){$("#cards").textContent=d.erro;return;}
  $("#cards").innerHTML=Object.entries(ROT).map(([k,t])=>{const n=d.faltando[k].length;
    return `<div class="n ${n?"falta":""}"><b>${n?n:"✓"}</b><span>${t}${n?" · SKUs":" · completo"}</span></div>`}).join("");
  $("#listas").innerHTML=Object.entries(ROT).filter(([k])=>d.faltando[k].length).map(([k,t])=>
    `<details><summary>${t}: ${d.faltando[k].length} de ${d.total} SKUs</summary><p>${d.faltando[k].join(" · ")}</p></details>`).join("");
  const a=d.faltando.anvisa.length,n=d.faltando.ncm.length,g=$("#gate");
  g.className="gate "+((a||n)?"aviso":"ok");
  g.innerHTML=(a||n)?`<b>Pode gerar testes.</b> Faltam ${a?`<b>${a}</b> SKUs sem ANVISA`:""}${a&&n?" e ":""}${n?`<b>${n}</b> sem NCM`:""}: esses itens saem como "em registro" no impresso.`
    :"<b>Pronto para imprimir:</b> ANVISA e NCM estão completos.";
}
let rodando=false;
function trava(){$("#gerar").disabled=rodando;$("#gerar-prop").disabled=rodando;}
$("#atualizar").onclick=pend;
$("#gerar").onclick=async()=>{const r=await fetch("/api/catalogo-impresso",{method:"POST",headers:hd,body:JSON.stringify({modo:$("#modo").value})});
  if(!r.ok){const e=await r.json();$("#st").className="st erro";$("#st").textContent=e.erro||"erro";} estado();};
$("#gerar-prop").onclick=async()=>{const r=await fetch("/api/propostas-impressas",{method:"POST",headers:hd,body:JSON.stringify({modo:$("#modo").value})});
  if(!r.ok){const e=await r.json();$("#st").className="st erro";$("#st").textContent=e.erro||"erro";} estado();};
$("#pasta").onclick=()=>fetch("/api/abrir-pasta",{method:"POST",headers:hd,body:"{}"});
async function estado(){
  const d=await (await fetch("/api/estado")).json(),j=d.job;rodando=j.rodando;trava();
  const st=$("#st");
  if(j.rodando){st.className="st";st.textContent="Executando: "+j.acao+"…";}
  else if(j.acao){const ok=j.codigo===0;st.className="st "+(ok?"ok":"erro");st.textContent=(ok?"Concluído: ":"Falhou: ")+j.acao;}
  const log=$("#log"),fim=log.scrollTop+log.clientHeight>=log.scrollHeight-8;
  if(j.acao){log.textContent=j.linhas.join("\\n");if(fim)log.scrollTop=log.scrollHeight;}
  $("#pdfs").textContent=d.impresso_pdfs.length?"Já gerados em saida/impresso/: "+d.impresso_pdfs.join(", "):"Nenhum PDF impresso gerado ainda.";
}
pend();estado();setInterval(estado,1500);
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
