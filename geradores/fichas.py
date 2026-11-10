#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FICHA TÉCNICA MDTech (WeasyPrint / HTML+CSS) — layout oficial.

  python gerar.py fichas --codigo A111     -> 1 PDF do código
  python gerar.py fichas --todos           -> PDF mestre (1 página por código)
  python gerar.py fichas --separados       -> 1 PDF por código (Ficha_<cod>_MDTech.pdf)

Mesmo motor do catálogo. Foto no mesmo padrão (caixa branca + borda), com
selo de ângulo sobre a foto quando o item tem Ângulo preenchido e existe
ícone correspondente em assets/icones/angulos/.
Ligado ao core: base, fotos, fontes, logos e cores.
"""
import os, base64, html, unicodedata
from datetime import date
from weasyprint import HTML

from mdtech import config, base as B, fotos as F, textos as T, marca as M

FONTS = str(config.FONTES)
NAVY="#193C6C"; INK="#1a2230"; LINE="#d8dee8"; MUT="#9aa4b2"; LAB="#8a94a3"
ZEBRA="#f4f6fa"; PANEL="#f7f9fc"

# accent por especialidade: fonte única em mdtech/marca.py::ACCENT (igual ao catálogo)
def accent(esp): return M.accent_hex(esp)

def font_face(fam,file,w,style="normal"):
    with open(os.path.join(FONTS,file),"rb") as f: b=base64.b64encode(f.read()).decode()
    return (f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{style};"
            f"src:url(data:font/ttf;base64,{b}) format('truetype');}}")
def b64file(p):
    with open(p,"rb") as f: return base64.b64encode(f.read()).decode()
def esc(x): return html.escape("" if x is None else str(x))
FALTA = '<span class="falta">—</span>'   # placeholder vermelho de campo pendente
def val(x): return esc(x) if x not in (None,"") else FALTA

import re as _re

def _eh_pinca(familia):
    return bool(_re.search(r"pin[cç]a", familia or "", _re.IGNORECASE))

def _selo_angulo_html(angulo, familia):
    """Selo com o ícone de ângulo sobre a foto. Aparece em qualquer
    ótica/endoscópio (Uro, Histero e as óticas HD-4K — todos usam 'ângulo' como
    ângulo de visão da lente); a única exceção é a pinça Mixter 90°
    (Laparoscopia), onde 'ângulo' é geometria da ponta, não vista de lente.
    Sem ícone correspondente ao valor = sem selo."""
    if _eh_pinca(familia):
        return ""
    ic = T.icone_angulo_b64(angulo)
    if not ic:
        return ""
    return f'<span class="selo-ang"><img src="data:image/png;base64,{ic}"></span>'

def _foto_html(item, ac):
    codigo = item.get("codigo", "")
    p = F.buscar(codigo)
    selo = _selo_angulo_html(item.get("angulo"), item.get("familia"))
    if p:
        # foto reduzida (1200 px, JPEG): a original embutida deixava cada ficha com até 5 MB
        return f'<div class="photo"><img src="data:image/jpeg;base64,{F.jpeg_reduzido_b64(str(p))}">{selo}</div>'
    return (f'<div class="photo ph" style="border-color:#E06666">'
            f'<span class="pht" style="color:#E06666">sem foto</span>'
            f'<span class="phc">{esc(codigo)}</span>{selo}</div>')

def _linha_marca(item):
    m=(item.get("marca") or "").strip()
    return "MDTech"   # marca própria (origem) — padrão da ficha

def _autoclav(item):
    return "Sim (134 °C)" if T.eh_sim(item.get("autoclavavel")) else val(item.get("autoclavavel"))

def _doc_html(item):
    ac=accent(item.get("especialidade"))
    faces="".join([font_face("Poppins","Poppins-Regular.ttf",400),
        font_face("Poppins","Poppins-Medium.ttf",500),font_face("Poppins","Poppins-SemiBold.ttf",600),
        font_face("Poppins","Poppins-Bold.ttf",700),font_face("Plex","IBMPlexMono-Regular.ttf",400),
        font_face("Plex","IBMPlexMono-Medium.ttf",500)])
    logo_b=b64file(str(config.LOGO_BRANCO))
    logo_c=b64file(str(config.LOGO_COLORIDO))
    nome=esc(T.nome_produto(item.get("descricao","")))
    cod=esc(item.get("codigo",""))
    esp=esc(item.get("especialidade",""))
    hoje=date.today().strftime("%d/%m/%Y")

    linhas=[
        ("CÓDIGO", f'<span class="mono">{cod}</span>', "DIÂMETRO (Ø)", (esc(T.diametro_fmt(item)) if T.diametro_fmt(item) else FALTA)),
        ("ESPECIALIDADE", esc(item.get("especialidade")), "COMPRIMENTO ÚTIL", (f'{esc(item["comprimento"])} mm' if item.get("comprimento") else FALTA)),
        ("FAMÍLIA", val(item.get("familia")), "ÂNGULO", val(item.get("angulo"))),
        ("MARCA / ORIGEM", _linha_marca(item), "AUTOCLAVÁVEL", _autoclav(item)),
    ]
    trs=""
    for i,(l1,v1,l2,v2) in enumerate(linhas):
        cls="zebra" if i%2==0 else ""
        trs+=(f'<tr class="{cls}">'
              f'<td><div class="lab">{l1}</div><div class="v">{v1}</div></td>'
              f'<td><div class="lab">{l2}</div><div class="v">{v2}</div></td></tr>')

    anv = esc(item.get("anvisa")) if item.get("anvisa") else '<span class="reg falta">em registro</span>'
    ncm = val(item.get("ncm"))

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    {faces}
    @page {{ size:A4; margin:0; }}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:Poppins;color:{INK};font-size:10pt;}}
    .mono{{font-family:Plex;}}

    /* header full-bleed */
    .head{{background:{NAVY};padding:9mm 16mm 8mm 16mm;position:relative;
           display:flex;align-items:center;justify-content:space-between;}}
    .head::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:6mm;background:{ac};}}
    .head .logo img{{height:11mm;}}
    .head .mid{{text-align:center;flex:1;}}
    .head .mid .esp{{color:{ac};font-weight:600;font-size:9pt;letter-spacing:.18em;}}
    .head .mid .sub{{color:#aeb9cc;font-size:7.5pt;margin-top:.6mm;}}
    .head .rt{{text-align:right;}}
    .head .rt .cod{{font-family:Plex;font-weight:500;color:#fff;font-size:15pt;letter-spacing:.04em;}}
    .head .rt .tag{{color:#aeb9cc;font-size:7pt;letter-spacing:.16em;margin-top:.4mm;}}

    .content{{padding:9mm 16mm 0 16mm;}}
    h1{{font-size:21pt;font-weight:700;color:{NAVY};line-height:1.1;margin-bottom:6mm;}}

    /* foto — mesmo padrão do catálogo (caixa branca + borda) */
    .photo{{height:52mm;background:#fff;border:.6pt solid {LINE};border-radius:2mm;
            display:flex;align-items:center;justify-content:center;overflow:hidden;
            padding:5mm;margin-bottom:7mm;position:relative;}}
    .photo img{{max-width:100%;max-height:100%;object-fit:contain;}}
    .photo.ph{{flex-direction:column;gap:1.5mm;border-style:dashed;}}
    .pht{{font-size:9pt;font-weight:600;letter-spacing:.06em;}}
    .phc{{font-family:Plex;font-size:8pt;color:#8a94a3;}}
    .selo-ang{{position:absolute;top:2.5mm;left:2.5mm;z-index:5;background:#fff;border:.6pt solid {LINE};
               border-radius:2mm;padding:1mm;line-height:0;}}
    .selo-ang img{{width:30mm;height:20mm;display:block;}}

    .h2{{font-size:12pt;font-weight:700;color:{NAVY};padding-bottom:2mm;
         border-bottom:1.6pt solid {ac};margin-bottom:3mm;}}

    table.specs{{width:100%;border-collapse:collapse;}}
    table.specs td{{width:50%;vertical-align:top;padding:2.6mm 4mm;border-bottom:.5pt solid {LINE};}}
    table.specs tr.zebra td{{background:{ZEBRA};}}
    .lab{{font-size:6.8pt;font-weight:500;color:{LAB};letter-spacing:.10em;
          text-transform:uppercase;margin-bottom:.8mm;}}
    .v{{font-size:11pt;font-weight:600;color:{INK};}}

    .desc{{padding:3mm 4mm 0 4mm;}}
    .desc .lab{{margin-bottom:1mm;}}
    .desc .txt{{font-family:Plex;font-size:8pt;color:#5b6675;line-height:1.4;}}

    .reg{{font-style:italic;color:#b6bdc8;font-weight:400;}}
    .falta{{color:#E06666;font-weight:700;}}      /* campo pendente = vermelho */
    .reg.falta{{font-style:italic;}}
    .regbox{{margin-top:7mm;background:{NAVY};border-radius:2.5mm;position:relative;
             display:flex;padding:5mm 6mm;overflow:hidden;}}
    .regbox::before{{content:"";position:absolute;left:0;top:0;bottom:0;width:4mm;background:{ac};}}
    .regbox .col{{flex:1;padding-left:3mm;}}
    .regbox .rlab{{font-size:7pt;color:#aeb9cc;letter-spacing:.10em;margin-bottom:1.2mm;}}
    .regbox .rval{{font-family:Plex;font-weight:500;color:#fff;font-size:13pt;letter-spacing:.04em;}}

    .wm{{text-align:center;margin-top:16mm;}}
    .wm img{{height:15mm;}}

    .foot{{position:fixed;left:16mm;right:16mm;bottom:9mm;
           display:flex;justify-content:space-between;align-items:center;
           border-top:.5pt solid {LINE};padding-top:2.5mm;
           font-size:7pt;color:{MUT};}}
    .foot b{{color:{NAVY};font-weight:600;}}
    </style></head><body>
      <div class="head">
        <div class="logo"><img src="data:image/png;base64,{logo_b}"></div>
        <div class="mid"><div class="esp">{esp}</div>
          <div class="sub">Instrumental cirúrgico · Ficha técnica</div></div>
        <div class="rt"><div class="cod">{cod}</div><div class="tag">FICHA TÉCNICA</div></div>
      </div>
      <div class="content">
        <h1>{nome}</h1>
        {_foto_html(item, ac)}
        <div class="h2">Especificações técnicas</div>
        <table class="specs">{trs}</table>
        <div class="desc"><div class="lab">Descrição (padrão de cadastro)</div>
          <div class="txt">{esc(item.get("descricao",""))}</div></div>
        <div class="regbox">
          <div class="col"><div class="rlab">REGISTRO ANVISA</div><div class="rval">{anv}</div></div>
          <div class="col"><div class="rlab">NCM</div><div class="rval">{ncm}</div></div>
        </div>
        <div class="wm"><img src="data:image/png;base64,{logo_c}"></div>
      </div>
      <div class="foot"><div><b>MDTech</b> · Tecnologia que abre caminhos</div><div>{hoje}</div></div>
    </body></html>"""

