/* MDTech — configuração do front.
   PREENCHA o contato do orçamento aqui. Nada mais no site precisa ser editado. */
window.MDTECH = {
  empresa: "MDTech",
  contato: {
    // WhatsApp: só dígitos, com DDI+DDD. Ex.: "5511999998888". Deixe "" para ocultar o botão.
    whatsapp: "",
    // E-mail que recebe os pedidos de orçamento. Deixe "" para ocultar o botão.
    email: "contato@mdtechsm.com.br"
  },
  // cor de destaque por especialidade (irmã dos catálogos/fichas)
  accent: {
    "Laparoscopia":  "#36A9E1",
    "Urologia":      "#2FA9A2",
    "Histeroscopia": "#C64B8C",
    "Ginecologia":   "#C64B8C",
    "Óticas HD-4K":  "#F5A623"
  },
  // Catálogos em PDF disponíveis para download (botão "Baixar catálogos" no topo).
  //
  // ATIVAR EM PRODUÇÃO — 2 passos, é só isso:
  //   1) troque CATALOGOS_ATIVO para true
  //   2) troque CATALOGOS_BASE pela URL onde os PDFs estão hospedados:
  //        - se forem pequenos o bastante pra ir no git: "catalogos/" (pasta local, padrão)
  //        - se forem hospedados fora do repo (ex.: assets de uma Release do GitHub,
  //          por causa do limite de 100MB por arquivo): a URL completa terminando em "/",
  //          ex.: "https://github.com/andrecanesin/catalogo-mdtech/releases/download/v1/"
  //   Os nomes de arquivo abaixo (Catalogo_Completo_MDTech.pdf etc.) são exatamente
  //   o que sai de `gerar.py catalogo --todos` + `gerar.py site` — não precisa mudar,
  //   só o BASE de onde eles são servidos.
  catalogosAtivo: false,
  catalogosBase: "catalogos/",
  catalogos: [
    { nome: "Catálogo completo",   arquivo: "Catalogo_Completo_MDTech.pdf",        completo: true },
    { nome: "Laparoscopia",        arquivo: "Catalogo_Laparoscopia_MDTech.pdf" },
    { nome: "Urologia",            arquivo: "Catalogo_Urologia_MDTech.pdf" },
    { nome: "Histeroscopia",       arquivo: "Catalogo_Histeroscopia_MDTech.pdf" },
    { nome: "Óticas HD-4K",        arquivo: "Catalogo_Oticas_HD-4K_MDTech.pdf" }
  ],
  // Quantidade de produtos por página na grade (mobile-friendly).
  produtosPorPagina: 20
};
