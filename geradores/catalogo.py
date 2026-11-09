#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MIOLO de catálogo MDTech (WeasyPrint / HTML+CSS) — layout oficial.

Só o miolo — capa/contra/divisórias no InDesign.
Layout: família = cabeçalho divisor · grade 2 colunas · card (foto + specs).
Ligado ao core: base, fotos, fontes, logo e cores vêm de mdtech/.

Perfis (pós-processo, NÃO alteram o layout):
  --perfil digital    -> INDICE ligado, sem páginas em branco (PDF navegável)
  --perfil impressao  -> paridade p/ encaixe frente-e-verso (páginas em branco no fim)
       --paridade par | impar | mult4
"""
import os, re, base64, html, unicodedata, math
from collections import defaultdict, OrderedDict
from weasyprint import HTML

from mdtech import config, marca as M, base as B, fotos as F, textos as T

# ---- paths do core ----
FONTS  = str(config.FONTES)
IMGDIR = str(config.IMAGENS)
LOGO   = str(config.LOGO_COLORIDO)

NAVY = M.hexnavy if hasattr(M, "hexnavy") else "#193C6C"
INK  = "#1a2230"; LINE = "#d8dee8"; MUT = "#9aa4b2"

# configuração de catálogo (marca/linha/ordem por especialidade). A cor
# "accent" NÃO mora mais aqui — vem de mdtech.marca.accent_hex(), fonte
# única (ver mdtech/marca.py::ACCENT).
ESPECS = {
    "Laparoscopia": {"marca":"TONGLU","linha":"MDTech Laparoscopia",
        "ordem":["Pinças de apreensão e dissecção","Tesouras","Porta-agulhas",
                 "Aplicadores de clip e clips","Pinças - Clamps / Bulldog","Afastadores",
                 "Trocateres","Eletrodos e Cabos HF","Cabos de fibra ótica","Agulhas",
                 "Irrigação e aspiração","Manipulador uterino"]},
    "Urologia":{"marca":"TIAN SONG","linha":"MDTech Urologia",
        "ordem":["Endoscópios autoclaváveis","Conjunto de camisas para cistoscopia",
                 "Pinças endoscópicas flexíveis","Conjunto para uretrotomia",
                 "Ressectoscópio monopolar 4mm","Ressectoscópio bipolar 4mm",
                 "Cistoscopia pediátrica","Litotripsia para cálculo de bexiga",
                 "Trocater de cistostomia","Evacuador de Hoffman","Evacuador de Ellik",
                 "Adaptador de Ev. Ellik","Acessórios"]},
    "Histeroscopia":{"marca":"TIAN SONG","linha":"MDTech Ginecologia",
                 "ordem":["Endoscópios autoclaváveis","Histeroscopia 2.9mm",
                 "Ressectoscópio monopolar 4mm","Ressectoscópio bipolar 4mm","Acessórios"]},
    "Óticas HD-4K":{"marca":"ASAP","linha":"MDTech Óticas HD-4K","ordem":[]},
}

def hex2rgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def tint(h,p):
    r,g,b=hex2rgb(h); return f"#{int(r+(255-r)*(1-p)):02X}{int(g+(255-g)*(1-p)):02X}{int(b+(255-b)*(1-p)):02X}"
def font_face(fam,file,w,style="normal"):
    with open(os.path.join(FONTS,file),"rb") as f: b=base64.b64encode(f.read()).decode()
    return (f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:{style};"
            f"src:url(data:font/ttf;base64,{b}) format('truetype');}}")
def b64file(p):
    with open(p,"rb") as f: return base64.b64encode(f.read()).decode()

def load_rows(espec):
    """Carrega as linhas da especialidade via mdtech.base (fonte única do
    contrato de colunas — COLUNAS em mdtech/base.py). Não lê o Excel direto
    aqui: se um nome de coluna mudar na planilha, ajusta só em base.py e
    este arquivo continua funcionando sem tocar em nada."""
    itens = B.por_especialidade(B.carregar(), espec)
    return [{nome: it.get(chave) for chave, nome in B.COLUNAS.items()} for it in itens]

def nome_curto(desc):
    # usa o limpador do core (mesma regra: corta em MDTECH, minúsculas p/ preposições, siglas)
    return T.nome_produto(desc)

def find_img(code):
    p=F.buscar(code)          # matcher tolerante do core (.C, caixa, traço)
    return str(p) if p else None

def esc(x): return html.escape("" if x is None else str(x))
FALTA = '<span class="falta">—</span>'   # campo pendente = vermelho
def val(x): return esc(x) if x not in (None,"") else FALTA
def dims(i):
    p=[]
    if i.get("Ø (mm)") not in (None,""):
        p.append(f'Ø {esc(i["Ø (mm)"])} mm')
    elif i.get("Ø (Fr)") not in (None,""):
        p.append(f'Ø {esc(i["Ø (Fr)"])} Fr')
    if i["Comp. (mm)"] not in (None,""): p.append(f'C {esc(i["Comp. (mm)"])} mm')
    if i["Ângulo"] not in (None,""):   p.append(esc(i["Ângulo"]))
    return " · ".join(p) if p else FALTA

import re as _re

def _eh_pinca(familia):
    return bool(_re.search(r"pin[cç]a", familia or "", _re.IGNORECASE))

def selo_angulo_html(angulo, familia):
    """Selo com o ícone de ângulo sobre a foto do card. Aparece em qualquer
    ótica/endoscópio (Uro, Histero, Óticas HD-4K — todos usam 'ângulo' como
    ângulo de visão da lente); a única exceção é a pinça Mixter 90°
    (Laparoscopia), onde 'ângulo' é geometria da ponta, não vista de lente.
    Sem ícone correspondente ao valor = sem selo."""
    if _eh_pinca(familia):
        return ""
    ic = T.icone_angulo_b64(angulo)
    if not ic:
        return ""
    return f'<span class="selo-ang"><img src="data:image/png;base64,{ic}"></span>'

# Perfil impressão = foto ORIGINAL (alta resolução p/ a gráfica); digital = foto reduzida (1200 px, JPEG).
FOTO_ALTA = False

def _foto_uri(img):
    if FOTO_ALTA:
        ext=os.path.splitext(img)[1].lstrip(".").lower() or "jpeg"
        return f"data:image/{ext};base64,{b64file(img)}"
    return f"data:image/jpeg;base64,{F.jpeg_reduzido_b64(img)}"

def card(i,accent):
    img=find_img(i["Código"])
    selo = selo_angulo_html(i.get("Ângulo"), i.get("Família"))
    if img:
        photo=f'<div class="cphoto"><img src="{_foto_uri(img)}">{selo}</div>'
    else:
        photo=(f'<div class="cphoto ph phred"><span class="pht">sem foto</span>'
               f'<span class="phc">{esc(i["Código"])}</span>{selo}</div>')
    anvisa=i.get("Registro ANVISA")
    anv=(f'ANVISA {esc(anvisa)}' if anvisa not in (None,"")
         else '<span class="reg falta">ANVISA em registro</span>')
    return (f'<div class="card">{photo}'
            f'<span class="ccod">{esc(i["Código"])}</span>'
            f'<div class="cname">{esc(nome_curto(i["Descrição (PT)"]))}</div>'
            f'<div class="cdims">{dims(i)}</div>'
            f'<div class="cncm">NCM {val(i["NCM"])}</div>'
            f'<div class="canv">{anv}</div></div>')

def _nav_fam(idx, nomes, pre):
    """Barra fixa do rodapé (digital): família anterior / próxima, para a página atual. Elemento 'running':
    cada família redefine a barra, e o WeasyPrint a repete em todas as páginas dela.
    Os ids levam o prefixo da linha (pre) para não colidirem quando os catálogos são juntados no completo."""
    ant = f'<a class="np" href="#{pre}-fam{idx-1}">&#8249; {esc(nomes[idx-1])}</a>' if idx > 0 else ""
    prox = f'<a class="np" href="#{pre}-fam{idx+1}">{esc(nomes[idx+1])} &#8250;</a>' if idx < len(nomes)-1 else ""
    return f'<div class="navfam">{ant}<span class="sp"></span>{prox}</div>'

def familia_html(fam,items,accent,idx,nomes=None,pre="c"):
    cards="".join(card(i,accent) for i in items)
    nav = _nav_fam(idx, nomes, pre) if nomes else ""
    return f"""
    <section class="fam" id="{pre}-fam{idx}">{nav}
      <div class="fam-head">
        <span class="tab"></span>
        <div class="fh-txt"><div class="kicker">{esc(items[0]['_linha'])}</div>
        <h2>{esc(fam)}</h2></div>
        <div class="badge">Autoclavável 134° · {len(items)} itens</div>
      </div>
      <div class="grid">{cards}</div>
    </section>"""

def indice_html(fam_list, titulo, accent, pre="c"):
    lis="".join(f'<li><a href="#{pre}-fam{idx}">{esc(f)}</a></li>' for idx,(f,_) in enumerate(fam_list))
    return f"""
    <section class="toc" id="{pre}-toc">
      <div class="toc-head"><span class="tab"></span>
        <div><div class="kicker">MDTech {esc(titulo)}</div><h2>Índice</h2></div></div>
      <ul class="toc-list">{lis}</ul>
    </section>"""

def _doc_html(espec_nome, incluir_indice):
    E=ESPECS[espec_nome]; accent=M.accent_hex(espec_nome); titulo=espec_nome
    rows=load_rows(espec_nome)
    for r in rows: r["_linha"]=E["linha"]
    grouped=defaultdict(list)
    for d in rows: grouped[d["Família"]].append(d)
    for d in rows:                                  # cross-listing "Também em"
        extra=d.get("Também em")
        if not extra: continue
        for f in [x.strip() for x in str(extra).replace(";","|").split("|") if x.strip()]:
            if f!=d["Família"]: grouped[f].append(d)
    fam=OrderedDict()
    for f in E["ordem"]:
        if f in grouped: fam[f]=grouped.pop(f)
    for f,items in grouped.items(): fam[f]=items

    faces="".join([font_face("Poppins","Poppins-Regular.ttf",400),
        font_face("Poppins","Poppins-Medium.ttf",500),font_face("Poppins","Poppins-SemiBold.ttf",600),
        font_face("Poppins","Poppins-Bold.ttf",700),font_face("Plex","IBMPlexMono-Regular.ttf",400),
        font_face("Plex","IBMPlexMono-Medium.ttf",500)])
    logo=b64file(LOGO)
    fam_list=list(fam.items())
    body=""
    pre=_slug(espec_nome).lower()                  # prefixo dos ids: único por linha (catálogo completo)
    if incluir_indice:
        body+=indice_html(fam_list, titulo, accent, pre)
    nomes=[f for f,_ in fam_list] if incluir_indice else None      # navegação fixa só no digital
    body+="".join(familia_html(f,items,accent,i,nomes,pre) for i,(f,items) in enumerate(fam_list))
    nav_idx=(f'<div class="navidx"><a class="np" href="#{pre}-toc">&#9776;&nbsp; Índice</a></div>' if incluir_indice else "")
    total=sum(len(v) for v in fam.values())
    skus=len({d["Código"] for v in fam.values() for d in v})
    A_TINT=tint(accent,0.10)
    ACC_TXT=M.accent_texto_hex(espec_nome)          # código do produto na cor da linha, versão AA
    if incluir_indice:   # digital: rodapé vira barra de navegação clicável
        RODAPE=(f'@bottom-left {{ content:element(navidx); vertical-align:middle; width:34mm; }}'
                f'@bottom-center {{ content:element(navfam); vertical-align:middle; width:112mm; }}'
                f'@bottom-right {{ content:counter(page); font-family:Plex; font-size:9pt; color:{NAVY}; vertical-align:middle; width:14mm; }}')
    else:                # impresso: rodapé institucional
        RODAPE=(f'@bottom-left {{ content:"Tecnologia que abre caminhos"; font-family:Poppins; font-size:7.5pt; color:{MUT}; }}'
                f'@bottom-right {{ content:counter(page); font-family:Plex; font-size:9pt; color:{NAVY}; }}')

    doc=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    {faces}
    @page {{ size:A4; margin:18mm;
      @top-left {{ content:element(brand); vertical-align:middle; }}
      @top-right {{ content:"{esc(titulo)}"; font-family:Poppins; font-weight:600; font-size:9pt;
                    color:{accent}; letter-spacing:.14em; text-transform:uppercase; vertical-align:middle; }}
      {RODAPE}
    }}
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:Poppins;color:{INK};}}
    .brand{{position:running(brand);}} .brand img{{height:7mm;}}
    /* barra fixa de navegação (digital). NÃO usar display:flex aqui: o WeasyPrint descarta os links. */
    .navidx{{position:running(navidx);}} .navfam{{position:running(navfam);text-align:center;}}
    .navfam .sp{{display:inline-block;width:5mm;}}
    .np{{display:inline-block;color:{NAVY};text-decoration:none;font-family:Poppins;font-weight:600;font-size:9.5pt;
         background:{A_TINT};border:.5pt solid {tint(accent,0.35)};border-radius:2mm;padding:1.6mm 3.4mm;white-space:nowrap;}}

    .toc{{break-after:page;}}
    .toc-head{{display:flex;align-items:stretch;gap:3.5mm;border-bottom:1.6pt solid {accent};
               padding-bottom:2mm;margin-bottom:6mm;}}
    .toc-head .kicker{{font-size:8pt;font-weight:600;color:{accent};letter-spacing:.16em;
                       text-transform:uppercase;margin-bottom:.6mm;}}
    .toc-head h2{{font-size:26pt;font-weight:600;color:{NAVY};line-height:1;}}
    .toc-list{{list-style:none;}}
    .toc-list li{{margin:0;border-bottom:.5pt solid {LINE};}}
    .toc-list a{{display:block;color:{NAVY};text-decoration:none;font-weight:600;font-size:13pt;padding:3mm 0;}}
    .toc-list a::after{{content:leader('.  ') target-counter(attr(href url),page);
                        color:{NAVY};font-weight:500;font-family:Plex;font-size:11pt;}}

    .fam{{margin-bottom:7mm;}}
    .fam-head{{display:flex;align-items:stretch;gap:3.5mm;border-bottom:1.6pt solid {accent};
               padding-bottom:2mm;margin-bottom:4mm;break-after:avoid;}}
    .tab{{width:2.4mm;background:{accent};border-radius:1.2mm;flex:none;}}
    .fh-txt{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
    .kicker{{font-size:8pt;font-weight:600;color:{accent};letter-spacing:.16em;
             text-transform:uppercase;margin-bottom:.6mm;}}
    .fam-head h2{{font-size:18pt;font-weight:600;color:{NAVY};line-height:1;}}
    .badge{{align-self:center;font-size:8pt;font-weight:500;color:#3d4756;background:{A_TINT};
            padding:1mm 2.4mm;border-radius:2mm;white-space:nowrap;}}

    .grid{{font-size:0;}}
    .card{{display:inline-block;width:50%;vertical-align:top;break-inside:avoid;
           padding-bottom:4.5mm;}}
    .card:nth-child(odd){{padding-right:3mm;}}
    .card:nth-child(even){{padding-left:3mm;}}
    .cphoto{{height:30mm;background:#fff;border:.5pt solid {LINE};border-radius:1.5mm;
             display:flex;align-items:center;justify-content:center;overflow:hidden;padding:3mm;
             position:relative;}}
    .cphoto img{{max-width:100%;max-height:100%;object-fit:contain;}}
    .cphoto.ph{{flex-direction:column;gap:1mm;background:{A_TINT};border:1pt dashed {accent};}}
    .cphoto.phred{{border:1pt dashed #E06666;}}
    .cphoto.phred .pht{{color:#E06666;}}
    .selo-ang{{position:absolute;top:1.5mm;left:1.5mm;z-index:5;background:#fff;border:.5pt solid {LINE};
               border-radius:1.5mm;padding:.6mm;line-height:0;}}
    .selo-ang img{{width:20mm;height:13mm;display:block;}}
    .falta{{color:#E06666;font-weight:700;}} .canv .reg.falta{{color:#E06666;font-style:italic;}}
    .pht{{font-size:8.5pt;font-weight:600;color:{accent};letter-spacing:.06em;}}
    .phc{{font-family:Plex;font-size:8.5pt;color:#5b6675;}}
    .ccod{{display:block;font-family:Plex;font-weight:500;color:{ACC_TXT};font-size:9.5pt;margin-top:2.2mm;}}
    .cname{{font-family:Poppins;font-weight:600;color:{NAVY};font-size:11pt;line-height:1.2;margin:.8mm 0 1mm;}}
    .cdims{{font-family:Poppins;font-size:9.5pt;color:#2f3a49;}}
    .cncm{{font-family:Plex;font-size:8.5pt;color:#46515f;margin-top:.8mm;}}
    .canv{{font-family:Plex;font-size:8.5pt;color:#46515f;margin-top:.3mm;}}
    .canv .reg{{font-family:Poppins;font-style:italic;color:#46515f;}}
    .canv .reg.falta{{color:#C62828;}}
    </style></head><body>
    <div class="brand"><img src="data:image/png;base64,{logo}"></div>{nav_idx}
    {body}</body></html>"""
    return doc, skus, total, len(fam), accent


