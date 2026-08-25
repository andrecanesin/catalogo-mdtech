/* Núcleo compartilhado entre a grade e a página de produto:
   - carrega produtos.json / meta.json
   - gerencia a lista de orçamento (persistida no navegador)
   - monta a mensagem de WhatsApp / e-mail
   Sem dependências externas. */
window.MD = (function () {
  const CHAVE = "mdtech_orcamento";
  const cfg = window.MDTECH || {};
  const accent = (cfg.accent) || {};

  function corEsp(esp) { return accent[esp] || "#36A9E1"; }

  // ---- normalização p/ busca (sem acento, minúsculo) ----
  function norm(s) {
    return (s || "").toString().toLowerCase()
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  // ---- dados ----
  async function carregar() {
    const [prod, meta] = await Promise.all([
      fetch("produtos.json").then(r => r.json()),
      fetch("meta.json").then(r => r.json()).catch(() => null)
    ]);
    return { produtos: prod, meta };
  }

  // ---- lista de orçamento (localStorage) ----
  function lista() {
    try { return JSON.parse(localStorage.getItem(CHAVE)) || []; }
    catch (e) { return []; }
  }
  function salvar(arr) {
    localStorage.setItem(CHAVE, JSON.stringify(arr));
    document.dispatchEvent(new CustomEvent("orcamento:mudou", { detail: arr }));
  }
  function tem(cod) { return lista().includes(cod); }
  function alternar(cod) {
    const arr = lista(); const i = arr.indexOf(cod);
    if (i >= 0) arr.splice(i, 1); else arr.push(cod);
    salvar(arr); return arr.includes(cod);
  }
  function remover(cod) { salvar(lista().filter(c => c !== cod)); }
  function limpar() { salvar([]); }

  // ---- mensagem de orçamento ----
  function _linhas(produtos) {
    const byCod = {}; produtos.forEach(p => byCod[p.codigo] = p);
    return lista().map((c, i) => {
      const p = byCod[c];
      return p ? `${i + 1}. ${p.codigo} — ${p.nome}` : `${i + 1}. ${c}`;
    });
  }
  function texto(produtos) {
    const l = _linhas(produtos);
    return `Olá! Gostaria de um orçamento dos seguintes itens MDTech:\n\n${l.join("\n")}\n\n(${l.length} ite${l.length === 1 ? "m" : "ns"})`;
  }
  function linkWhatsApp(produtos) {
    const num = (cfg.contato && cfg.contato.whatsapp) || "";
    if (!num) return null;
    return `https://wa.me/${num}?text=${encodeURIComponent(texto(produtos))}`;
  }
  function linkEmail(produtos) {
    const mail = (cfg.contato && cfg.contato.email) || "";
    if (!mail) return null;
    const assunto = "Pedido de orçamento — Catálogo MDTech";
    return `mailto:${mail}?subject=${encodeURIComponent(assunto)}&body=${encodeURIComponent(texto(produtos))}`;
  }

  return { cfg, corEsp, norm, carregar,
           lista, tem, alternar, remover, limpar,
           texto, linkWhatsApp, linkEmail };
})();
