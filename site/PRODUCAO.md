# Produção — fichas, catálogos PDF e contato

O site é publicado pelo GitHub Actions a cada push na `main` (workflow **Publicar site**,
`.github/workflows/publicar.yml`). Este arquivo diz o que o Actions já faz sozinho e o
que ainda é manual.

## 1) Fichas técnicas (uma por produto) — automático
O workflow roda `python gerar.py fichas --separados` e depois `python gerar.py site`, e
publica `site/fichas/` junto com o site. Nada a fazer:

- `site/fichas/` está no `.gitignore` da raiz (gerado, não vai pro git).
- O botão "Baixar ficha técnica" da página de produto usa o link local
  `fichas/<codigo>.pdf` e aparece sozinho quando o produto tem `ficha_pdf` no
  `produtos.json`.
- Se o botão sumir depois de uma publicação, abrir a aba **Actions** e ler o log do passo
  "Fichas técnicas" ou "Conferir resultado".

## 2) Catálogos (arquivos grandes) — Release do GitHub, manual
Os catálogos em PDF passam de 100 MB. **Não entram no git nem são gerados no Actions**:
o GitHub barra arquivo acima de 100 MB e o histórico do repositório incharia pra sempre.
O botão "Baixar catálogos" fica escondido (`catalogosAtivo: false` em `js/config.js`) até
você ligar assim:

1. Gerar os PDFs na sua máquina, a partir da raiz do projeto:
   ```bash
   python gerar.py catalogo --todos --perfil digital
   python gerar.py site
   ```
   O primeiro comando gera os miolos em `saida/`; o segundo copia pra `site/catalogos/`
   com os nomes que o `js/config.js` espera (`Catalogo_Completo_MDTech.pdf`,
   `Catalogo_Laparoscopia_MDTech.pdf` etc.) e monta o catálogo completo. Esses são os
   arquivos a subir na release.
2. No GitHub, repositório `catalogo-mdtech` → **Releases** → **Create a new release**
   (tag, por exemplo, `catalogos-v1`).
3. Anexar os PDFs de `site/catalogos/` como assets da release (aceita até 2 GB por arquivo).
4. Copiar a URL base dos assets, algo como
   `https://github.com/andrecanesin/catalogo-mdtech/releases/download/catalogos-v1/`.
5. Em `site/js/config.js`, mudar só estas duas linhas:
   ```js
   catalogosAtivo: true,
   catalogosBase: "https://github.com/andrecanesin/catalogo-mdtech/releases/download/catalogos-v1/",
   ```
6. Commit e push na `main` (ver seção 4). O botão aparece depois do deploy.

Quando gerar catálogos novos: criar uma nova release (ou substituir os assets da atual) e,
se a tag mudou, atualizar `catalogosBase`.

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
