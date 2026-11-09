# MDTech — Documentação do Projeto

Documento de referência de arquitetura e decisões. Escrito pra quem nunca viu o
projeto conseguir entender o todo e continuar sozinho. O resumo operacional que
o Claude Code lê sozinho está no `CLAUDE.md`; os comandos e flags, no `LEIA-ME.md`.

---

## 1. O que é isso

Marca própria MDTech, consolidando o catálogo de 3 fornecedores originais
(TONGLU = Laparoscopia, TIAN SONG = Urologia/Histeroscopia, ASAP = Óticas
HD-4K) numa base de dados única, que alimenta 3 saídas automatizadas:

1. **Catálogos em PDF** (um por especialidade + um completo) — pra impressão
   gráfica ou distribuição digital.
2. **Fichas técnicas em PDF** (uma por código de produto) — download
   individual no site.
3. **Site/catálogo digital** — GitHub Pages, é a ferramenta de trabalho da
   equipe comercial e o que se mostra pro cliente.

Tudo nasce de **uma única planilha** (a fonte da verdade) e um script Python
gera as 3 saídas de forma consistente — não existe edição manual duplicada
em vários lugares.

---

## 2. Um repositório só

Tudo mora em **`github.com/andrecanesin/catalogo-mdtech`** (público). O `site/` é uma
pasta comum dentro dele — não é mais um repositório separado.

| Parte | Onde | Quem edita |
|---|---|---|
| Automação (Python) | `gerar.py`, `mdtech/`, `geradores/` | Código; roda via `gerar.py` |
| Dados | `dados/Base_MDTech_Consolidada.xlsx` | Planilha, à mão |
| Catálogo digital (HTML/CSS/JS) | `site/` | À mão (JS com cuidado, ver seção 6) |
| Publicação | `.github/workflows/publicar.yml` | Só se o processo de build mudar |

Publicação: **cada `git push` na `main` dispara o workflow "Publicar site"**, que gera
os dados e as fichas e publica `site/` no GitHub Pages. Não há mais deploy direto da
pasta nem dois `git push` diferentes — a antiga dor de cabeça de "em qual pasta estou?"
acabou: o `git` é sempre o da raiz.

Os arquivos gerados (`site/produtos.json`, `site/meta.json`, `site/fotos/`,
`site/fichas/`, `site/catalogos/`) estão no `.gitignore` da raiz. Não vão pro git; o
Actions os recria a cada publicação.

---

## 3. Estrutura de pastas

```
catalogo-mdtech/
├── CLAUDE.md                          contexto lido pelo Claude Code (resumo + regras de ouro)
├── DOCUMENTACAO_PROJETO.md            este arquivo (arquitetura e decisões)
├── LEIA-ME.md                         comandos e flags do gerar.py
├── requirements.txt                   dependências Python (o Actions usa)
├── .github/workflows/publicar.yml     build + publicação no Pages a cada push na main
├── .claude/skills/mdtech-ui-ux/       skill de UI/UX do projeto
├── dados/
│   └── Base_MDTech_Consolidada.xlsx   ← A FONTE DA VERDADE. Tudo vem daqui.
├── assets/
│   ├── imagens/                       fotos dos produtos (por fornecedor, casadas por código)
│   ├── logos/                         logo MDTech (branco + colorido)
│   ├── fontes/                        Poppins + IBM Plex Mono (.ttf)
│   └── icones/angulos/                0.png, 12.png, 30.png, 70.png — selo de ângulo
├── mdtech/                            núcleo compartilhado (SEM ele nada roda)
│   ├── config.py                      todos os caminhos do projeto (editar aqui muda pra todo mundo)
│   ├── marca.py                       paleta de cor + fontes
│   ├── layout.py                      helpers de desenho (usado por card.py)
│   ├── fotos.py                       casamento tolerante de foto por código
│   ├── base.py                        leitura/normalização da planilha (contrato de colunas)
│   └── textos.py                      limpeza de nome de produto, diametro_fmt, ícone de ângulo (base64)
├── geradores/                         um módulo por tipo de material
│   ├── catalogo.py                    miolo do catálogo PDF (WeasyPrint)
│   ├── fichas.py                      ficha técnica PDF (WeasyPrint)
│   ├── card.py                        card de produto avulso (PIL, pra rede social)
│   ├── dashboard.py                   painel de pendências (fotos faltando, ANVISA, etc.)
│   └── site.py                        exporta a base -> site/produtos.json + copia fotos/fichas/catálogos
├── saida/                             PDFs/previews gerados localmente (git-ignorado)
│   ├── digital/                       fichas e catálogos leves (foto 1200 px): o que vai ao ar
│   └── impresso/                      catálogos para a gráfica (foto original): só local, nunca publicado
├── gerar.py                           CLI único — ponto de entrada de tudo
└── site/                              catálogo digital — pasta comum do repositório
    ├── PRODUCAO.md                    como ligar o download dos catálogos PDF (Release)
    ├── index.html / produto.html
    ├── css/estilo.css
    ├── js/{config,dados,catalogo,produto}.js
    ├── img/angulos/                   mesmos ícones de assets/icones/angulos, versão site
    ├── produtos.json / meta.json      GERADOS — não editar à mão, não vão pro git
    ├── fotos/                         GERADO — JPEG 1600 px (+ thumbs/ de 600 px) das fotos casadas (não vai pro git)
    ├── fichas/                        GERADO — 1 PDF por produto (não vai pro git; o Actions recria)
    └── catalogos/                     GERADO localmente — PDFs grandes, nunca no git (ver seção 7)
```

