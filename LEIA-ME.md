# Materiais MDTech — geração unificada

Um único projeto que gera **fichas técnicas**, **catálogos (miolo)**, **cards
promocionais**, um **dashboard de pendências** e alimenta o **catálogo digital
(site)**, tudo a partir da **mesma base** e dos **mesmos assets**.

## Um repositório só

Tudo mora neste repositório (`andrecanesin/catalogo-mdtech`, público): a
automação Python e o catálogo digital. O `site/` é uma pasta comum dele.

| | Raiz | `site/` |
|---|---|---|
| O que é | Projeto de automação (Python) | Catálogo digital (HTML/CSS/JS estático) |
| Quem edita | Só via `gerar.py` + módulos Python | HTML/CSS/JS editados **à mão**, direto ali |

`python gerar.py site` só escreve `produtos.json`/`meta.json`/`fotos/`/`fichas/`
**dentro de `site/`** — não existe pasta de build intermediária. Editar o front e
gerar dado são ações independentes.

**Publicação:** cada `git push` na `main` dispara o workflow **Publicar site**
(`.github/workflows/publicar.yml`), que gera as fichas e os dados e publica `site/`
no GitHub Pages. Os arquivos gerados (`site/produtos.json`, `meta.json`, `fotos/`,
`fichas/`, `catalogos/`) estão no `.gitignore` e o Actions os recria a cada
publicação. Detalhes em `DOCUMENTACAO_PROJETO.md`.

## Estrutura
```
catalogo-mdtech/
├── .github/workflows/publicar.yml   build + publicação no Pages a cada push na main
├── .claude/skills/mdtech-ui-ux/     skill de UI/UX do projeto
├── CLAUDE.md                        contexto e regras de ouro (lido pelo Claude Code)
├── dados/    Base_MDTech_Consolidada.xlsx        (fonte única da verdade)
├── assets/
│   ├── imagens/   fotos por código — em subpastas por fornecedor:
│   │   ├── TONGLU/      (Laparoscopia)
│   │   ├── TIAN_SONG/   (Urologia / Histeroscopia)
│   │   └── ASAP/        (Óticas HD-4K)
│   │   └── (fotos soltas na raiz também funcionam)
│   ├── logos/     logo-mdtech-hor-branco.png + logo-topo-reduzido.png
│   ├── fontes/    Poppins-Bold/SemiBold/Medium/Regular + IBMPlexMono-Bold/Medium/Regular
│   └── icones/angulos/   0.png, 12.png, 30.png, 70.png — selo de ângulo
├── mdtech/   CORE compartilhado (não duplicar lógica fora daqui):
│   ├── config.py  caminhos, aba da base, SITE (= raiz/site), CONTATO_URL
│   ├── marca.py   cores, accent por especialidade, fontes
│   ├── base.py    leitura da base + CONTRATO de nomes de coluna (dic COLUNAS)
│   ├── fotos.py   matcher de foto por código — RECURSIVO nas subpastas
│   ├── textos.py  limpeza de nome (CAIXA ALTA + specs → nome curto) + ícone de ângulo (base64)
│   └── layout.py  helpers de desenho + quebra de linha
├── geradores/  card.py · fichas.py · catalogo.py · dashboard.py · site.py  (só o LAYOUT)
├── saida/    PDFs e previews gerados localmente (git-ignorado, é lixeira de build)
│   ├── digital/    fichas e catálogos LEVES (foto 1200 px): é o que o site, o Actions e o servidor usam
│   └── impresso/   catálogos p/ a gráfica (foto ORIGINAL): só local, nunca publicado
├── gerar.py  CLI único
├── requirements.txt
└── site/     catálogo digital — pasta comum do repositório, front escrito à mão
    ├── PRODUCAO.md         como ligar o download dos catálogos PDF (Release)
    ├── index.html / produto.html
    ├── css/estilo.css
    ├── js/{config,dados,catalogo,produto}.js
    ├── img/angulos/        mesmos ícones de assets/icones/angulos, versão site
    ├── produtos.json / meta.json   GERADOS por `gerar.py site` — não editar à mão
    ├── fotos/              GERADO — JPEG 1600 px + thumbs/ 600 px das fotos casadas (originais ficam em assets/)
    ├── fichas/             GERADO — 1 PDF por produto (o Actions recria)
    └── catalogos/          GERADO local — PDFs grandes, nunca no git
```

