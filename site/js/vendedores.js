/* Gestão dos vendedores (vendedores.html), só para administradores. Conversa com /conta.py/admin/... (servidor/mdtech_conta).
   A senha inicial gerada aparece UMA vez, com atalhos para enviar ao vendedor (WhatsApp, e-mail, copiar). */
(function () {
  const $ = id => document.getElementById(id);
  const esc = MD.esc;
  const msg = $("adm-msg");
  let EU = "", ultimaMensagem = "";

  function aviso(texto, ok) {
    msg.textContent = texto || ""; msg.hidden = !texto; msg.classList.toggle("ok", !!ok);
    if (texto) msg.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  const data = t => t ? new Date(t * 1000).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
  const linkEntrar = () => location.origin + location.pathname.replace(/[^/]*$/, "") + "entrar.html";

  function mensagem(v, senha) {
    const nome = (v.nome || "").split(" ")[0];
    return `Olá${nome ? ", " + nome : ""}! Seu acesso de vendedor ao catálogo MDTech está pronto.\n\n` +
      `Entre em ${linkEntrar()}\nE-mail: ${v.email}\nSenha inicial: ${senha}\n\n` +
      `No primeiro acesso, o site pede para você criar a sua senha. Depois de entrar, os preços de tabela aparecem no catálogo.`;
  }
  function mostrarSenha(v, senha, titulo) {
    ultimaMensagem = mensagem(v, senha);
    $("senha-titulo").textContent = titulo;
    $("senha-para").innerHTML = `Para <b>${esc(v.nome ? v.nome + " · " + v.email : v.email)}</b>`;
    $("senha-valor").textContent = senha;
    $("env-wpp").href = "https://wa.me/?text=" + encodeURIComponent(ultimaMensagem);
    $("env-mail").href = "mailto:" + encodeURIComponent(v.email) + "?subject=" + encodeURIComponent("Acesso ao catálogo MDTech") +
      "&body=" + encodeURIComponent(ultimaMensagem);
    const p = $("painel-senha"); p.hidden = false; p.focus(); p.scrollIntoView({ block: "start", behavior: "smooth" });
  }
  $("env-copiar").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(ultimaMensagem); aviso("Mensagem copiada. Cole no WhatsApp ou no e-mail do vendedor.", true); }
    catch (e) { aviso("Não consegui copiar: selecione a senha e copie à mão."); }
  });
  $("env-fechar").addEventListener("click", () => {
    if (!confirm("Fechar? A senha não aparece de novo (se precisar, gere uma nova).")) return;
    $("painel-senha").hidden = true; $("senha-valor").textContent = ""; ultimaMensagem = "";
  });

  async function op(rota, corpo) {
    const r = await MD.contaReq("/admin/" + rota, corpo);
    if (r.status === 401) { location.href = "entrar.html?volta=vendedores.html"; return null; }
    if (r.status !== 200) { aviso(r.dados.erro || "Não foi possível concluir. Tente de novo."); return null; }
    return r.dados;
  }

  function cartao(v) {
    const badges = [
      v.ativo ? "" : '<span class="adm-b off">Desativado</span>',
      v.bloqueado ? '<span class="adm-b alerta">Bloqueado por tentativas</span>' : "",
      v.ativo && v.trocar_senha ? '<span class="adm-b pend">Falta criar a senha</span>' : "",
      v.admin ? '<span class="adm-b adm">Administrador</span>' : "",
      v.email === EU ? '<span class="adm-b eu">Você</span>' : ""
    ].join("");
    const acoes = [];
    if (v.ativo) acoes.push(`<button type="button" data-op="redefinir">Nova senha</button>`);
    if (v.bloqueado) acoes.push(`<button type="button" data-op="desbloquear">Desbloquear</button>`);
    if (v.email !== EU) {
      acoes.push(v.ativo ? `<button type="button" data-op="desativar" class="perigo">Desativar</button>`
                         : `<button type="button" data-op="reativar">Reativar</button>`);
      if (v.ativo) acoes.push(`<button type="button" data-op="admin">${v.admin ? "Tirar administrador" : "Tornar administrador"}</button>`);
    }
    acoes.push(`<button type="button" data-op="nome">${v.nome ? "Alterar nome" : "Pôr nome"}</button>`);
    return `<li class="adm-item${v.ativo ? "" : " inativo"}" data-email="${esc(v.email)}">
      <div class="adm-quem">${v.nome ? `<b>${esc(v.nome)}</b>` : ""}<span class="adm-email">${esc(v.email)}</span></div>
      <div class="adm-badges">${badges}</div>
      <p class="adm-acesso">${v.ultimo_login ? "Último acesso: " + data(v.ultimo_login) : "Ainda não entrou"}</p>
      <div class="adm-acoes">${acoes.join("")}</div></li>`;
  }

  let VENDEDORES = [];
  async function carregar() {
    if (!MD.contaAtiva()) {
      $("adm-sub").innerHTML = `A gestão dos vendedores funciona no endereço oficial: <a href="${esc((MD.cfg.conta || {}).endereco || "/")}vendedores.html">abrir</a>.`;
      return false;
    }
    const r = await MD.contaReq("/admin/vendedores");
    if (r.status === 401) {
      $("adm-sub").innerHTML = 'Entre com a sua conta de administrador. <a href="entrar.html?volta=vendedores.html">Entrar</a>';
      return false;
    }
    if (r.status !== 200) { $("adm-sub").textContent = ""; aviso(r.dados.erro || "Não foi possível abrir a lista."); return false; }
    EU = r.dados.eu; VENDEDORES = r.dados.vendedores;
    // ativos primeiro (quem precisa de atenção no topo), depois desativados
    const peso = v => (v.ativo ? 0 : 10) - (v.bloqueado ? 2 : 0) - (v.trocar_senha ? 1 : 0);
    VENDEDORES.sort((a, b) => peso(a) - peso(b) || a.email.localeCompare(b.email));
    $("lista").innerHTML = VENDEDORES.map(cartao).join("");
    $("lista-total").textContent = `(${VENDEDORES.filter(v => v.ativo).length} ativos)`;
    $("adm-conteudo").hidden = false;
    carregarHistorico();
    return true;
  }
  async function carregarHistorico() {
    const r = await MD.contaReq("/admin/historico");
    if (r.status !== 200) return;
    $("hist-lista").innerHTML = r.dados.historico.map(h =>
      `<li><time>${data(h.quando)}</time> <b>${esc(h.autor)}</b> ${esc(h.acao)} <b>${esc(h.alvo)}</b></li>`).join("") || "<li>Nada ainda.</li>";
  }

  $("lista").addEventListener("click", async e => {
    const b = e.target.closest("button[data-op]"); if (!b) return;
    const email = b.closest("[data-email]").dataset.email, v = VENDEDORES.find(x => x.email === email), o = b.dataset.op;
    aviso("");
    if (o === "redefinir" && !confirm(`Gerar nova senha para ${email}? A senha atual deixa de valer e ele sai dos aparelhos.`)) return;
    if (o === "desativar" && !confirm(`Desativar ${email}? Ele sai de todos os aparelhos e não entra mais.`)) return;
    if (o === "reativar" && !confirm(`Reativar ${email}? Será gerada uma senha inicial nova.`)) return;
    let corpo = { email };
    if (o === "admin") {
      if (!confirm(v.admin ? `Tirar o acesso de administrador de ${email}?` : `Tornar ${email} administrador? Ele poderá gerenciar os vendedores.`)) return;
      corpo.admin = !v.admin;
    }
    if (o === "nome") { const n = prompt("Nome do vendedor:", v.nome || ""); if (n === null) return; corpo.nome = n; }
    b.disabled = true;
    const d = await op(o, corpo);
    b.disabled = false;
    if (!d) return;
    await carregar();
    if (d.senha) mostrarSenha({ ...v, ...(corpo.nome != null ? { nome: corpo.nome } : {}) }, d.senha, o === "reativar" ? "Acesso reativado" : "Nova senha inicial");
    else aviso({ desativar: `${email} foi desativado.`, desbloquear: `${email} foi desbloqueado.`, admin: "Pronto.", nome: "Nome salvo." }[o] || "Pronto.", true);
  });

  $("f-add").addEventListener("submit", async e => {
    e.preventDefault(); aviso("");
    const email = $("add-email").value.trim(), nome = $("add-nome").value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { aviso("Informe um e-mail válido."); $("add-email").focus(); return; }
    const bt = e.target.querySelector("button[type=submit]"); bt.disabled = true; bt.classList.add("carregando");
    const d = await op("adicionar", { email, nome });
    bt.disabled = false; bt.classList.remove("carregando");
    if (!d) return;
    $("add-email").value = ""; $("add-nome").value = "";
    await carregar();
    mostrarSenha({ email: d.email, nome }, d.senha, "Vendedor cadastrado");
  });

  carregar();
})();