**Regra de ouro**: `produtos.json`, `meta.json`, `site/fotos/`, `site/fichas/`
e `site/catalogos/` são todos **gerados**. Nunca editar à mão — a próxima
rodada de `gerar.py site` (local ou no Actions) sobrescreve.

---

## 4. Como rodar e publicar

### Publicar (o caminho normal)
1. Editar a planilha e/ou o HTML/CSS/JS do `site/`.
2. (Opcional) conferir local — ver abaixo.
3. `git add`, `git commit`, `git push origin main`.
4. Abrir a aba **Actions** do repositório: o workflow **Publicar site** deve terminar
   verde. Só então o Pages está atualizado (leva alguns minutos). Conferir o site
   antes de dizer que está no ar.

O workflow (`.github/workflows/publicar.yml`) faz, nesta ordem: instala as bibliotecas
do WeasyPrint e o `requirements.txt` → `python gerar.py fichas --separados` →
`python gerar.py site` → confere que `produtos.json`, `fotos/` e `fichas/` não estão
vazios e que `meta.json` tem produtos e fotos → publica a pasta `site/` no Pages.
Também pode ser disparado à mão pela aba Actions (`workflow_dispatch`); a opção "Ignorar o cache" força refazer as fichas.

**Cache das fichas:** a geração das fichas (152 PDFs, ~1 min 46 s) é a etapa mais lenta. O workflow guarda a pasta `saida/`
com `actions/cache`, e a chave é o hash de `dados/Base_MDTech_Consolidada.xlsx`, `geradores/fichas.py`, `gerar.py`,
`mdtech/*.py`, `assets/**` e `requirements.txt`. Mudou só o HTML/CSS/JS do site: as fichas vêm do cache e a publicação cai
para cerca de 1 minuto. Se alguma coisa nova passar a influenciar as fichas, incluir o caminho na chave (`publicar.yml`).
O `requirements.txt` não fixa a versão do WeasyPrint: uma atualização dele só aparece nas fichas na próxima regeneração.

Configuração única do Pages: **Settings → Pages → Build and deployment → Source:
GitHub Actions**. Sem isso o workflow roda mas o site não atualiza.

### Conferir localmente (sempre a partir da raiz)
```bash
python gerar.py fichas --separados && python gerar.py site
cd site && python -m http.server       # abre http://localhost:8000
```

### Geração completa local (PDFs)
```bash
python gerar.py tudo                          # checklist + dashboard + catálogos + fichas
python gerar.py checklist                     # fotos faltando
python gerar.py dashboard                     # painel de pendências (ANVISA, NCM, etc.)
python gerar.py catalogo --todos              # 1 PDF por especialidade
python gerar.py fichas --separados            # 1 PDF por produto
python gerar.py site                          # produtos.json + copia fotos/fichas/catálogos pro site/
```
Os catálogos digitais também são gerados pelo Actions (leves). Os impressos, só local (seção 7).

### Preview rápido sem gerar PDF
Pra ajustar CSS sem esperar o WeasyPrint:
```bash
python gerar.py catalogo Histeroscopia --preview   # -> saida/Preview_Catalogo_Histeroscopia.html
python gerar.py fichas --codigo A0322 --preview    # -> saida/Preview_Ficha_A0322.html
```
Abre o `.html` gerado direto no navegador, dá F5 depois de qualquer mudança
no bloco `<style>` de `_doc_html()` (dentro de `catalogo.py`/`fichas.py`).
Isso simula a folha A4 (o `@page` do CSS de impressão é ignorado pelo
navegador, então o preview injeta um CSS equivalente só pra essa visualização
— não vai pro PDF final).

