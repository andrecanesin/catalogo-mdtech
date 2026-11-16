# Deploy no servidor (Apache, SSH)

Roda na **máquina do André** (o build interno usa `dados/precos_reais.xlsx`, que não está no git).

0. Uma vez: `python deploy/extrair_precos.py "caminho/da/sua/planilha_com_precos.xlsx"` cria `dados/precos_reais.xlsx` (fora do git).
1. `cp deploy/env.exemplo deploy/.env` e preencher `DEPLOY_PATH` (pasta pública do domínio no servidor).
2. Criar `deploy/vendedores.txt` (um e-mail por linha) e rodar `python deploy/logins.py`.
   As senhas saem em `deploy/senhas_vendedores.txt`: enviar a cada vendedor e **apagar o arquivo**.
3. `deploy/deploy.sh`. No fim ele confere que `/interno` responde 401 (pede login) e que a raiz não tem preço.

- Vendedor novo/saiu: editar `vendedores.txt`, rodar `logins.py` e `deploy.sh --so-enviar`. Nova senha de alguém: `logins.py --resetar email`.
- Exige no Apache: `AllowOverride AuthConfig` na pasta do domínio. O `.htaccess` do `/interno` só tem diretivas de login (com `Options`/`Header` o servidor dava erro 500). Se `/interno` não responder 401, o script avisa.
- Nada daqui (`.env`, `.htpasswd`, lista e senhas) vai ao git: o repositório é público.
