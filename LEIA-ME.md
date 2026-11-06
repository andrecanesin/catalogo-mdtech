# Materiais MDTech — geração unificada

Um único projeto que gera **fichas técnicas**, **catálogos (miolo)**, **cards
promocionais**, um **dashboard de pendências** e alimenta o **catálogo digital
(site)**, tudo a partir da **mesma base** e dos **mesmos assets**.

## Dois repositórios git — não confundir

| | `materiais-mdtech/` (raiz) | `materiais-mdtech/site/` |
|---|---|---|
| O que é | Projeto de automação (Python) | Catálogo digital (HTML/CSS/JS estático) |
| Repo git próprio | — | **Sim** — GitHub Pages roda direto dessa pasta |
| Quem edita | Só via `gerar.py` + módulos Python | HTML/CSS/JS editados **à mão**, direto ali |

`site/` **não é gerado, não é copiado de lugar nenhum**. É uma pasta git de
verdade, com HTML/CSS/JS escritos à mão e versionados ali dentro. O comando
`python gerar.py site` só escreve `produtos.json`/`meta.json`/`fotos/`
**direto dentro dela** — não existe pasta de build intermediária, não existe
`site-fonte/`. Editar o front e gerar dado são duas ações independentes.

**Isso importa na prática**: antes de `git push`, confirme em qual pasta
está (`pwd`) — historicamente essa foi a maior dor de cabeça do projeto.

## Estrutura
```
materiais-mdtech/
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
├── saida/    PDFs e previews gerados (git-ignorado, é lixeira de build)
├── gerar.py  CLI único
└── site/     catálogo digital — REPO GIT PRÓPRIO, front escrito à mão
    ├── .gitignore          catalogos/*.pdf e fichas/*.pdf ficam de fora (ver PRODUCAO.md)
    ├── PRODUCAO.md         checklist pra quando isso for pra produção de verdade
    ├── index.html / produto.html
    ├── css/estilo.css
    ├── js/{config,dados,catalogo,produto}.js
    ├── img/angulos/        mesmos ícones de assets/icones/angulos, versão site
    ├── produtos.json / meta.json   GERADOS por `gerar.py site` — não editar à mão
    ├── fotos/              GERADO — cópia das fotos casadas
    ├── fichas/             GERADO (git-ignorado por ora) — 1 PDF por produto
    └── catalogos/          GERADO (git-ignorado por ora) — PDFs por especialidade + completo
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

Tudo (exceto o que vai pra `site/`) cai em `saida/`.

### `tudo` — geração completa num comando
```
python gerar.py tudo                              # dashboard + catálogos + fichas
python gerar.py tudo --perfil impressao --paridade impar   # catálogos p/ gráfica
python gerar.py tudo --sem-fichas                 # ex.: só dashboard + catálogos
python gerar.py tudo --sem-catalogo               # ex.: só dashboard + fichas
```
Não inclui **cards** (precisam de código/preço específicos — rode `card` à
parte) nem **site** (rode `site` à parte quando quiser publicar).

**Atenção:** `tudo` gera fichas com `--todos` (o PDF mestre), **não**
`--separados`. Se o botão "Baixar ficha técnica" não aparecer no site depois
de rodar `tudo` + `site`, é por isso — rode `fichas --separados` manualmente
antes de `gerar.py site`.

### Preview rápido sem gerar PDF
```
python gerar.py catalogo Histeroscopia --preview   # -> saida/Preview_Catalogo_Histeroscopia.html
python gerar.py fichas --codigo A0322 --preview    # -> saida/Preview_Ficha_A0322.html
```
Abre o `.html` gerado direto no navegador, dá F5 depois de qualquer mudança
no bloco `<style>` de `_doc_html()` (dentro de `catalogo.py`/`fichas.py`).
O preview injeta um CSS equivalente ao `@page` de impressão (que o navegador
ignora) só pra essa visualização — não vai pro PDF final.

### Catálogo — dois perfis

**`--perfil digital`** (tela): 1 PDF navegável, **sem páginas em branco**, com
**índice/bookmarks** (especialidade → família) e **link de contato** clicável
(opcional, via `CONTATO_URL` em `config.py`).
```
python gerar.py catalogo --todos --perfil digital
python gerar.py catalogo Laparoscopia --perfil digital
```

**`--perfil impressao`** (gráfica, frente e verso): 1 PDF por especialidade,
com **paridade** para encaixar capa/contra sem desalinhar.

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
Depois de rodar, confira dentro da pasta `site/` (`git status`) — é lá que
mora o repositório de verdade do catálogo digital, publicado via GitHub
Pages.

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
3. **Identidade só em `mdtech/marca.py`.** Trocou cor/fonte? Reflete em tudo.
4. **Foto = arquivo nomeado pelo código** em `assets/imagens/` (em qualquer subpasta).
5. **HTML/CSS/JS do site = só em `site/`, editados à mão.** `gerar.py site`
   nunca escreve HTML/CSS/JS — só dados. Não crie lógica de template em
   `geradores/site.py`.
6. Cada gerador em `geradores/` cuida **apenas do layout** — nada de reler base
   ou reimplementar matcher.

## Fluxo de produção
1. Editar a base (`dados/Base_MDTech_Consolidada.xlsx`).
2. Colocar fotos em `assets/imagens/<FORNECEDOR>/` (nome = código).
3. `python gerar.py checklist` (ou `dashboard`) → ver o que falta.
4. `python gerar.py catalogo --todos --perfil digital` / `fichas --separados` / `card` / `site`.
5. Dentro de `site/`: `git status`, `git add`, `git commit`, `git push`.
