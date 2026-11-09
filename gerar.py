#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI único de geração de materiais MDTech.

    python gerar.py catalogo Laparoscopia
    python gerar.py catalogo --todos
    python gerar.py fichas --codigo A153
    python gerar.py fichas --todos
    python gerar.py fichas --separados       # 1 PDF por código (usado pelo botão do site)
    python gerar.py card --codigo A299 --preco 5.990 --hero A299-3__2_.png
    python gerar.py card --exemplo          # roda o CFG de exemplo completo
    python gerar.py checklist               # confere fotos casadas/faltantes
    python gerar.py site                     # exporta base -> produtos.json (catálogo digital)
    python gerar.py tudo                     # checklist + dashboard + catálogos + fichas
    python gerar.py tudo --perfil impressao --paridade impar
    python gerar.py tudo --sem-fichas        # ex.: só dashboard + catálogos
"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    ap = argparse.ArgumentParser(prog="gerar", description="Materiais MDTech")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("catalogo")
    p.add_argument("especialidade", nargs="?")
    p.add_argument("--todos", action="store_true")
    p.add_argument("--perfil", choices=["impressao", "digital"], default="digital",
                   help="impressao=paridade/brancos p/ gráfica · digital=índice navegável, sem brancos")
    p.add_argument("--paridade", choices=["nenhuma", "par", "impar", "mult4"],
                   default="nenhuma",
                   help="(só impressão) par=separado · impar=unificado · mult4=caderno")
    p.add_argument("--preview", action="store_true",
                   help="não gera PDF — salva o HTML puro em saida/Preview_Catalogo_<especialidade>.html "
                        "pra abrir no navegador e conferir layout/CSS rapidinho")

    p = sub.add_parser("fichas")
    p.add_argument("--codigo")
    p.add_argument("--todos", action="store_true",
                   help="1 PDF mestre com todos os códigos (1 página cada)")
    p.add_argument("--separados", action="store_true",
                   help="1 PDF por código (Ficha_<cod>_MDTech.pdf) — é o que 'gerar.py site' "
                        "casa e copia pra site/fichas/, pro botão de download na página de produto")
    p.add_argument("--preview", action="store_true",
                   help="não gera PDF — salva o HTML puro de --codigo em "
                        "saida/Preview_Ficha_<codigo>.html pra abrir no navegador")

    p = sub.add_parser("card")
    p.add_argument("--codigo")
    p.add_argument("--titulo"); p.add_argument("--specs")
    p.add_argument("--preco"); p.add_argument("--anvisa")
    p.add_argument("--hero"); p.add_argument("--hero-extra", dest="hero_extra")
    p.add_argument("--nota"); p.add_argument("--saida")
    p.add_argument("--exemplo", action="store_true")

    sub.add_parser("dashboard")
    sub.add_parser("checklist")
    sub.add_parser("site", help="exporta a base -> site/produtos.json (catálogo digital)")

    p = sub.add_parser("tudo", help="roda checklist + dashboard + catálogos + fichas de uma vez")
    p.add_argument("--perfil", choices=["impressao", "digital"], default="digital",
                   help="perfil dos catálogos (padrão: digital)")
    p.add_argument("--paridade", choices=["nenhuma", "par", "impar", "mult4"],
                   default="nenhuma", help="(só impressão)")
    p.add_argument("--sem-fichas", dest="sem_fichas", action="store_true", help="pula as fichas")
    p.add_argument("--sem-catalogo", dest="sem_catalogo", action="store_true", help="pula os catálogos")

    a = ap.parse_args()

    if a.cmd == "catalogo":
        from geradores import catalogo
        if a.preview:
            alvo = a.especialidade or "Laparoscopia"
            catalogo.preview(alvo, perfil=a.perfil)
        else:
            catalogo.gerar(a.especialidade, todos=a.todos, paridade=a.paridade, perfil=a.perfil)

    elif a.cmd == "fichas":
        from geradores import fichas
        if a.preview:
            if not a.codigo:
                print("[erro] --preview precisa de --codigo (ex.: fichas --codigo A153.C --preview)")
            else:
                fichas.preview(a.codigo)
        else:
            fichas.gerar(codigo=a.codigo, todos=a.todos, separados=a.separados)

    elif a.cmd == "card":
        from geradores import card
        from mdtech import config
        if a.exemplo:
            cfg = dict(card.CFG_EXEMPLO)
            cfg["hero"] = str(config.IMAGENS / cfg["hero"])
            if cfg.get("hero_extra"):
                cfg["hero_extra"] = str(config.IMAGENS / cfg["hero_extra"])
        else:
            cfg = {k: v for k, v in dict(
                codigo=a.codigo, titulo=a.titulo, specs=a.specs, preco=a.preco,
                anvisa=a.anvisa, nota=a.nota, saida=a.saida,
                hero=str(config.IMAGENS / a.hero) if a.hero else None,
                hero_extra=str(config.IMAGENS / a.hero_extra) if a.hero_extra else None,
            ).items() if v is not None}
        card.gerar(cfg)

    elif a.cmd == "dashboard":
        from geradores import dashboard
        dashboard.gerar()

    elif a.cmd == "site":
        from geradores import site
        site.gerar()

    elif a.cmd == "checklist":
        _checklist()

    elif a.cmd == "tudo":
        print("=== 1/4 · CHECKLIST DE FOTOS ===")
        _checklist()
        print("\n=== 2/4 · DASHBOARD DE PENDÊNCIAS ===")
        from geradores import dashboard
        dashboard.gerar()
        if not a.sem_catalogo:
            print("\n=== 3/4 · CATÁLOGOS (todos) ===")
            from geradores import catalogo
            catalogo.gerar(None, todos=True, paridade=a.paridade, perfil=a.perfil)
        else:
            print("\n=== 3/4 · CATÁLOGOS — pulado (--sem-catalogo) ===")
        if not a.sem_fichas:
            print("\n=== 4/4 · FICHAS (todas) ===")
            from geradores import fichas
            fichas.gerar(codigo=None, todos=True)
        else:
            print("\n=== 4/4 · FICHAS — pulado (--sem-fichas) ===")
        from mdtech import config
        print(f"\n✔ Concluído. Tudo em: {config.SAIDA}")


def _checklist():
    from mdtech import base as B, fotos as F
    casadas, faltantes = F.checklist(B.carregar())
    print(f"Fotos casadas: {len(casadas)} | faltantes: {len(faltantes)}")
    if faltantes:
        print("Faltando:", ", ".join(faltantes[:60]) + (" ..." if len(faltantes) > 60 else ""))


if __name__ == "__main__":
    main()
