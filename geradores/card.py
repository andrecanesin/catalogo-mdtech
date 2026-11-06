# -*- coding: utf-8 -*-
"""Gerador de CARD PROMOCIONAL (WhatsApp 1080x1350).

Uso via CLI:   python gerar.py card --codigo A299 --preco 5.990
Uso direto:    from geradores.card import gerar; gerar(CFG)

Se 'codigo' for informado, puxa titulo/specs/anvisa/foto da base automaticamente;
os campos passados em CFG sempre têm prioridade (override manual).
"""
from PIL import Image
from mdtech import config, marca as M, base as B, fotos as F, textos as T
from mdtech.layout import (canvas, rrect, medir, texto, texto_centro,
                           texto_espacado, carregar_recortada, encaixar,
                           multilinha, ajustar)

Wd, Ht, MX = 1080, 1350, 64
# posições verticais (ajuste fino aqui)
BAND_H = 150
HERO_Y0, HERO_Y1 = 336, 760
CARD_Y0, CARD_Y1 = 786, 1022
NOTA_Y = 1048
PRICE_Y0, PRICE_Y1 = 1088, 1244
FOOT_LOGO_Y, FOOT_TAG_Y = 1262, 1310


def _da_base(codigo):
    """Monta um CFG parcial a partir da base, se o código existir."""
    it = B.por_codigo(B.carregar(), codigo)
    if not it:
        return {}
    diam = T.diametro_fmt(it)   # "16,5 Fr" ou "5 mm" ou "" — nunca lê 'diametro' direto
    specs = " · ".join(x for x in [
        f"Ø {diam}" if diam else "",
        f"C {it['comprimento']} mm" if it.get("comprimento") else "",
        it.get("angulo") and f"{it['angulo']}",
        "Autoclavável" if str(it.get("autoclavavel","")).lower() in ("sim","x","true","1") else "",
    ] if x)
    foto = F.buscar(codigo)
    return dict(
        titulo=T.nome_produto(it.get("descricao") or codigo),   # nome limpo, igual fichas/catálogo
        specs=specs,
        anvisa=it.get("anvisa") or None,
        hero=str(foto) if foto else None,
    )