**Regra de ouro**: `produtos.json`, `meta.json`, `site/fotos/`, `site/fichas/`
e `site/catalogos/` são todos **gerados**. Nunca editar à mão — a próxima
rodada de `gerar.py site` sobrescreve.

## Instalar
```
pip install -r requirements.txt
```
Requisitos: weasyprint, reportlab, pypdf, pillow, openpyxl.

## Comandos (CLI único: `gerar.py`)

| Comando | O que faz |
|---|---|
| `python gerar.py catalogo <Especialidade>` | Miolo de UMA especialidade (PDF vetorial) |
| `python gerar.py catalogo --todos` | Miolo de todas as especialidades |
| `python gerar.py fichas --codigo A153` | 1 ficha técnica (PDF) |
| `python gerar.py fichas --todos` | PDF mestre com todos os códigos (1 página cada) |
| `python gerar.py fichas --separados` | 1 PDF por código (`Ficha_<cod>_MDTech.pdf`) — é o que o botão do site usa |
| `python gerar.py card --codigo A299 --preco 5.990` | Card promocional WhatsApp (1080×1350) |
| `python gerar.py card --exemplo` | Card de exemplo |
| `python gerar.py dashboard` | Painel HTML de pendências (regerável) |
| `python gerar.py checklist` | Lista fotos casadas × faltantes no terminal |
| `python gerar.py site` | Gera `produtos.json`/`meta.json` **direto em `site/`** + copia fotos/fichas/catálogos pra lá. NÃO toca em HTML/CSS/JS. |
| `python gerar.py tudo` | **Roda tudo de uma vez:** checklist + dashboard + catálogos + fichas |

Fichas e catálogos digitais caem em `saida/digital/`; catálogos impressos, em `saida/impresso/`; previews
e dashboard, em `saida/`. O site só lê de `saida/digital/`.

### `tudo` — geração completa num comando
```
python gerar.py tudo                              # dashboard + catálogos + fichas
python gerar.py tudo --perfil impressao --paridade impar   # catálogos p/ gráfica
python gerar.py tudo --sem-fichas                 # ex.: só dashboard + catálogos
python gerar.py tudo --sem-catalogo               # ex.: só dashboard + fichas
```
Não inclui **cards** (precisam de código/preço específicos — rode `card` à
parte) nem **site** (rode `site` à parte só para conferir local; quem publica é o Actions).

**Atenção:** `tudo` gera fichas com `--todos` (o PDF mestre), **não**
`--separados`. Se o botão "Baixar ficha técnica" não aparecer no site depois
de rodar `tudo` + `site`, é por isso — rode `fichas --separados` manualmente
antes de `gerar.py site`. (No GitHub Actions isso já é feito na ordem certa.)

### Propostas básicas (kits por tipo de uso)
```
python gerar.py kits                          # todos os kits da aba KITS
python gerar.py kits --kit "Hérnia de Hiato"  # um kit
python gerar.py kits --kit "Hérnia de Hiato" --preview   # HTML no navegador, sem gerar PDF
```
Um PDF por kit em `saida/propostas/`; o Actions também os gera e `gerar.py site` os copia para `site/propostas/` e escreve
`site/propostas.json`, de onde o menu **"Catálogos e propostas"** do site monta a lista (kit novo na aba KITS = aparece sozinho).
Um PDF por kit em `saida/propostas/` (ex.: `Kit_Proposta_Basica_Hernia_de_Hiato_MDTech.pdf`). Os kits ficam na aba
**KITS** da planilha-base: `Kit` · `Grupo` · `Ordem` · `Código` · `Qtd` · `Observação` · `Preço unit. (R$)`. A proposta é uma **relação completa**: todos
os itens fazem parte do kit; `Grupo` só divide a lista em seções do PDF (ex.: Itens principais, Porta-agulhas) e `Qtd` é a
quantidade de cada item (vazio = 1). Nome, Ø, comprimento, ANVISA e foto vêm da BASE DE PRODUTOS pelo código (match exato: `A215` ≠ `A215.C`).
O preço é opcional: preenchendo `Preço unit. (R$)`, o PDF ganha as colunas de preço e o total do kit.

