from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import json, sys
saida = sys.argv[1]
F = "assets/fontes/"
W, H = 1080, 1920
NAVY, AZUL_TXT, MUT = (25, 60, 108), (24, 116, 161), (96, 108, 126)
CORES = {"Laparoscopia": (245, 166, 35), "Urologia": (54, 169, 225), "Histeroscopia": (198, 75, 140)}
f = lambda n, s: ImageFont.truetype(F + n, s)
prod = json.load(open("site/produtos.json", encoding="utf-8"))
cont = {e: sum(1 for p in prod if e in (p.get("especialidades") or [p["especialidade"]])) for e in CORES}
FOTOS = {"Laparoscopia": "A153.C", "Urologia": "A0322", "Histeroscopia": "10-0385-00"}
img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
for y in range(H):
    t = y / H; d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip((246, 251, 254), (210, 233, 249))))
# topo: zona de segurança dos stories (~250 px) só com a logo
d.rectangle((0, 0, W, 230), fill=NAVY)
logo = Image.open("assets/logos/logo-mdtech-hor-branco.png").convert("RGBA"); logo.thumbnail((440, 110), Image.LANCZOS)
img.paste(logo, ((W - logo.width) // 2, 130 - logo.height // 2 + 20), logo)
for i, c in enumerate(CORES.values()):
    d.rectangle((i * W // 3, 230, (i + 1) * W // 3, 240), fill=c)
def centro(y, texto, fonte, cor):
    w = d.textlength(texto, font=fonte); d.text(((W - w) / 2, y), texto, font=fonte, fill=cor)
centro(310, "CATÁLOGO DIGITAL", f("Poppins-SemiBold.ttf", 26), AZUL_TXT)
centro(356, "Tudo da MDTech,", f("Poppins-Bold.ttf", 74), NAVY)
centro(446, "em um só lugar.", f("Poppins-Bold.ttf", 74), NAVY)
centro(570, "Instrumentais e óticas cirúrgicas", f("Poppins-Regular.ttf", 29), MUT)
centro(610, "para laparoscopia, urologia e histeroscopia.", f("Poppins-Regular.ttf", 29), MUT)
def faixa(y, esp, codigo):
    cor = CORES[esp]; h = 260
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle((64, y + 8, W - 56, y + h + 8), 30, fill=70)
    img.paste(Image.new("RGB", (W, H), (120, 160, 200)), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
    dd = ImageDraw.Draw(img); dd.rounded_rectangle((60, y, W - 60, y + h), 30, fill="white")
    dd.rounded_rectangle((60, y, 76, y + h), 8, fill=cor); dd.rounded_rectangle((60, y + 8, 76, y + h - 8), 4, fill=cor)
    rotulo = esp.upper(); fr = f("Poppins-Bold.ttf", 24); wl = dd.textlength(rotulo, font=fr) + 44
    dd.rounded_rectangle((104, y + 26, 104 + wl, y + 70), 22, fill=cor)
    dd.text((104 + wl / 2, y + 48), rotulo, font=fr, fill="white", anchor="mm")
    dd.text((W - 92, y + 48), f"{cont[esp]} produtos", font=f("Poppins-Medium.ttf", 24), fill=MUT, anchor="rm")
    foto = Image.open("site/" + next(p["foto_thumb"] for p in prod if p["codigo"] == codigo).split("?")[0]).convert("RGB")
    bruto = ImageChops.difference(foto, Image.new("RGB", foto.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 18 else 0)
    foto = foto.crop(bruto.getbbox()); box = (W - 2 * 104, h - 116); foto.thumbnail(box, Image.LANCZOS)
    img.paste(foto, ((W - foto.width) // 2, y + 92 + (box[1] - foto.height) // 2))
for i, esp in enumerate(CORES):
    faixa(720 + i * 286, esp, FOTOS[esp])
d = ImageDraw.Draw(img)
# chamada; abaixo de ~1580 fica livre para o adesivo de link do Instagram
d.rounded_rectangle((60, 1590, W - 60, 1672), 41, fill=NAVY)
d.text((W / 2, 1631), "Códigos, medidas e fichas técnicas", font=f("Poppins-SemiBold.ttf", 28), fill="white", anchor="mm")
centro(1700, "catalogo.mdtechsm.com.br", f("Poppins-Medium.ttf", 24), NAVY)
img.save(saida, "PNG", optimize=True); print("ok", img.size)
