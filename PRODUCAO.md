# Checklist pra produção — ligar catálogos e fichas em PDF

Hoje (`.gitignore` do repo `site/`) os PDFs de `catalogos/` e `fichas/` ficam
**fora do git** — existem no seu disco (o `gerar.py site` continua gerando
tudo normalmente), só não são versionados/enviados pro GitHub ainda. Isso é
proposital enquanto o site não está em produção: evita o problema de arquivo
grande demais (>100MB) travando o push, e evita inchar o histórico do repo
à toa antes de precisar.

Quando for a hora de ir pra produção, siga isso:

## 1) Fichas técnicas (uma por produto — arquivos pequenos)
Essas normalmente cabem tranquilo no git (cada uma é 1 produto, 1 foto).
Confira o tamanho total antes de decidir:
```
du -sh site/fichas/
```
- **Se for uns poucos MB no total** → é só remover a linha `fichas/*.pdf`
  do `.gitignore` e commitar normal. Nada mais muda no código — o link do
  botão "Baixar ficha técnica" na página de produto já é local
  (`fichas/<codigo>.pdf`) e já funciona.
- **Se ficar grande demais** (muitas fotos de alta resolução) → mesma
  estratégia dos catálogos abaixo (hospedar fora do git).

## 2) Catálogos (arquivos grandes — GitHub barra acima de 100MB)
Esses **não devem ir pro git**, mesmo em produção — cresce o histórico do
repositório pra sempre a cada catálogo novo que você gerar. Hospede fora:

**Opção mais simples (fica tudo dentro do próprio GitHub, sem contratar nada):**
1. No repositório `catalogo-mdtech` no GitHub → aba **Releases** →
   **"Create a new release"**.
2. Anexa os PDFs de `site/catalogos/` como assets da release (aceita até 2GB
   por arquivo).
3. Copia a URL base dos assets — algo como:
   `https://github.com/andrecanesin/catalogo-mdtech/releases/download/v1/`
4. Abre `site/js/config.js` e muda só essas 2 linhas:
   ```js
   catalogosAtivo: true,
   catalogosBase: "https://github.com/andrecanesin/catalogo-mdtech/releases/download/v1/",
   ```
5. Pronto — o botão "Baixar catálogos" no topo do site liga sozinho.

**Se preferir manter local (repo pequeno, poucos catálogos, sem se importar
com o tamanho do repo):**
1. Remove `catalogos/*.pdf` do `.gitignore` e commita os PDFs normalmente.
2. Em `config.js`:
   ```js
   catalogosAtivo: true,
   catalogosBase: "catalogos/",
   ```

Toda vez que gerar um catálogo novo (`gerar.py catalogo --todos` seguido de
`gerar.py site`), é só repetir o upload como asset de uma nova release (ou
o commit, se escolheu manter local) — o resto do site não muda.

## 3) WhatsApp
`site/js/config.js` → `contato.whatsapp` está vazio. Preenche com
DDI+DDD+número, só dígitos (ex.: `"5511999998888"`) pra ativar o botão
de WhatsApp na bandeja e na página de produto.

## 4) Depois de tudo isso
```
git add .
git commit -m "produção: catálogos e fichas ativados"
git push origin main
```