### Painel local (só o marketing, só nesta máquina)
```
python painel.py
```
Abre `http://127.0.0.1:8800` e faz **duas coisas**: (1) mostra **o que falta de informação** (ANVISA, foto, Ø, comprimento,
NCM, em SKUs) e abre o painel completo de pendências; (2) gera o material **impresso** (foto original) em `saida/impresso/`,
**liberado só quando a ANVISA estiver completa** (a trava vale também no servidor do painel). Escolha a montagem do catálogo:
separado (par), unificado (ímpar) ou caderno (múltiplo de 4). Propostas impressas: em desenvolvimento.
Fichas, catálogos digitais, propostas digitais e o site **não** estão no painel: o GitHub os gera e publica sozinho, e o site
é a fonte única. Só biblioteca padrão; escuta só em 127.0.0.1; não faz commit nem push.

### Preview rápido sem gerar PDF
```
python gerar.py catalogo Histeroscopia --preview   # -> saida/Preview_Catalogo_Histeroscopia.html
python gerar.py fichas --codigo A0322 --preview    # -> saida/Preview_Ficha_A0322.html
```
Abre o `.html` gerado direto no navegador, dá F5 depois de qualquer mudança
no bloco `<style>` de `_doc_html()` (dentro de `catalogo.py`/`fichas.py`).
O preview injeta um CSS equivalente ao `@page` de impressão (que o navegador
ignora) só pra essa visualização — não vai pro PDF final.

### Catálogo — dois perfis (dois trilhos, nunca misturados)

**`--perfil digital`** (padrão; tela): 1 PDF navegável, **sem páginas em branco**, com
**índice/bookmarks** (especialidade → família), **foto reduzida (1200 px)** e **link de contato** clicável
(opcional, via `CONTATO_URL` em `config.py`). Sai em `saida/digital/`. O catálogo **completo** (montado por
`gerar.py site`) leva a capa `assets/capas/Catalogo_Completo.pdf` + todos os miolos; os catálogos por linha saem só
com miolo e índice (capa de cada linha: colocar em `assets/capas/<Especialidade>.pdf` quando existir).
```
python gerar.py catalogo --todos --perfil digital
python gerar.py catalogo Laparoscopia --perfil digital
```

**`--perfil impressao`** (gráfica, frente e verso): 1 PDF por especialidade, com **foto ORIGINAL**
(alta resolução) e **paridade** para encaixar capa/contra sem desalinhar. Sai em `saida/impresso/`,
**só local**: nunca vai ao site, ao Actions nem ao git. Fichas só existem no digital.

| Cenário | Montagem | Miolo | Flag |
|---|---|---|---|
| Separado | capa + miolo + contracapa | PAR | `--paridade par` |
| Unificado | capa_geral + (capa_espec + miolo)×N + contra | ÍMPAR | `--paridade impar` |
| Caderno | múltiplo de 4 | — | `--paridade mult4` |
```
python gerar.py catalogo Laparoscopia --perfil impressao --paridade par
python gerar.py catalogo --todos --perfil impressao --paridade impar
```
Só o **miolo** sai do Python. Capa, contracapa, divisórias, CMYK, sangria e
marcas de corte = InDesign.

### Card — flags
`--codigo` `--titulo` `--specs` `--preco` `--anvisa` `--hero` `--hero-extra`
`--nota` `--saida` `--exemplo`.
```
python gerar.py card --codigo A299 --preco 5.990 --hero A299-3__2_.png
```

### Site — gerando os dados do catálogo digital

HTML/CSS/JS ficam **em `site/`, editados ali mesmo, à mão** — não existe
lugar separado pra "fonte" do front. `python gerar.py site` **não gera nem
copia HTML**: ele só escreve `produtos.json`, `meta.json` e copia as fotos/
fichas/catálogos casados por código, tudo direto dentro de `site/`.
```
python gerar.py site
```
Pra conferir local: `fichas --separados`, `site`, e depois `python -m http.server`
dentro de `site/`. Os arquivos gerados não vão pro git; quem publica é o Actions
(ver "Fluxo de produção").

## Fotos por código — subpastas (recursivo)

O matcher (`mdtech/fotos.py`) varre `assets/imagens/` **e todas as subpastas**
(`TONGLU`, `TIAN_SONG`, `ASAP`, ou fotos soltas na raiz). **O código é a chave
única** — não importa em qual subpasta a foto está; pode reorganizar as pastas à
vontade sem tocar no código.

O matcher é **tolerante**: ignora caixa (`a153` = `A153`), sufixo `.C` de
autoclavável ausente no arquivo, espaços e variações de traço/ponto.
Ex.: o código `A153.C` casa com `A153.jpg`, `a153.png`, `A153.C.jpeg`…

