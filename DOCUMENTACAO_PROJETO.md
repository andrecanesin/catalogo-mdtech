# MDTech — Documentação do Projeto

Documento de referência único. Escrito pra quem nunca viu o projeto conseguir
entender o todo e continuar sozinho — arquitetura, convenções, comandos,
decisões e pendências.

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

## 2. Dois repositórios git — não confundir

| | `materiais-mdtech/` (raiz) | `materiais-mdtech/site/` |
|---|---|---|
| O que é | Projeto de automação (Python) | Catálogo digital (HTML/CSS/JS estático) |
| Repo git | (ver com o André se está versionado) | **Sim** — próprio repo, raiz = essa pasta |
| GitHub | — | `github.com/andrecanesin/catalogo-mdtech` |
| Deploy | Não tem — só gera arquivo local | **GitHub Pages**, direto dessa branch |
| Quem edita | Só via `gerar.py` + os módulos Python | Pode editar HTML/CSS direto (JS com cuidado) |

**Isso importa na prática**: quando for dar `git push`, confirme em qual
pasta está (`pwd`). Historicamente a maior dor de cabeça do projeto foi
exatamente isso — tentar dar push de dentro de `site/` com caminho de fora
dele, ou vice-versa.

---

## 3. Estrutura de pastas

```
materiais-mdtech/
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
│   ├── base.py                        leitura/normalização da planilha
│   └── textos.py                      limpeza de nome de produto + ícone de ângulo (base64)
├── geradores/                         um módulo por tipo de material
│   ├── catalogo.py                    miolo do catálogo PDF (WeasyPrint)
│   ├── fichas.py                      ficha técnica PDF (WeasyPrint)
│   ├── card.py                        card de produto avulso (PIL, pra rede social)
│   ├── dashboard.py                   painel de pendências (fotos faltando, ANVISA, etc.)
│   └── site.py                        exporta a base -> site/produtos.json + copia fotos/fichas/catálogos
├── saida/                             TODO PDF gerado cai aqui (git-ignorado, é lixeira de build)
├── gerar.py                           CLI único — ponto de entrada de tudo
└── site/                              catálogo digital — REPO GIT PRÓPRIO (ver seção 2)
    ├── .gitignore                     catalogos/*.pdf e fichas/*.pdf ficam de fora (ver seção 7)
    ├── PRODUCAO.md                    checklist pra quando isso for pra produção de verdade
    ├── index.html / produto.html
    ├── css/estilo.css
    ├── js/{config,dados,catalogo,produto}.js
    ├── img/angulos/                   mesmos ícones de assets/icones/angulos, versão site
    ├── produtos.json / meta.json      GERADOS por `gerar.py site` — não editar à mão
    ├── fotos/                         GERADO — cópia das fotos casadas
    ├── fichas/                        GERADO (git-ignorado por ora) — 1 PDF por produto
    └── catalogos/                     GERADO (git-ignorado por ora) — PDFs por especialidade + completo
```

**Regra de ouro**: `produtos.json`, `meta.json`, `site/fotos/`, `site/fichas/`
e `site/catalogos/` são todos **gerados**. Nunca editar à mão — a próxima
rodada de `gerar.py site` sobrescreve.

---

## 4. Como rodar tudo

Sempre a partir da raiz `materiais-mdtech/`:

```bash
# tudo de uma vez (checklist + dashboard + catálogos + fichas)
python gerar.py tudo

# ou passo a passo:
python gerar.py checklist                    # fotos faltando
python gerar.py dashboard                     # painel de pendências (ANVISA, NCM, etc.)
python gerar.py catalogo --todos              # 1 PDF por especialidade
python gerar.py fichas --separados            # 1 PDF por produto
python gerar.py site                          # produtos.json + copia fotos/fichas/catálogos pro site/
```

**Preview rápido sem gerar PDF** (pra ajustar CSS sem esperar o WeasyPrint):
```bash
python gerar.py catalogo Histeroscopia --preview   # -> saida/Preview_Catalogo_Histeroscopia.html
python gerar.py fichas --codigo A0322 --preview    # -> saida/Preview_Ficha_A0322.html
```
Abre o `.html` gerado direto no navegador, dá F5 depois de qualquer mudança
no bloco `<style>` de `_doc_html()` (dentro de `catalogo.py`/`fichas.py`).
Isso simula a folha A4 (o `@page` do CSS de impressão é ignorado pelo
navegador, então o preview injeta um CSS equivalente só pra essa visualização
— não vai pro PDF final).

**Um catálogo/ficha específicos:**
```bash
python gerar.py catalogo Laparoscopia
python gerar.py fichas --codigo A153.C
```

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
- **PDFs pesados ficam fora do git** (ambos `catalogos/*.pdf` e
  `fichas/*.pdf`, via `.gitignore` em `site/`). Motivo: GitHub recusa
  arquivo > 100MB, e mesmo abaixo disso, PDF versionado incha o histórico
  do repo pra sempre. Ver seção 7.
