---
name: mdtech-ui-ux
description: Use ao criar ou alterar qualquer tela, layout, CSS, HTML ou JS do catálogo digital da MDTech (pasta site/) e o layout dos PDFs (catálogo e fichas). Garante identidade visual, tom de voz, acessibilidade e as regras de contrato HTML/JS do projeto.
---

# MDTech — UI/UX e desenvolvimento do catálogo

Ferramenta de trabalho da equipe comercial e vitrine para o cliente (hospitais, clínicas, centros cirúrgicos).
Lê `CLAUDE.md` antes de mexer em qualquer coisa. Para decisões estéticas novas, combine esta skill com `frontend-design`.

## Identidade (fonte: `mdtech/marca.py`)
- Navy `#193C6C` (títulos, cabeçalhos), Cyan `#36A9E1` (destaque/ação), texto `#232D3C`, cinza `#606C7E`, painel `#F4F7FB`, linha `#DFE6EF`.
- Cor por especialidade: Laparoscopia `#36A9E1` · Urologia `#2FA9A2` · Histeroscopia/Ginecologia `#C64B8C` · Óticas HD-4K `#F5A623`.
  Mudou aqui → mudar também `site/js/config.js` (espelho manual).
- Fontes: Poppins (texto) e IBM Plex Mono (códigos, NCM, ANVISA). Arquivos em `assets/fontes/`.
- **Campo pendente = vermelho `#E06666`** (traço vermelho, "em registro" vermelho, foto ausente com borda tracejada vermelha). Nunca deixar campo vazio em branco.

## Tom de voz
Técnico sem ser inacessível, direto sem ser frio, seguro sem ser arrogante. Evitar linguagem genérica de marketing, promessas vagas, estética "hospital genérico" e apelo emocional. Pergunta-guia: "isso abre caminhos ou cria obstáculos?"

## Regras de produto
- Site estático, **sem preço**. Ação do visitante: **"+ Adicionar no orçamento"** → estado "✓ No orçamento" → pedido por WhatsApp/e-mail com os códigos.
- Selo de ângulo só em óticas/endoscópios (família **sem** "Pinça"), só na página de detalhe do site; ícone = `img/angulos/<graus>.png`.
- Diâmetro sempre via `diametro_fmt` (mm ou Fr). Nunca montar "mm" na mão.
- Código em 2 especialidades = 1 produto com várias tags.

## Contrato HTML ↔ JS (não quebrar)
- Pode mudar CSS, texto e estrutura visual. **Não renomear/remover `id` ou `class` usados pelo JS** sem ajustar o JS junto (a falha é silenciosa).
- Lightbox/zoom é criado via JS; não depender de markup fixo.
- Não editar `produtos.json`, `meta.json`, `site/fotos/`, `site/fichas/`, `site/catalogos/` — são gerados.

## UX e acessibilidade
- Mobile primeiro (a equipe comercial usa celular): grade com paginação (`produtosPorPagina` em `config.js`), alvos de toque ≥ 44px, sem rolagem horizontal.
- Contraste AA mínimo, foco visível por teclado, `alt` nas fotos (código + nome), rótulos nos filtros.
- Estados sempre tratados: sem foto, sem ficha PDF, sem resultado de busca, WhatsApp não configurado (botão oculto).
- Desempenho: fotos `loading="lazy"`; não adicionar bibliotecas pesadas sem necessidade.

## Fluxo de trabalho
1. Layout de PDF: `python gerar.py catalogo <Esp> --preview` / `fichas --codigo X --preview` (HTML no navegador, sem gerar PDF).
2. Site: `python gerar.py fichas --separados && python gerar.py site`, depois servir `site/` (`python -m http.server`) e conferir no navegador (desktop e celular).
3. Publicar = `git push` na `main`; o GitHub Actions gera e publica. Conferir a aba Actions antes de dizer que está no ar.
