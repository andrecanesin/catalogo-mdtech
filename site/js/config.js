/* MDTech — configuração do front.
   PREENCHA o contato do orçamento aqui. Nada mais no site precisa ser editado. */
window.MDTECH = {
  empresa: "MDTech",
  contato: {
    // WhatsApp: só dígitos, com DDI+DDD. Ex.: "5511999998888". Deixe "" para ocultar o botão.
    whatsapp: "5516997726466",
    // E-mail que recebe os pedidos de orçamento. Deixe "" para ocultar o botão.
    email: "contato@mdtechsm.com.br"
  },
  // cor de destaque por especialidade — ESPELHO MANUAL de mdtech/marca.py::ACCENT
  // (fonte única da verdade). JS não importa Python, então mudou lá, muda aqui também à mão.
  accent: {
    "Laparoscopia":  "#36A9E1",
    "Urologia":      "#2FA9A2",
    "Histeroscopia": "#C64B8C",
    "Ginecologia":   "#C64B8C",
    "Óticas HD-4K":  "#F5A623"
  },
  // variante ESCURA, só para TEXTO e para fundo de texto branco (códigos, tags, botão "No orçamento"):
  // passa no contraste AA (≥4,5:1). A cor original segue em faixas, bordas e PDFs. Só existe no site.
  accentTexto: {
    "Laparoscopia":  "#1874A1",
    "Urologia":      "#227974",
    "Histeroscopia": "#A83A74",
    "Ginecologia":   "#A83A74",
    "Óticas HD-4K":  "#996207"
  },
  // Catálogos em PDF disponíveis para download (botão "Baixar catálogos" no topo).
  //
  // Os catálogos DIGITAIS (PDF leve, foto reduzida) são gerados pelo Actions a cada publicação e
  // ficam em site/catalogos/ (não vão pro git). Por isso catalogosAtivo está ligado e a base é local.
  // Os catálogos IMPRESSOS (foto original) NUNCA entram aqui: são só locais (saida/impresso/).
  // Se um dia os PDFs forem hospedados fora do site (servidor, Release do GitHub), troque catalogosBase
  // pela URL completa terminando em "/". Os nomes de arquivo abaixo (Catalogo_Completo_MDTech.pdf etc.)
  // são exatamente o que sai de `gerar.py catalogo --todos --perfil digital` + `gerar.py site`.
  catalogosAtivo: true,
  catalogosBase: "catalogos/",
  catalogos: [
    { nome: "Catálogo completo",   arquivo: "Catalogo_Completo_MDTech.pdf",        completo: true },
    { nome: "Laparoscopia",        arquivo: "Catalogo_Laparoscopia_MDTech.pdf" },
    { nome: "Urologia",            arquivo: "Catalogo_Urologia_MDTech.pdf" },
    { nome: "Histeroscopia",       arquivo: "Catalogo_Histeroscopia_MDTech.pdf" },
    { nome: "Óticas HD-4K",        arquivo: "Catalogo_Oticas_HD-4K_MDTech.pdf" }
  ],
  // Ordem na grade quando o filtro de família está ativo: estes códigos ficam por último.
  // (A ordem da base e dos PDFs não muda; vale só para o site.)
  ultimosNaFamilia: { "Trocateres": ["A219"] },
  // Quantidade de produtos por página na grade (mobile-friendly).
  produtosPorPagina: 20,

  // Preços: vêm da coluna "Preço (R$)" da base (produtos.json). Hoje são FICTÍCIOS: o site avisa "valores ilustrativos"
  // (flag preco_ficticio de cada produto, definida por PRECOS_FICTICIOS em mdtech/config.py). mostrar:false esconde tudo.
  precos: { mostrar: true, aviso: "Valores ilustrativos, sujeitos à tabela comercial vigente." },

  // Botão "Suporte" (canto da tela): menu guiado ANTES do WhatsApp. É suporte interno do catálogo
  // (problema técnico, dúvida de uso, dado do produto, sugestão), não venda. Usa o mesmo WhatsApp do
  // contato; sem WhatsApp configurado, o botão some. Mude textos, categorias e respostas só aqui.
  suporte: {
    ativo: true,
    horario: "",     // ex.: "Seg a sex, 8h às 18h" (vazio = não mostra)
    categorias: [
      { id: "tecnico",  nome: "Problema técnico",       dica: "Algo não abre, não baixa ou não funciona" },
      { id: "uso",      nome: "Dúvida de uso",          dica: "Como usar o site, os catálogos ou as propostas" },
      { id: "dados",    nome: "Informação do produto",  dica: "Dado errado ou faltando: foto, medida, ANVISA" },
      { id: "melhoria", nome: "Sugestão de melhoria",   dica: "Uma ideia para melhorar o site ou os materiais" },
      { id: "outro",    nome: "Outro assunto",          dica: "" }
    ],
    // respostas rápidas mostradas antes de chamar no WhatsApp; cat = categorias em que aparecem ("*" = todas)
    faq: [
      { cat: ["uso", "tecnico"], p: "Como baixo a ficha técnica de um produto?",
        r: "Abra o produto e clique em “Baixar ficha técnica (PDF)”." },
      { cat: ["uso", "tecnico"], p: "Onde estão os catálogos e as propostas?",
        r: "No botão “Catálogos e propostas”, no topo de qualquer página." },
      { cat: ["uso"], p: "Como peço um orçamento?",
        r: "Clique em “+ Adicionar no orçamento” nos itens, depois em “Ver lista” e “Pedir no WhatsApp”." },
      { cat: ["uso", "tecnico"], p: "Como volto ao índice dentro do PDF do catálogo?",
        r: "Use o botão “☰ Índice” no rodapé de cada página. No catálogo completo, o botão “Todas as linhas”, no topo, leva ao índice geral." },
      { cat: ["dados"], p: "O que significa “em registro” na ANVISA?",
        r: "O registro daquele produto ainda não foi informado ou está em andamento. Aparece assim que for concluído." }
    ]
  }
};
