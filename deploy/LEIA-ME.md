# Deploy no servidor (Apache, SSH)

Roda na **máquina do André** (o build interno usa `dados/precos_reais.xlsx`, que não está no git).

0. Uma vez: `python deploy/extrair_precos.py "caminho/da/sua/planilha_com_precos.xlsx"` cria `dados/precos_reais.xlsx` (fora do git).
1. `cp deploy/env.exemplo deploy/.env` e preencher `DEPLOY_PATH` (pasta pública do domínio no servidor).
2. Criar `deploy/vendedores.txt` (um e-mail por linha) e rodar `python deploy/logins.py`.
   As senhas saem em `deploy/senhas_vendedores.txt`: enviar a cada vendedor e **apagar o arquivo**.
3. `bash deploy/deploy.sh`. No fim ele confere que `/interno` responde 401 (pede login) e que a raiz não tem preço.

## Troca de versão e rollback (17/11)
O `deploy.sh` não sobrescreve mais a pasta pública arquivo por arquivo. A versão nova vai inteira para `~/mdtech_deploy` no servidor e
entra no lugar da atual de uma vez (`deploy/remoto.sh`, dois `mv`). Com isso:
- arquivo que deixou de ser gerado (foto, ficha) sai junto; o que **não** é gerado pelo deploy (o `.htaccess` da raiz feito à mão,
  `.well-known` do certificado) é copiado para a versão nova e aparece na saída como "mantido";
- a pasta nova herda o grupo, as permissões e a ACL da atual (sem isso o Apache poderia dar 403);
- se a conferência no ar falhar, o script **volta sozinho** para a versão anterior;
- `bash deploy/deploy.sh --voltar` volta para a versão anterior (rollback; rodar de novo volta mais uma). Ficam guardadas 2.
- `bash deploy/deploy.sh --simular` gera e envia, mostra o que a troca faria e não troca nada. **Use na primeira vez.**
- O app do login (`~/mdtech_app`) troca junto com o site; os dados (`/var/lib/mdtech`) e os preços não voltam no rollback.

## Cópia do backup fora do servidor
O servidor guarda 14 cópias diárias do banco do login (`~/backups_mdtech`). Para ter uma cópia **fora** dele: `bash deploy/baixar_backup.sh`
(baixa para `~/backups_mdtech_servidor`; rodar de vez em quando, ex.: toda semana). Guarde fora do repositório: tem e-mails e hashes de senha.

- Vendedor novo/saiu: editar `vendedores.txt`, rodar `logins.py` e `deploy.sh --so-enviar`. Nova senha de alguém: `logins.py --resetar email`.
- Exige no Apache: `AllowOverride AuthConfig` na pasta do domínio. O `.htaccess` do `/interno` só tem diretivas de login (com `Options`/`Header` o servidor dava erro 500). Se `/interno` não responder 401, o script avisa.
- Nada daqui (`.env`, `.htpasswd`, lista e senhas) vai ao git: o repositório é público.

## Login novo dos vendedores (Fase 1, substitui o Basic Auth)
O `deploy.sh` também envia o app de login (`servidor/`, ver `servidor/LEIA-ME.md`) e os preços para `/var/lib/mdtech` (fora da pasta pública),
e confere que `/conta.py/precos` responde 401 sem login. Vendedores: `ssh ... python3 mdtech_app/admin.py adicionar email`.
Enquanto o login novo não estiver testado, o `/interno` com Basic Auth (`logins.py`) continua no ar.
