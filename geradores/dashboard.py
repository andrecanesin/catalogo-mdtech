#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DASHBOARD de pendências de informação dos produtos (HTML).

  python gerar.py dashboard

Lê a base + pasta de fotos e gera um painel HTML com o que falta por produto:
Foto, Ø, Comprimento, NCM, Registro ANVISA. Inclui listas expansíveis por
fornecedor e botão "Baixar CSV". Foto é medida na pasta assets/imagens/.
"""
import re, json, datetime
from mdtech import config, base as B, fotos as F

CAMPOS=[("foto","Foto"),("diametro","Ø (mm/Fr)"),("comprimento","Comprimento"),
        ("ncm","NCM"),("anvisa","Registro ANVISA")]
ORD=["TONGLU","TIAN SONG","ASAP"]
def _vazio(v): return str(v or "").strip()==""
def _norm(s): return re.sub(r'[^A-Za-z0-9]','',str(s or '')).upper()
def _forn(it):
    m=(it.get("marca") or "").upper(); e=it.get("especialidade","")
    if "TONGLU" in m or e=="Laparoscopia": return "TONGLU"
    if "TIAN" in m or e in ("Urologia","Histeroscopia"): return "TIAN SONG"
    return "ASAP"
def _falta(it,c):
    if c=="foto": return F.buscar(it["codigo"]) is None
    if c=="diametro": return _vazio(it.get("diametro")) and _vazio(it.get("diametro_fr"))
    return _vazio(it.get(c))
def _cor(p): return "#2FA9A2" if p>=80 else ("#F5A623" if p>=50 else "#E06666")

def gerar():
    itens=B.carregar(); seen=set(); uniq=[]
    for it in itens:
        n=_norm(it["codigo"])
        if n not in seen: seen.add(n); uniq.append(it)
    tot=len(uniq)
    resumo={c:sum(_falta(it,c) for it in uniq) for c,_ in CAMPOS}
    porf={f:{"tot":0} for f in ORD}
    for it in uniq:
        f=_forn(it); porf[f]["tot"]+=1
        for c,_ in CAMPOS: porf[f][c]=porf[f].get(c,0)+_falta(it,c)
    dist={i:0 for i in range(len(CAMPOS)+1)}
    for it in uniq:
        ok=len(CAMPOS)-sum(_falta(it,c) for c,_ in CAMPOS); dist[ok]+=1
    det={c:{} for c,_ in CAMPOS}; pend_rows=[]
    for it in uniq:
        f=_forn(it)
        for c,lab in CAMPOS:
            if _falta(it,c):
                det[c].setdefault(f,[]).append(it["codigo"])
                pend_rows.append([it["codigo"],f,it.get("especialidade",""),it.get("familia",""),lab])
    for c in det:
        for f in det[c]: det[c][f]=sorted(det[c][f])

    # ---- KPIs ----
    def kpi(c,lab):
        falta=resumo[c]; ok=tot-falta; pct=round(ok/tot*100) if tot else 0
        return (f'<div class="kpi"><div class="kpi-lab">{lab}</div>'
                f'<div class="kpi-num">{falta}<span>faltam</span></div>'
                f'<div class="bar"><i style="width:{pct}%;background:{_cor(pct)}"></i></div>'
                f'<div class="kpi-sub">{ok}/{tot} preenchidos · {pct}%</div></div>')
    kpis="".join(kpi(c,lab) for c,lab in CAMPOS)

    # ---- tabela fornecedor ----
    rows=""
    for f in ORD:
        d=porf[f]; cells="".join(f'<td class="{"z" if d.get(c,0)==0 else ""}">{d.get(c,0)}</td>' for c,_ in CAMPOS)
        rows+=f'<tr><td class="fn">{f}</td><td>{d["tot"]}</td>{cells}</tr>'
    thead="".join(f"<th>{lab}</th>" for _,lab in CAMPOS)
    tfoot="".join(f"<td>{resumo[c]}</td>" for c,_ in CAMPOS)

    # ---- completude ----
    maxd=max(dist.values()) or 1; bars=""
    for k in range(len(CAMPOS),-1,-1):
        n=dist[k]; w=round(n/maxd*100)
        cor="#2FA9A2" if k==len(CAMPOS) else ("#36A9E1" if k>=3 else "#F5A623" if k>=1 else "#E06666")
        bars+=f'<div class="drow"><span class="dk">{k}/5</span><div class="db"><i style="width:{w}%;background:{cor}"></i></div><span class="dn">{n}</span></div>'

    # ---- listas expansíveis ----
    listas=""
    for c,lab in CAMPOS:
        tc=resumo[c]
        if tc==0:
            corpo='<p class="okp">Tudo preenchido ✓</p>'
        else:
            corpo=""
            for f in ORD:
                cods=det[c].get(f,[])
                if not cods: continue
                chips=" ".join(f'<span class="cx">{x}</span>' for x in cods)
                corpo+=f'<div class="grp"><b>{f}</b> <span>({len(cods)})</span><div class="cods">{chips}</div></div>'
        listas+=f'<details><summary><span>{lab}</span><em>{tc} faltam</em></summary><div class="det">{corpo}</div></details>'
    pend_json=json.dumps(pend_rows,ensure_ascii=False)
    hoje=datetime.date.today().strftime("%d/%m/%Y")

    html="""<!DOCTYPE html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard de Pendências — MDTech</title>