Se o mesmo código existir em 2 subpastas, vence a 1ª em ordem alfabética de
caminho (determinístico). `fotos.subpasta(codigo)` diz **onde** a foto foi achada
— útil para detectar foto no fornecedor errado.

## Diâmetro: mm × Fr

A base tem **duas colunas de diâmetro**: `Ø (mm)` e `Ø (Fr)`. Laparoscopia e
endoscópios são sempre mm; **pinças e camisas de Urologia/Histeroscopia são
medidas em Fr (French)**, não mm — confirmado item a item contra os catálogos
dos fornecedores.

**Nunca leia a coluna `diametro` direto num gerador novo.** Use
`mdtech.textos.diametro_fmt(item)`, que decide sozinho: usa mm se preenchido,
senão usa Fr, formatando como `"16,5 Fr"` ou `"5 mm"`. Fichas, catálogo e site
já usam essa função — qualquer material novo deve fazer o mesmo, senão volta
a tratar Fr como se fosse mm.

## Campos faltando = VERMELHO

Em **fichas** e **catálogo**, todo campo pendente aparece destacado em
**vermelho** (`#E06666`), não mais como traço cinza:
- **Ø, Comprimento, Ângulo, Família** ausentes → `—` vermelho.
- **ANVISA** sem número → "em registro" em vermelho.
- **Foto** ausente → caixa com borda tracejada vermelha + "sem foto".

O **dashboard** (`gerar.py dashboard`) mostra o mapa completo do que falta
(Foto / Ø / Comprimento / NCM / ANVISA) por produto e por fornecedor, com listas
expansíveis e export CSV.

## Selo de ângulo — regra final

Aparece em qualquer item cujo campo **Ângulo esteja preenchido E a família
NÃO contenha "Pinça"** — cobre endoscópios/ressectoscópios/cistoscópios de
qualquer especialidade, exclui a exceção real (pinça Mixter 90° de
Laparoscopia, onde "ângulo" é geometria da ponta, não vista de lente). Ícone
= arquivo nomeado pelo número de graus (`assets/icones/angulos/30.png`,
`site/img/angulos/30.png`). Hoje cobre 0°, 12°, 30°, 70°.

## Regras de ouro (o que mantém a organização)
1. **A base é a única fonte da verdade.** Editar ANVISA/NCM/specs só nela.
2. **Nomes de coluna moram em `mdtech/base.py` (dic COLUNAS).** Mudou a base?
   Ajusta só ali — os geradores continuam lendo por chave canônica. Inclui
   `diametro` (Ø mm) e `diametro_fr` (Ø Fr) — veja seção "Diâmetro: mm × Fr".
3. **Identidade só em `mdtech/marca.py`.** Trocou cor/fonte? Reflete em tudo
   (`site/js/config.js` tem a cor por especialidade como espelho manual).
4. **Foto = arquivo nomeado pelo código** em `assets/imagens/` (em qualquer subpasta).
5. **HTML/CSS/JS do site = só em `site/`, editados à mão.** `gerar.py site`
   nunca escreve HTML/CSS/JS — só dados. Não crie lógica de template em
   `geradores/site.py`.
6. Cada gerador em `geradores/` cuida **apenas do layout** — nada de reler base
   ou reimplementar matcher.
7. **Não editar arquivos gerados à mão.** Não commitar PDF grande (GitHub bloqueia
   > 100 MB): catálogos em PDF são gerados local e sobem como Release (`site/PRODUCAO.md`).

## Fluxo de produção
1. Editar a base (`dados/Base_MDTech_Consolidada.xlsx`) e/ou o HTML/CSS/JS de `site/`.
2. Colocar fotos em `assets/imagens/<FORNECEDOR>/` (nome = código).
3. `python gerar.py checklist` (ou `dashboard`) → ver o que falta.
4. (Opcional) conferir local: `python gerar.py fichas --separados && python gerar.py site`,
   depois `python -m http.server` dentro de `site/`. Materiais impressos:
   `catalogo --todos --perfil digital` / `card`.
5. Na raiz: `git status` (nenhum PDF nem arquivo gerado na lista), `git add`,
   `git commit`, `git push origin main`.
6. Abrir a aba **Actions** do GitHub: o workflow **Publicar site** deve terminar verde.
   Só então o Pages está atualizado. Se ficar vermelho, abrir o passo com erro e ler o log.