def gerar(cfg: dict):
    # merge: base (se houver codigo) < cfg do usuário
    dados = {}
    if cfg.get("codigo"):
        dados.update(_da_base(cfg["codigo"]))
    dados.update({k: v for k, v in cfg.items() if v is not None})

    img, d = canvas(Wd, Ht, M.WHITE)

    # ---- TOPO ----
    d.rectangle([0, 0, Wd, BAND_H], fill=M.NAVY)
    if config.LOGO_BRANCO.exists():
        encaixar(img, Image.open(str(config.LOGO_BRANCO)).convert("RGBA"),
                 (60, 46, 60+284, 46+58), anchor="tl")
    badge = dados.get("badge", "LANÇAMENTO")
    if badge:
        pf = M.bold(26); pw, _ = medir(d, badge, pf)
        rrect(d, [Wd-MX-pw-56, 52, Wd-MX, 102], 25, fill=M.CYAN)
        texto(d, (Wd-MX-pw-28, 61), badge, pf, M.NAVY)

    # ---- TÍTULO (auto-ajuste + quebra até 2 linhas) ----
    titulo = dados.get("titulo", "")
    ft, linhas = ajustar(d, titulo, M.bold, max_w=Wd-2*MX-40, tam_ini=50,
                         max_linhas=2, tam_min=34)
    lead = int(ft.size*1.12)
    ty = 208 - (lead*len(linhas))//2
    multilinha(d, (0, ty), titulo, ft, M.NAVY, max_w=Wd-2*MX-40,
               leading=lead, max_linhas=2, centro=True, cx=Wd/2)
    sub_y = ty + lead*len(linhas) + 8
    if dados.get("specs"):
        texto_centro(d, Wd/2, sub_y, dados["specs"], M.med(22), M.GRAY)
        sub_y += 40
    rrect(d, [Wd/2-40, sub_y, Wd/2+40, sub_y+5], 3, fill=M.CYAN)

    # ---- HERO ----
    rrect(d, [MX, HERO_Y0, Wd-MX, HERO_Y1], 28, fill=M.PANEL)
    if dados.get("hero"):
        encaixar(img, carregar_recortada(dados["hero"]),
                 (96, HERO_Y0+20, Wd-96, HERO_Y0+20+264), anchor="tl")
    if dados.get("hero_extra"):
        encaixar(img, carregar_recortada(dados["hero_extra"]),
                 (120, HERO_Y1-168, 120+360, HERO_Y1-20), anchor="bl")

    # ---- CARDS DE PONTA ----
    pts = dados.get("pontas") or []
    if pts:
        n = len(pts); gap = 28; cw = (Wd-2*MX-gap*(n-1))/n
        for i, p in enumerate(pts):
            x0 = MX + i*(cw+gap); x1 = x0+cw
            rrect(d, [x0, CARD_Y0, x1, CARD_Y1], 22, fill=M.WHITE, outline=M.LINE, w=2)
            foto = p.get("img") or (F.buscar(p["codigo"]) if p.get("codigo") else None)
            if foto:
                encaixar(img, carregar_recortada(foto),
                         (x0+22, CARD_Y0+20, x1-22, CARD_Y0+20+100))
            d.line([x0+24, CARD_Y0+136, x1-24, CARD_Y0+136], fill=M.LINE, width=2)
            texto(d, (x0+30, CARD_Y0+152), p.get("codigo", ""), M.mono(30), M.NAVY)
            texto(d, (x0+30, CARD_Y0+192), p.get("nome", ""), M.bold(28), M.INK)
            if p.get("tag"):
                tf = M.med(19); tgw, _ = medir(d, p["tag"], tf)
                rrect(d, [x1-24-tgw-28, CARD_Y0+154, x1-24, CARD_Y0+154+34], 17, fill=M.CHIP)
                texto(d, (x1-24-tgw-14, CARD_Y0+160), p["tag"], tf, M.NAVY)

    # ---- NOTA ----
    if dados.get("nota"):
        f = M.med(22); w, _ = medir(d, dados["nota"], f)
        cx = (Wd-w)/2+16; y = NOTA_Y; ck = cx-34
        d.line([ck, y+16, ck+7, y+23], fill=M.CYAN, width=4)
        d.line([ck+7, y+23, ck+20, y+8], fill=M.CYAN, width=4)
        texto(d, (cx, y+4), dados["nota"], f, M.GRAY)

    # ---- PREÇO ----
    rrect(d, [MX, PRICE_Y0, Wd-MX, PRICE_Y1], 26, fill=M.NAVY)
    rrect(d, [MX, PRICE_Y0, MX+22, PRICE_Y1], 26, fill=M.CYAN)
    d.rectangle([MX+12, PRICE_Y0, MX+28, PRICE_Y1], fill=M.NAVY)
    texto(d, (124, PRICE_Y0+30), "PREÇO PROMOCIONAL DE LANÇAMENTO", M.med(24), M.SUB)
    preco = dados.get("preco", "")
    rs, big, cts = M.bold(40), M.bold(82), M.bold(46)
    texto(d, (120, PRICE_Y0+66), "R$", rs, M.CYAN); w1, _ = medir(d, "R$", rs)
    texto(d, (120+w1+14, PRICE_Y0+50), preco, big, M.WHITE); w2, _ = medir(d, preco, big)
    texto(d, (120+w1+14+w2, PRICE_Y0+66), ",00", cts, M.WHITE)
    if dados.get("anvisa"):
        rrect(d, [Wd-MX-232, PRICE_Y0+34, Wd-88, PRICE_Y0+134], 18, fill=M.NAVY2)
        texto_centro(d, Wd-MX-232/2-24, PRICE_Y0+50, "ANVISA", M.bold(24), M.CYAN)
        texto_centro(d, Wd-MX-232/2-24, PRICE_Y0+82, str(dados["anvisa"]), M.monor(24), M.WHITE)

    # ---- RODAPÉ (assinatura) ----
    if config.LOGO_COLORIDO.exists():
        lc = Image.open(str(config.LOGO_COLORIDO)).convert("RGBA")
        lw, lh = lc.size; h = 42; nw = int(lw*h/lh)
        img.alpha_composite(lc.resize((nw, h), Image.LANCZOS), (int((Wd-nw)/2), FOOT_LOGO_Y))
    texto_espacado(d, Wd/2, FOOT_TAG_Y, M.TAGLINE, M.med(17), M.MUT, track=3)

    saida = config.SAIDA / (dados.get("saida") or f"Card_{dados.get('codigo','MDTech')}.png")
    img.convert("RGB").save(str(saida), quality=95)
    print("Card gerado:", saida)
    return saida


# CFG de exemplo (rodar direto: python geradores/card.py)
CFG_EXEMPLO = dict(
    titulo="Pinça Bipolar de Coagulação",
    specs="Dupla ação · Ø 5 mm × 330 mm · 3 partes destacáveis · Autoclavável 134°C",
    hero="A299-3__2_.png", hero_extra="A108.png",
    pontas=[
        dict(img=None, codigo="A299-3", nome="Tipo Maryland", tag="dupla ação"),
        dict(img=None, codigo="A299",   nome="Atraumática",   tag="dupla ação"),
    ],
    nota="Acompanha cabo bipolar A108-2  ·  Ø 4 mm × 3 m  ·  plugue duplo",
    preco="5.990", anvisa="82568290004",
    saida="MDTech_Pinca_Bipolar_A299_lancamento.png",
)

if __name__ == "__main__":
    # ajusta caminhos relativos de hero/pontas para a pasta de imagens
    def _abs(n): 
        from mdtech import config as c
        return str(c.IMAGENS / n) if n and not str(n).startswith("/") else n
    cfg = dict(CFG_EXEMPLO)
    cfg["hero"] = _abs(cfg["hero"]); cfg["hero_extra"] = _abs(cfg.get("hero_extra"))
    gerar(cfg)