def _slug(s):
    return unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().replace(" ","_").replace("/","-")

def preview(codigo):
    """Salva o HTML puro de uma ficha (o mesmo que vira PDF) pra abrir direto
    no navegador — não roda o WeasyPrint, é instantâneo.

    O navegador ignora @page (é só de impressão), então injeta aqui um CSS
    extra só-de-preview que simula a folha A4 (largura 210mm, centralizada) —
    sem isso o conteúdo ficaria esticado 100% da largura da tela. A ficha usa
    @page margin:0 (cabeçalho full-bleed), então aqui não precisa de padding
    extra no body, só o max-width. Esse CSS extra NÃO entra no PDF final."""
    itens = B.carregar()
    it = B.por_codigo(itens, codigo)
    if not it:
        print(f"[erro] código não encontrado: {codigo}"); return None
    doc = _doc_html(it)
    css_preview = """<style>
      html{background:#dde3ec;}
      body{max-width:210mm;margin:24px auto;background:#fff;
           box-shadow:0 4px 28px rgba(20,30,50,.25);}
    </style>"""
    doc = doc.replace("</head>", css_preview + "</head>")
    out = config.SAIDA / f"Preview_Ficha_{_slug(it['codigo'])}.html"
    out.write_text(doc, encoding="utf-8")
    print(f"Preview: {it['codigo']} -> {out}")
    print("Abra esse arquivo no navegador (duplo-clique) pra ver o layout.")
    return str(out)