<style>
:root{--navy:#193C6C;--cyan:#36A9E1;--ink:#1a2230;--mut:#8a94a3;--line:#e3e9f2;--panel:#f4f7fb;}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;}
body{background:#eef2f7;color:var(--ink);padding:24px;}
.wrap{max-width:1040px;margin:0 auto;}
.head{background:var(--navy);color:#fff;border-radius:16px;padding:22px 26px;display:flex;justify-content:space-between;align-items:center;position:relative;overflow:hidden;}
.head::before{content:"";position:absolute;left:0;top:0;bottom:0;width:8px;background:var(--cyan);}
.head h1{font-size:22px;font-weight:800;} .head .sub{color:#aeb9cc;font-size:13px;margin-top:3px;}
.head .tot{text-align:right;} .head .tot b{font-size:34px;display:block;} .head .tot span{color:#aeb9cc;font-size:12px;}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:18px 0;}
.kpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;}
.kpi-lab{font-size:12px;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
.kpi-num{font-size:30px;font-weight:800;color:var(--navy);margin:6px 0 2px;}
.kpi-num span{font-size:12px;color:var(--mut);font-weight:600;margin-left:6px;}
.bar{height:8px;background:#eef2f7;border-radius:6px;overflow:hidden;margin:8px 0 6px;}
.bar i{display:block;height:100%;border-radius:6px;}
.kpi-sub{font-size:11px;color:var(--mut);}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px;}
.card h2{font-size:15px;color:var(--navy);margin-bottom:14px;}
table{width:100%;border-collapse:collapse;font-size:14px;}
th,td{padding:9px 10px;text-align:center;border-bottom:1px solid var(--line);}
th{background:var(--panel);color:var(--navy);font-size:12px;text-transform:uppercase;letter-spacing:.03em;}
td.fn{text-align:left;font-weight:700;color:var(--navy);} th:first-child,td:first-child{text-align:left;}
td.z{color:#2FA9A2;font-weight:700;} tfoot td{font-weight:800;background:#f0f6ff;color:var(--navy);}
.drow{display:flex;align-items:center;gap:12px;margin:7px 0;}
.dk{width:34px;font-weight:700;color:var(--navy);font-size:13px;}
.db{flex:1;height:14px;background:#eef2f7;border-radius:7px;overflow:hidden;}
.db i{display:block;height:100%;border-radius:7px;}
.dn{width:34px;text-align:right;color:var(--mut);font-size:13px;font-weight:600;}
.note{background:#fff8e6;border:1px solid #f5d98a;color:#7a5c12;font-size:12px;border-radius:10px;padding:10px 14px;margin-bottom:18px;}
details{border:1px solid var(--line);border-radius:10px;margin-bottom:8px;overflow:hidden;}
summary{cursor:pointer;padding:11px 14px;font-weight:600;color:var(--navy);background:var(--panel);list-style:none;display:flex;justify-content:space-between;}
summary::-webkit-details-marker{display:none;}
summary em{color:#E06666;font-style:normal;font-weight:700;font-size:13px;}
.det{padding:12px 14px;} .grp{margin-bottom:10px;} .grp b{color:var(--navy);} .grp>span{color:var(--mut);font-size:12px;}
.cods{margin-top:6px;display:flex;flex-wrap:wrap;gap:5px;}
.cx{font-family:ui-monospace,Menlo,monospace;font-size:11px;background:#eef4fb;color:#274a78;padding:2px 7px;border-radius:5px;}
.okp{color:#2FA9A2;font-weight:600;}
.btn{background:var(--cyan);color:#fff;border:0;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;}
.foot{color:var(--mut);font-size:11px;text-align:center;margin-top:8px;}
</style></head><body><div class="wrap">
  <div class="head"><div><h1>Dashboard de Pendências — Base MDTech</h1>
    <div class="sub">O que falta preencher por produto · gerado em __HOJE__</div></div>
    <div class="tot"><b>__TOT__</b><span>SKUs na base</span></div></div>

  <div class="grid">__KPIS__</div>

  <div class="note"><b>Foto</b> é medida na pasta <code>assets/imagens/</code>. Após adicionar fotos, rode <code>python gerar.py dashboard</code> de novo.</div>

  <div class="card"><h2>Pendências por fornecedor (quantidade que falta)</h2>
    <table><thead><tr><th>Fornecedor</th><th>SKUs</th>__THEAD__</tr></thead>
      <tbody>__ROWS__</tbody>
      <tfoot><tr><td>TOTAL</td><td>__TOT__</td>__TFOOT__</tr></tfoot></table></div>

  <div class="card"><h2>Completude por produto (campos preenchidos de 5)</h2>__BARS__</div>

  <div class="card"><h2 style="display:flex;justify-content:space-between;align-items:center">Listas de pendências <button class="btn" onclick="baixarCSV()">⬇ Baixar CSV</button></h2>__LISTAS__</div>

  <div class="foot">MDTech · Tecnologia que abre caminhos · fonte: Base_MDTech_Consolidada.xlsx</div>
</div>
<script>
const PEND=__PENDJSON__;
function baixarCSV(){
 let csv="codigo;fornecedor;especialidade;familia;campo_faltante\\n";
 PEND.forEach(r=>csv+=r.map(x=>String(x).replace(/;/g,",")).join(";")+"\\n");
 const b=new Blob([csv],{type:"text/csv;charset=utf-8"});
 const a=document.createElement("a");a.href=URL.createObjectURL(b);
 a.download="Pendencias_MDTech.csv";a.click();
}
</script></body></html>"""

    html=(html.replace("__HOJE__",hoje).replace("__TOT__",str(tot))
          .replace("__KPIS__",kpis).replace("__THEAD__",thead).replace("__ROWS__",rows)
          .replace("__TFOOT__",tfoot).replace("__BARS__",bars).replace("__LISTAS__",listas)
          .replace("__PENDJSON__",pend_json))
    out=config.SAIDA/"Dashboard_Pendencias_MDTech.html"
    out.write_text(html,encoding="utf-8")
    print("Dashboard:",out)
    return out

if __name__=="__main__":
    gerar()