- **Site é estático, sem preço.** Ação do visitante é "montar lista e pedir
  orçamento" (WhatsApp/e-mail com os códigos escolhidos), não comprar
  direto.

---

## 6. Site digital — pontos de atenção

- **Fonte da verdade de configuração**: `site/js/config.js`. Contato
  (WhatsApp/e-mail), cor por especialidade, catálogos disponíveis pra
  download, produtos por página — tudo ali, comentado.
- **`produtos.json`/`meta.json` são gerados**, não editar à mão.
- **IDs e classes no HTML são "contrato" com o JS.** Pode editar
  CSS/texto/estrutura visual livremente, mas mudar/remover um `id="..."`
  ou `class="..."` sem também mudar o JS correspondente quebra alguma
  função (geralmente sem erro visível — só para de funcionar).
- **Zoom da foto e lightbox são criados via JS** (não dependem de markup
  fixo no `produto.html`) — decisão de robustez pra não depender de HTML
  e JS ficarem sincronizados manualmente.

---

## 7. PDFs em produção — o que falta decidir

Hoje (`catalogosAtivo: false` em `config.js`) o botão "Baixar catálogos"
fica **escondido** — decisão consciente enquanto o site não está em
produção. O passo a passo completo pra ligar isso está em
**`site/PRODUCAO.md`** — não duplicar aqui, esse arquivo é a referência.
Resumo da decisão pendente: hospedar os PDFs grandes fora do git (Release
do GitHub é o caminho mais simples, sem contratar serviço novo) ou aceitar
comitar os pequenos (fichas) e manter só os catálogos fora.

---

## 8. Problemas já enfrentados (pra não repetir)

- **`git push` "trava"/não termina** → normalmente não travou, terminou com
  erro e a última linha do log tem a explicação real (ex.:
  `remote: error: File ... exceeds GitHub's file size limit`). Sempre olhar
  a última linha antes de assumir que travou.
- **PDF grande preso num commit antigo continua bloqueando push mesmo
  depois de removido num commit novo** → o git manda o histórico inteiro
  que falta, não só o último commit. Solução: `git reset --mixed
  origin/main` (mantém os arquivos no disco, desfaz só os commits locais),
  arruma o `.gitignore`/remove os PDFs do índice, `git add -A`, commita de
  novo como um commit só, limpo.
- **`python gerar.py catalogo todos`** (sem `--`) → dá erro
  "especialidade desconhecida: todos", porque `todos` é uma **flag**
  (`--todos`), não um valor posicional.
- **Botão de ficha técnica / catálogo não aparece no site** → geralmente é
  só ordem dos comandos: precisa rodar `fichas --separados` (ou
  `catalogo --todos`) **antes** de `gerar.py site`, senão `ficha_pdf` fica
  `null` pra todo mundo (comportamento esperado, não é bug).

---

## 9. Sobre esse projeto no Claude (contexto pra quem for pedir ajuda por aqui)

Esse projeto tem um arquivo `PROJETO_MDTECH_COMPLETO.md` anexado ao Project
do Claude, com um snapshot do código numa data específica. **Ele fica
desatualizado a cada mudança feita fora dessas conversas** (como as
correções manuais que você já fez direto no `catalogo.py`/`fichas.py`) — o
Claude pode se confundir se buscar informação nele sem perceber que é uma
versão antiga.

Duas opções, escolha uma:
- **Mais simples**: ignorar esse arquivo dali pra frente. Sempre anexar os
  arquivos **atuais de verdade** (do seu disco) quando pedir ajuda com algo
  específico, em vez de confiar no snapshot.
- **Mais organizado**: pedir pro Claude gerar uma versão atualizada desse
  `.md` (juntando tudo que mudou) e resubir no Project, pra ele voltar a
  ser uma referência confiável.

Esse arquivo que você está lendo agora (`DOCUMENTACAO_PROJETO.md`) é sobre
**arquitetura e decisões** (o que raramente muda) — pode ficar no Project
sem risco de ficar obsoleto rápido, ao contrário do snapshot de código.

---

## 10. Onboarding rápido — se você é a "outra pessoa"

1. Leia as seções 1–3 (o quê, onde, por quê separado em 2 repos).
2. Abra a planilha `dados/Base_MDTech_Consolidada.xlsx` — é literalmente
   tudo que existe. Mexeu nela, roda `python gerar.py tudo` e `gerar.py
   site`, tudo se atualiza sozinho.
3. Pra mexer visualmente no site, edite `site/css/estilo.css` e
   `site/index.html`/`produto.html` livremente. Pra qualquer coisa em JS,
   leia a seção 6 primeiro.
4. Pra mexer no layout dos PDFs, use `--preview` (seção 4) antes de gerar
   PDF de verdade — muito mais rápido pra iterar.
5. Antes de `git push` em qualquer um dos 2 repos, roda `git status` e
   confere se não tem PDF grande na lista de "to be committed".