Um catálogo ou ficha específicos: `python gerar.py catalogo Laparoscopia`,
`python gerar.py fichas --codigo A153.C`.

---

## 5. Convenções e decisões (o "porquê" das coisas)

- **Campo pendente = vermelho.** Regra visual em todo lugar (PDF e site):
  ANVISA/NCM/qualquer campo vazio aparece em vermelho (`#E06666`) em vez de
  ficar em branco — ninguém esquece de preencher depois.
- **Selo de ângulo aparece em óticas/endoscópios, não em pinças.** O campo
  "Ângulo" existe pra dois sentidos diferentes: ângulo de visão de lente
  (endoscópios/ressectoscópios/cistoscópios — leva selo) e geometria da
  ponta de instrumento (ex.: pinça Mixter 90° — não leva selo). O critério
  no código é **família contém "Pinça"** → sem selo. Ver `selo_angulo_html()`
  em `catalogo.py` / `_selo_angulo_html()` em `fichas.py` / `seloAngulo()`
  em `site/js/dados.js`.
- **Ícone do selo = arquivo nomeado pelo número de graus.** `Ângulo = "30°"`
  → `assets/icones/angulos/30.png` (Python) ou `site/img/angulos/30.png`
  (site). Ângulo sem ícone correspondente simplesmente não desenha o selo
  (não quebra nada). Hoje cobre 0°, 12°, 30°, 70° — falta 90° (só 1 item na
  base tem, e é a pinça Mixter, que não leva selo mesmo — então não é
  urgente).
- **Diâmetro sempre via `mdtech.textos.diametro_fmt(item)`.** Decide sozinho
  entre mm e Fr. Nunca montar "mm" na mão.
- **Cross-listing (Uro ↔ Histero).** Um código pode aparecer em 2
  especialidades (coluna "Também em" na planilha). No site isso vira UM
  produto só com `especialidades`/`familias` em lista — a galeria mostra as
  duas tags empilhadas, e o filtro considera pertencimento a qualquer uma.
- **Nome de arquivo do catálogo.** `catalogo.py` gera
  `Miolo_Catalogo_<Especialidade>_MDTech.pdf` (é só o miolo — capa/contra
  ainda são feitas à parte, hoje no InDesign). `gerar.py site` copia pro
  site removendo o prefixo `Miolo_`.
- **Fichas técnicas com código repetido em 2 especialidades** ganham sufixo
  da especialidade no nome do arquivo pra não se sobrescreverem
  (`Ficha_<slug>_<especialidade>_MDTech.pdf`).
- **PDFs pesados nunca entram no git.** GitHub recusa arquivo > 100 MB, e
  mesmo abaixo disso, PDF versionado incha o histórico pra sempre. Fichas e
  catálogos de `site/` estão no `.gitignore` da raiz; fichas e catálogos digitais são recriados
  pelo Actions, e os impressos ficam só locais (seção 7).
- **Site é estático, sem preço.** Ação do visitante é "montar lista e pedir
  orçamento" (WhatsApp/e-mail com os códigos escolhidos), não comprar
  direto.
- **Nada sensível em repositório público.** O repositório é público: contatos de
  fornecedores, preços e documentos internos não entram nele.

---

## 6. Site digital — pontos de atenção

- **Fonte da verdade de configuração**: `site/js/config.js`. Contato
  (WhatsApp/e-mail), cor por especialidade, catálogos disponíveis pra
  download, produtos por página — tudo ali, comentado. A cor por
  especialidade é espelho manual de `mdtech/marca.py::ACCENT`.
- **`produtos.json`/`meta.json` são gerados**, não editar à mão.
- **IDs e classes no HTML são "contrato" com o JS.** Pode editar
  CSS/texto/estrutura visual livremente, mas mudar/remover um `id="..."`
  ou `class="..."` sem também mudar o JS correspondente quebra alguma
  função (geralmente sem erro visível — só para de funcionar).
- **Zoom da foto e lightbox são criados via JS** (não dependem de markup
  fixo no `produto.html`) — decisão de robustez pra não depender de HTML
  e JS ficarem sincronizados manualmente.
- **Botão "Baixar ficha técnica"** aparece quando `produtos.json` tem `ficha_pdf`
  pro item. No Actions isso é automático (o workflow gera as fichas antes de rodar
  `site`). No teste local, rodar `fichas --separados` antes de `site`.

---

## 7. Catálogos em PDF — digital (automático) e impresso (local)

As **fichas** já são geradas e publicadas pelo Actions; nada a decidir ali.

