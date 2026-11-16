/* Tela de acesso dos vendedores (entrar.html): entrar, trocar a senha inicial, sair.
   Conversa com o app /conta.py (servidor/mdtech_conta). A senha nunca é guardada no navegador. */
(function () {
  const $ = id => document.getElementById(id);
  const cfg = MD.cfg.conta || {};
  const msg = $("conta-msg"), sub = $("conta-sub");
  const telas = ["f-entrar", "f-trocar", "v-conectado", "v-fora"];
  let senhaRecebida = "";           // só em memória, para o 1º acesso não pedir a senha duas vezes

  // volta=produto.html?codigo=A153 -> só endereços deste site
  function destino() {
    const v = new URLSearchParams(location.search).get("volta") || "";
    try {
      const u = new URL(v, location.href);
      if (v && u.origin === location.origin && /^[\w\-]+\.html$/.test(u.pathname.split("/").pop())) return u.pathname.split("/").pop() + u.search;
    } catch (e) { /* ignora */ }
    return "index.html";
  }
  function mostrar(id, titulo, texto) {
    telas.forEach(t => $(t).hidden = t !== id);
    if (titulo) $("conta-titulo").textContent = titulo;
    if (texto != null) sub.textContent = texto;
    sub.hidden = !sub.textContent;
  }
  function aviso(texto, ok) {
    msg.textContent = texto || ""; msg.hidden = !texto;
    msg.classList.toggle("ok", !!ok);
  }
  function ocupado(form, sim) {
    form.querySelectorAll("button[type=submit]").forEach(b => { b.disabled = sim; b.classList.toggle("carregando", sim); });
  }

  // mostrar/ocultar senha
  document.querySelectorAll(".ver-senha").forEach(b => b.addEventListener("click", () => {
    const i = $(b.getAttribute("aria-controls")), ver = i.type === "password";
    i.type = ver ? "text" : "password";
    b.textContent = ver ? "Ocultar" : "Mostrar"; b.setAttribute("aria-pressed", String(ver));
  }));

  // "Esqueceu a senha?" -> WhatsApp do marketing com a mensagem pronta (recuperação manual por enquanto)
  const wpp = (MD.cfg.contato || {}).whatsapp;
  if (wpp) {
    const p = $("ajuda-senha");
    p.innerHTML = 'Esqueceu a senha? <a target="_blank" rel="noopener">Peça uma nova ao marketing</a>.';
    p.querySelector("a").href = "https://wa.me/" + wpp + "?text=" +
      encodeURIComponent("Olá! Esqueci a senha do acesso de vendedores do catálogo MDTech. Meu e-mail: ");
  }

  function telaEntrar(texto) {
    mostrar("f-entrar", "Acesso de vendedores", "Entre com o seu e-mail para ver os preços de tabela no catálogo.");
    if (texto) aviso(texto, true);
    $("email").focus();
  }
  function telaTrocar(obrigatoria) {
    const temAtual = obrigatoria && senhaRecebida;
    $("bloco-atual").hidden = !!temAtual;
    $("atual").value = temAtual ? senhaRecebida : "";
    $("nova").value = $("nova2").value = "";
    $("bt-cancelar-troca").hidden = obrigatoria;
    mostrar("f-trocar", obrigatoria ? "Crie a sua senha" : "Trocar a senha",
      obrigatoria ? "No primeiro acesso, troque a senha que você recebeu por uma só sua." : "");
    (temAtual ? $("nova") : $("atual")).focus();
  }
  function telaConectado(email) {
    $("quem").textContent = email;
    $("bt-catalogo").href = destino();
    mostrar("v-conectado", "Acesso de vendedores", "");
  }

  $("f-entrar").addEventListener("submit", async e => {
    e.preventDefault(); aviso("");
    const email = $("email").value.trim(), senha = $("senha").value;
    if (!email || !senha) { aviso("Informe o e-mail e a senha."); (email ? $("senha") : $("email")).focus(); return; }
    ocupado(e.target, true);
    const r = await MD.contaReq("/entrar", { email, senha });
    ocupado(e.target, false);
    if (r.status !== 200) { aviso(r.dados.erro || "Não foi possível entrar. Tente de novo."); $("senha").select(); return; }
    $("senha").value = "";
    if (r.dados.trocar_senha) { senhaRecebida = senha; telaTrocar(true); return; }
    location.href = destino();
  });

  $("f-trocar").addEventListener("submit", async e => {
    e.preventDefault(); aviso("");
    const atual = $("atual").value, nova = $("nova").value, nova2 = $("nova2").value;
    if (!atual) { aviso("Informe a senha atual."); $("atual").focus(); return; }
    if (nova.length < 10) { aviso("A nova senha precisa ter pelo menos 10 caracteres."); $("nova").focus(); return; }
    if (nova !== nova2) { aviso("As duas senhas novas não são iguais."); $("nova2").focus(); return; }
    ocupado(e.target, true);
    const r = await MD.contaReq("/trocar-senha", { senha_atual: atual, nova });
    ocupado(e.target, false);
    if (r.status === 401) { senhaRecebida = ""; telaEntrar(); aviso(r.dados.erro); return; }
    if (r.status !== 200) {
      aviso(r.dados.erro || "Não foi possível salvar. Tente de novo.");
      if (/atual/i.test(r.dados.erro || "")) { $("bloco-atual").hidden = false; $("atual").value = ""; $("atual").focus(); }
      else $("nova").focus();
      return;
    }
    senhaRecebida = "";
    aviso("Senha salva. Abrindo o catálogo…", true);
    setTimeout(() => location.href = destino(), 900);
  });

  $("bt-trocar").addEventListener("click", () => { aviso(""); telaTrocar(false); });
  $("bt-cancelar-troca").addEventListener("click", async () => { aviso(""); iniciar(); });
  $("bt-sair").addEventListener("click", async () => {
    await MD.contaReq("/sair", {});
    $("email").value = ""; telaEntrar("Você saiu. Até a próxima.");
  });

  async function iniciar() {
    if (!MD.contaAtiva()) {
      const base = cfg.endereco || "/";
      $("bt-oficial").href = base + "entrar.html";
      mostrar("v-fora", "Acesso de vendedores", "");
      return;
    }
    if (!MD.ehVendedor()) { telaEntrar(); return; }
    const r = await MD.contaReq("/eu");
    if (r.status === 401) MD.esquecerVendedor();
    if (r.status === 200 && r.dados.trocar_senha) telaTrocar(true);
    else if (r.status === 200 && location.hash === "#trocar") { telaConectado(r.dados.email); telaTrocar(false); }
    else if (r.status === 200) telaConectado(r.dados.email);
    else if (r.status === 0) { telaEntrar(); aviso(r.dados.erro); }
    else telaEntrar();
  }
  iniciar();
})();