def gerar(codigo=None, todos=False, separados=False):
    itens=B.carregar()
    if separados:
        # 1 PDF por código. Código que aparece em 2 especialidades (cross-listing)
        # ganha sufixo da especialidade p/ não sobrescrever.
        from collections import Counter
        cont=Counter(_slug(it["codigo"]) for it in itens)
        saidas=[]
        for it in itens:
            slug=_slug(it["codigo"])
            if cont[slug]>1:
                slug=f"{slug}_{_slug(it.get('especialidade',''))}"
            saida=str(config.SAIDA_DIGITAL/f"Ficha_{slug}_MDTech.pdf")
            HTML(string=_doc_html(it), base_url=str(config.IMAGENS)).write_pdf(saida)
            saidas.append(saida)
        print(f"Fichas separadas: {len(saidas)} PDFs -> {config.SAIDA_DIGITAL}")
        return saidas
    if todos:
        docs=[_doc_html(it) for it in itens]
        saida=str(config.SAIDA_DIGITAL/"Fichas_MDTech.pdf")
        # une as páginas: renderiza cada uma e concatena
        from weasyprint import HTML as _H
        docs_render=[_H(string=d, base_url=str(config.IMAGENS)).render() for d in docs]
        base_doc=docs_render[0]
        all_pages=[p for dr in docs_render for p in dr.pages]
        base_doc.copy(all_pages).write_pdf(saida)
        print(f"Ficha mestre: {len(itens)} páginas -> {saida}")
        return saida
    it=B.por_codigo(itens,codigo)
    if not it:
        print(f"[erro] código não encontrado: {codigo}"); return None
    saida=str(config.SAIDA_DIGITAL/f"Ficha_{_slug(it['codigo'])}_MDTech.pdf")
    HTML(string=_doc_html(it), base_url=str(config.IMAGENS)).write_pdf(saida)
    print("Ficha gerada:", saida)
    return saida

if __name__=="__main__":
    gerar(codigo="A299")