Os **catálogos digitais** (foto reduzida a 1200 px) pesam poucos MB (completo ~3 MB; Laparoscopia ~1,8 MB) e levam ~25 s,
então o Actions os gera junto com o site e o botão "Baixar catálogos" está ligado (`catalogosAtivo: true`). O completo leva
a capa de `assets/capas/Catalogo_Completo.pdf`; os por linha saem com miolo + índice.

Os **catálogos impressos** usam a foto ORIGINAL (alta resolução), ficam em `saida/impresso/` e **nunca** passam pelo Actions,
pelo site ou pelo git: são gerados só na máquina do André (`python painel.py`) e seguem para o InDesign.
Detalhes em **`site/PRODUCAO.md`**.

---

## 8. Problemas já enfrentados (pra não repetir)

- **`git push` "trava"/não termina** → normalmente não travou, terminou com
  erro e a última linha do log tem a explicação real (ex.:
  `remote: error: File ... exceeds GitHub's file size limit`). Sempre olhar
  a última linha antes de assumir que travou. O push inicial leva ~300 MB (fotos).
- **PDF grande preso num commit antigo continua bloqueando push mesmo
  depois de removido num commit novo** → o git manda o histórico inteiro
  que falta, não só o último commit. Solução: `git reset --mixed
  origin/main` (mantém os arquivos no disco, desfaz só os commits locais),
  confere o `.gitignore`, `git add -A`, commita de novo como um commit só, limpo.
  Antes de todo `git add -A`: `git status` e conferir que nenhum PDF entrou.
- **Workflow "Publicar site" fica vermelho** → abrir a aba Actions, clicar no passo
  vermelho e ler o log. Causas já vistas ou esperadas: biblioteca do WeasyPrint
  faltando, `requirements.txt` desatualizado, base com coluna renomeada (ver
  `mdtech/base.py::COLUNAS`) ou "Conferir resultado" falhando porque `fotos/` ou
  `fichas/` saiu vazio. Reproduzir local com `fichas --separados` + `site` antes de
  tentar de novo.
- **Publicar site: `build` verde, mas o `deploy` falha com "Timeout reached, aborting!"** → o Pages ficou em `syncing_files`
  por 10 min. Causa provável: artefato grande demais (as fichas embutiam a foto original e o site chegou a 158 MB). Hoje as
  fichas usam foto de 1200 px (site de ~18 MB). Re-executar o job no mesmo commit **não funciona** (o Pages guarda a
  publicação pelo SHA e ela já foi cancelada: "Deployment cancelled"); é preciso um **commit novo** na `main`.
- **Pushed e o site não mudou** → conferir se o Pages está com Source = GitHub Actions
  e se o último workflow da `main` terminou verde.
- **`python gerar.py catalogo todos`** (sem `--`) → dá erro
  "especialidade desconhecida: todos", porque `todos` é uma **flag**
  (`--todos`), não um valor posicional.
- **Botão de ficha técnica não aparece no site local** → o `fichas --separados`
  precisa rodar **antes** de `gerar.py site`, senão `ficha_pdf` fica `null` pra todo
  mundo (comportamento esperado, não é bug). No Actions a ordem já está certa.

---

## 9. Onde está o código e o contexto (pra quem for pedir ajuda ao Claude)

O repositório é a referência: código, `CLAUDE.md` (lido automaticamente pelo Claude
Code), a skill `mdtech-ui-ux` e esta documentação. Não existe mais um snapshot de
código separado — qualquer cópia fora do repositório fica desatualizada na primeira
mudança. Ao pedir ajuda, aponte os arquivos **atuais** do repositório.

Histórico de lançamento e contatos de fornecedores **não ficam no repositório**
(ele é público); estão com o André.

---

## 10. Onboarding rápido — se você é a "outra pessoa"

1. Leia as seções 1–3 (o quê, onde, como se organiza).
2. Abra a planilha `dados/Base_MDTech_Consolidada.xlsx` — é literalmente
   tudo que existe. Mexeu nela, roda `python gerar.py tudo` e `gerar.py
   site`, tudo se atualiza sozinho.
3. Pra mexer visualmente no site, edite `site/css/estilo.css` e
   `site/index.html`/`produto.html` livremente. Pra qualquer coisa em JS,
   leia a seção 6 primeiro.
4. Pra mexer no layout dos PDFs, use `--preview` (seção 4) antes de gerar
   PDF de verdade — muito mais rápido pra iterar.
5. Antes de `git push`, roda `git status` e confere que não tem PDF grande nem
   arquivo gerado na lista de "to be committed". Depois do push, acompanhe a aba
   Actions até ficar verde.