def _slug(titulo):
    return unicodedata.normalize("NFKD",titulo).encode("ascii","ignore").decode().replace(' ','_').replace('/','-')

def _pad_paridade(pdf_path, paridade):
    """Anexa página(s) A4 em branco ao PDF p/ atingir a paridade (pós-processo)."""
    if paridade in (None,"nenhuma"): return 0
    from pypdf import PdfReader, PdfWriter
    r=PdfReader(pdf_path); n=len(r.pages)
    if paridade=="par":   add=(0 if n%2==0 else 1)
    elif paridade=="impar": add=(0 if n%2==1 else 1)
    elif paridade=="mult4": add=(-n)%4
    else: add=0
    if not add: return 0
    w=PdfWriter()
    for pg in r.pages: w.add_page(pg)
    W_pt,H_pt=r.pages[0].mediabox.width, r.pages[0].mediabox.height
    for _ in range(add): w.add_blank_page(width=W_pt, height=H_pt)
    with open(pdf_path,"wb") as f: w.write(f)
    return add


def preview(espec_nome, perfil="digital"):
    """Salva o HTML puro (o mesmo que vira PDF) pra abrir direto no navegador —
    não roda o WeasyPrint, é instantâneo. Ótimo pra iterar em CSS: edita aqui
    embaixo (bloco <style> em _doc_html), roda de novo, dá F5 no navegador.

    O navegador ignora a regra @page (é só de impressão), então injeta aqui
    um CSS extra só-de-preview que simula a folha A4 (largura 210mm,
    centralizada, com a mesma margem de 18mm que o PDF usa) — sem isso o
    conteúdo ficaria esticado 100% da largura da tela, bem diferente do PDF.
    Esse CSS extra NÃO entra no PDF final (só é usado aqui no preview)."""
    global FOTO_ALTA
    FOTO_ALTA = (perfil!="digital")
    incluir_indice = (perfil=="digital")
    doc, skus, total, nfam, accent = _doc_html(espec_nome, incluir_indice)
    css_preview = """<style>
      html{background:#dde3ec;}
      body{max-width:210mm;margin:24px auto;padding:18mm;background:#fff;
           box-shadow:0 4px 28px rgba(20,30,50,.25);box-sizing:border-box;}
    </style>"""
    doc = doc.replace("</head>", css_preview + "</head>")
    out = config.SAIDA / f"Preview_Catalogo_{_slug(espec_nome)}.html"
    out.write_text(doc, encoding="utf-8")
    print(f"Preview: {espec_nome} ({skus} SKUs) -> {out}")
    print("Abra esse arquivo no navegador (duplo-clique) pra ver o layout.")
    return str(out)


