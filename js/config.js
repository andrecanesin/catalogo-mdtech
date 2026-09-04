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
  // Os arquivos devem estar em site/catalogos/. Deixe o array vazio para ocultar o botão.
  catalogos: [
    { nome: "Catálogo completo",   arquivo: "catalogos/Catalogo_Completo_MDTech.pdf",      completo: true },
    { nome: "Laparoscopia",        arquivo: "catalogos/Catalogo_Laparoscopia_MDTech.pdf" },
    { nome: "Urologia",            arquivo: "catalogos/Catalogo_Urologia_MDTech.pdf" },
    { nome: "Ginecologia",         arquivo: "catalogos/Catalogo_Ginecologia_MDTech.pdf" },
    { nome: "Óticas HD-4K",        arquivo: "catalogos/Catalogo_Oticas_MDTech.pdf" }
  ],
  // Quantidade de produtos por página na grade (mobile-friendly).
  produtosPorPagina: 20
};
