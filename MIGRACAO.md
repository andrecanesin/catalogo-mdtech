# Migração para repositório único (Git Bash, uma linha por vez)

Pasta do projeto: `/d/_DOING/MATERIAIS_AUTOMATIZADOS`. Hoje só o `site/` é repositório (`catalogo-mdtech`).
Depois: a raiz vira o repositório, o `site/` é uma pasta dentro dele e o histórico do site continua.

## 0. Antes de tudo
1. Backup da pasta inteira (cerca de 1 GB):
   `cp -r /d/_DOING/MATERIAIS_AUTOMATIZADOS /d/_DOING/MATERIAIS_AUTOMATIZADOS_BACKUP`
2. Nada pendente no site:
   `cd /d/_DOING/MATERIAIS_AUTOMATIZADOS/site && git status && git push origin main`
   Esperado: "working tree clean" e "Everything up-to-date" (ou o push do commit de 27/10).
3. Colocar o `repo-unico.zip` na raiz do projeto (`/d/_DOING/MATERIAIS_AUTOMATIZADOS`).

## 1. Mover o git para a raiz
```
cd /d/_DOING/MATERIAIS_AUTOMATIZADOS
mv site/.git .git
python -c "import zipfile; zipfile.ZipFile('repo-unico.zip').extractall('_pacote')"
cp -r _pacote/repo-unico/. .
rm -rf _pacote
```
Isso traz: `.github/workflows/publicar.yml`, `.gitignore`, `.claude/skills/mdtech-ui-ux/`, `CLAUDE.md` e este arquivo.
(Se perguntar sobre sobrescrever `.gitignore` ou `CLAUDE.md`, pode sobrescrever.)

## 2. Conferir antes de commitar
```
git add -A
git status --short | head -60
git status --short | grep -ci "\.pdf$"
find . -size +50M -not -path "./.git/*"
git status --short | grep -c "^R"
```
- A 3ª linha deve imprimir **0** (nenhum PDF).
- A 4ª não deve listar nenhum arquivo (nada acima de 50 MB).
- A 5ª deve ser maior que 0: são os arquivos do site que o git reconheceu como movidos para `site/` (o histórico acompanha).
- Deve aparecer `assets/imagens/...` (≈ 300 MB), `dados/Base_MDTech_Consolidada.xlsx`, `mdtech/`, `geradores/`, `gerar.py`, `requirements.txt`.
- **Não** devem aparecer `saida/`, `site/fotos/`, `site/fichas/`, `site/produtos.json`.
Se algo fugir disso, pare e me mande a saída.

## 3. Commit
```
git commit -m "reorganiza: repositorio unico (automacao + site) com publicacao por GitHub Actions"
```

## 4. Ligar a publicação por Actions (no navegador)
GitHub → repositório `catalogo-mdtech` → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Faça isso **antes** do push. O site pode ficar fora do ar por alguns minutos até o primeiro deploy.

## 5. Publicar
```
git push origin main
```
O push envia ~300 MB (fotos): pode levar alguns minutos. Olhe a **última linha** da saída (`main -> main` = ok).
Depois abra a aba **Actions**: o workflow **Publicar site** deve terminar verde. Em seguida abra o site e confira
(por exemplo, `A2101` com 7 Fr).

## Se algo falhar
- Antes do push: o backup da pasta garante que nada se perde.
- No Actions: abra o passo vermelho, copie o log e me mande.
