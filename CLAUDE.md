# MDTech — catálogo e materiais

> Lido automaticamente pelo Claude Code. Para decisões históricas, ver `DOCUMENTACAO_PROJETO.md`.
> Skill de UI/UX do projeto: `.claude/skills/mdtech-ui-ux/`.

## O que é
Marca própria MDTech, com produtos de 3 fornecedores (TONGLU = Laparoscopia, TIAN SONG = Urologia/Histeroscopia,
ASAP = Óticas HD-4K). Uma planilha (`dados/Base_MDTech_Consolidada.xlsx`) é a **fonte única da verdade** e
alimenta, via `gerar.py`: catálogos PDF, fichas técnicas PDF e o catálogo digital (site estático no GitHub Pages).

## Um repositório só
Tudo mora neste repositório (`andrecanesin/catalogo-mdtech`, público). O `site/` é uma pasta comum, não é mais repo separado.
```
dados/        planilha-base            assets/       imagens (por fornecedor), logos, fontes, ícones
mdtech/       núcleo Python            geradores/    catalogo, fichas, card, dashboard, site
site/         HTML/CSS/JS escritos à mão (+ arquivos gerados, ignorados no git)
.github/workflows/publicar.yml         publica no Pages a cada push na main
```
Os arquivos gerados (`site/produtos.json`, `meta.json`, `fotos/`, `fichas/`, `catalogos/`) estão no `.gitignore`;
o GitHub Actions os recria a cada publicação.

## Como publicar
1. Editar a planilha e/ou o HTML/CSS/JS do `site/`.
2. (Opcional) conferir local: `python gerar.py fichas --separados && python gerar.py site`, depois `python -m http.server` dentro de `site/`.
3. `git add`, `git commit`, `git push origin main`. O workflow **Publicar site** roda sozinho (aba Actions); em ~minutos o Pages atualiza.
- Catálogos em PDF (130 MB+) **não** são gerados no Actions nem entram no git: gerar local (`gerar.py catalogo --todos`) e subir como Release (ver `site/PRODUCAO.md`).

## Comandos
```bash
python gerar.py tudo                  # checklist + dashboard + catálogos + fichas (local)
python gerar.py fichas --separados    # antes de 'site', para o botão de download aparecer
python gerar.py site                  # produtos.json + fotos + fichas -> site/
python gerar.py dashboard             # painel de pendências (inclui status das fotos)
python gerar.py catalogo Laparoscopia --preview   # preview HTML sem gerar PDF
python painel.py                      # painel local (127.0.0.1:8800) com botões para os comandos acima
```
Todas as flags: `LEIA-ME.md`.

## Regras de ouro
1. A base é a única fonte da verdade (ANVISA/NCM/specs só nela).
2. Nomes de coluna só em `mdtech/base.py` (`COLUNAS`); todo gerador lê via `mdtech.base.carregar()`.
3. Cor por especialidade em `mdtech/marca.py::ACCENT`; `site/js/config.js` é espelho manual.
4. Diâmetro sempre via `mdtech.textos.diametro_fmt(item)` (mm vs Fr).
5. Foto = arquivo nomeado pelo código em `assets/imagens/<FORNECEDOR>/` (matcher tolerante, `mdtech/fotos.py`).
6. Não editar arquivos gerados à mão. Não commitar PDF grande (GitHub bloqueia > 100 MB).

## Modelo por tipo de tarefa
O padrão do projeto é **Sonnet 5.5 com esforço médio**. Antes de começar uma tarefa, avisar o André se ela
exigir outro modelo, dizendo qual e por quê.
- **Subir para Opus 5.5:** refatoração grande de `mdtech/` ou `geradores/`; redesenho do layout do catálogo ou
  do site; auditoria completa de código; depuração que não resolveu em duas tentativas.
- **Descer para Haiku 5.5:** tarefas repetitivas e simples (renomear, formatar, conferir listas).
- **Todo o resto:** seguir no Sonnet 5.5, sem avisar.

## Antes do deploy em servidor (lembrete)
O projeto vai para um servidor próprio, não para o GitHub Pages. Ao planejar o deploy:
- **Preços:** em desenvolvimento podem ficar no git, mas o repositório é **público**. Antes de ir ao ar, tirar os preços do
  repositório (planilha, `produtos.json`) e servi-los só por onde houver controle de acesso; revisar a regra "sem preço" da skill.
- **Publicação:** `.github/workflows/publicar.yml` hoje publica no Pages; trocar pelo envio ao servidor.
- **Catálogos PDF:** continuam fora do git (Release ou envio direto ao servidor).

## Estado dos dados (base de 08/11/2026, 174 linhas / 152 SKUs únicos)
- ANVISA: aguardando novos registros do regulatório. Vazio em 49 linhas (40 SKUs): 30 "em processo" (processo_Anvisa.xlsx de 23/09, pode estar velho) e 17 linhas /
  14 códigos sem registro e sem processo: A0320, A0322, A0323, A0210.1, A0211.1, A0222, A1101.1–A1104.1, A1105.1,
  A1106.1, A1106.2, F1104.
- A219 = 82568290004 (arquivo ANVISA de 27/10 prevalece). A2101 = 82568290002, mas o arquivo lista 2 números: confirmar com o regulatório.
- A215-2.C e A310.C sem registro (o nº 82568290004 só existia na aba antiga, removida).
- Comprimento vazio em 48 SKUs, diâmetro vazio em 35 SKUs: sobra só o que o fornecedor não informou nos catálogos
  TONGLU, TIAN SONG e ASAP.
- A108: divergência de diâmetro (descrição D=5MM x catálogo TONGLU Φ4×3000mm); confirmar com o fornecedor.
- `dashboard` mostra o mapa atualizado.

## Histórico resumido
- 23/09: corrigidos diâmetro em Fr ausente no site, A153.C ausente do catálogo de Laparoscopia (erro de linha inicial),
  cor de accent triplicada; removida a aba REGISTROS ANVISA (nenhum script a lia).
- 27/10: aplicados registros ANVISA do arquivo de 27/10 (35 linhas) e publicado o site.
- 05/11: decisão de unificar em repositório único, com publicação por GitHub Actions (este arquivo).
- 08/11: base com 24 comprimentos novos (17 extraídos das descrições e 7 dos catálogos da TONGLU: A206 e A145 = 330 mm;
  clamps A272, A273, A275, A276 e A277 = 65, 45, 25, 25 e 55 mm). Catálogos da TONGLU, TIAN SONG (urologia 2025 e
  cirurgia 2023.5) e ASAP conferidos: não trazem comprimento de camisas, peças guia, eletrodos, trocartes,
  adaptadores, evacuadores nem clips.
