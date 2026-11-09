# Produção — fichas, catálogos digitais e contato

O site é publicado pelo GitHub Actions a cada push na `main` (workflow **Publicar site**,
`.github/workflows/publicar.yml`). Este arquivo diz o que o Actions já faz sozinho e o
que ainda é manual (só o WhatsApp e os catálogos impressos).

## 1) Fichas técnicas (uma por produto) — automático
O workflow roda `python gerar.py fichas --separados` e depois `python gerar.py site`, e
publica `site/fichas/` junto com o site. Nada a fazer:

- `site/fichas/` está no `.gitignore` da raiz (gerado, não vai pro git).
- O botão "Baixar ficha técnica" da página de produto usa o link local
  `fichas/<codigo>.pdf` e aparece sozinho quando o produto tem `ficha_pdf` no
  `produtos.json`.
- Se o botão sumir depois de uma publicação, abrir a aba **Actions** e ler o log do passo
  "Fichas técnicas" ou "Conferir resultado".

## 2) Catálogos digitais — automático
O workflow também roda `python gerar.py catalogo --todos --perfil digital` (foto reduzida: o catálogo
completo tem ~3 MB e os quatro por linha somam ~3 MB, em cerca de 25 s) e `gerar.py site` os copia para
`site/catalogos/`. O botão "Baixar catálogos" está ligado (`catalogosAtivo: true` em `js/config.js`):

- **Catálogo completo:** a capa (`assets/capas/Catalogo_Completo.pdf`) + os miolos de todas as linhas.
- **Catálogo por linha** (Laparoscopia, Urologia, Histeroscopia, Óticas HD-4K): miolo + índice navegável. Quando
  existir a capa de uma linha, salvar em `assets/capas/<Especialidade>.pdf` (a inclusão por linha ainda precisa
  ser ligada no gerador).
- `site/catalogos/` está no `.gitignore` (gerado). Se faltar um catálogo, a etapa "Conferir resultado" do
  workflow falha e a publicação não vai ao ar.

Os catálogos **impressos** (foto ORIGINAL, alta resolução, paridade para a gráfica) **nunca passam por aqui**: são
gerados só na sua máquina (`python painel.py`, bloco "Impresso") em `saida/impresso/`, e vão para o InDesign.

## 3) WhatsApp
`site/js/config.js` → `contato.whatsapp` está vazio. Preencher com DDI+DDD+número, só
dígitos (ex.: `"5511999998888"`), pra ativar o botão de WhatsApp na bandeja de orçamento
e na página de produto. Vazio = botão oculto.

## 4) Publicar
Na raiz do projeto:
```bash
git status
git add site/js/config.js
git commit -m "producao: catalogos e contato ativados"
git push origin main
```
Depois abrir a aba **Actions**: o workflow **Publicar site** precisa terminar verde.
Só então conferir o site no ar.