def build(espec_nome, perfil="digital", paridade="nenhuma"):
    global FOTO_ALTA
    FOTO_ALTA = (perfil!="digital")          # impressão = foto original
    incluir_indice = (perfil=="digital")     # digital = navegável com índice
    doc, skus, total, nfam, accent = _doc_html(espec_nome, incluir_indice)
    pasta = config.SAIDA_DIGITAL if perfil=="digital" else config.SAIDA_IMPRESSO
    out=str(pasta / f"Miolo_Catalogo_{_slug(espec_nome)}_MDTech.pdf")
    HTML(string=doc,base_url=IMGDIR).write_pdf(out)
    brancos = 0 if perfil=="digital" else _pad_paridade(out, paridade)
    from pypdf import PdfReader
    npag=len(PdfReader(out).pages)
    extra=f" (+{brancos} branco → {npag}, paridade '{paridade}')" if brancos else ""
    print(f"  {espec_nome}: {skus} SKUs · {total} cards · {nfam} famílias → {npag} págs{extra}  [{os.path.basename(out)}]")
    return out, npag


def gerar(especialidade=None, todos=False, paridade="nenhuma", perfil="digital"):
    print(f"Miolo (layout oficial WeasyPrint) · perfil='{perfil}'"
          + (f" · paridade='{paridade}'" if perfil!='digital' else " · índice navegável, sem brancos"))
    alvos = list(ESPECS.keys()) if todos else [especialidade]
    saidas=[]
    for esp in alvos:
        if esp not in ESPECS:
            print(f"  [aviso] especialidade desconhecida: {esp}"); continue
        saidas.append(build(esp, perfil=perfil, paridade=paridade))
    return saidas


if __name__=="__main__":
    import sys
    arg=sys.argv[1] if len(sys.argv)>1 else "Laparoscopia"
    if arg.lower()=="todos": gerar(todos=True, perfil="digital")
    else: gerar(arg, perfil="digital")
