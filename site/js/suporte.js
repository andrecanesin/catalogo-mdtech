/* Botão "Suporte": menu guiado, sem sair da caixa.
   Fluxo: escolher o assunto -> ver respostas rápidas -> descrever -> ENVIAR POR E-MAIL (serviço Web3Forms, sem backend
   próprio; a chave fica em config.js, suporte.chaveEmail). O e-mail leva assunto, nome, retorno, descrição e contexto
   (página, produto, aparelho). Sem a chave, cai no modo antigo: abre o WhatsApp com a mensagem pronta.
   Com a chave, o WhatsApp vira só um link secundário. Textos e categorias em config.js (suporte).
   O markup é criado aqui, não depende de nada no HTML. Sem e-mail E sem WhatsApp configurados, o botão não aparece. */
(function () {
  const C = window.MDTECH || {}, S = C.suporte || {};
  const num = ((C.contato && C.contato.whatsapp) || "").replace(/\D/g, "");
  const chave = (S.chaveEmail || "").trim();      // envio por e-mail: ver MD.enviarEmail (dados.js)
  if (S.ativo === false || (!num && !chave)) return;
  const esc = s => (window.MD && MD.esc) ? MD.esc(s) : String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cats = S.categorias || [], faq = S.faq || [];
  // Nada é gravado no aparelho: ao enviar, o formulário é limpo e volta uma tela de confirmação.

  function contexto() {
    const q = new URLSearchParams(location.search), cod = q.get("codigo");
    const celular = window.matchMedia("(pointer:coarse)").matches || window.innerWidth < 700;
    return {
      produto: cod || "",
      pagina: (document.title || "").replace(/\s*·\s*MDTech$/, "") + " (" + location.pathname.split("/").pop() + (location.search || "") + ")",
      aparelho: (celular ? "celular" : "computador") + ", tela " + window.innerWidth + "×" + window.innerHeight
    };
  }

  function montar() {
    const raiz = document.createElement("div");
    raiz.innerHTML = `
      <button class="sup-fab" id="sup-fab" type="button" aria-haspopup="dialog" aria-expanded="false">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-width="2" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>
        Suporte</button>
      <div class="sup-bg" id="sup-bg" hidden></div>
      <div class="sup-panel" id="sup-panel" role="dialog" aria-modal="true" aria-labelledby="sup-t" hidden>
        <div class="sup-head"><strong id="sup-t">Suporte</strong>
          <button class="sup-x" id="sup-x" type="button" aria-label="Fechar suporte">×</button></div>
        <p class="sup-sub">Problemas técnicos, dúvidas de uso e sugestões de melhoria do catálogo.${S.horario ? ` <b>${esc(S.horario)}</b>` : ""}</p>
        <div id="sup-form">
        <fieldset class="sup-cats"><legend>Sobre o que é?</legend>
          ${cats.map((c, i) => `<label class="sup-cat"><input type="radio" name="sup-cat" value="${esc(c.id)}">
            <span><b>${esc(c.nome)}</b>${c.dica ? `<small>${esc(c.dica)}</small>` : ""}</span></label>`).join("")}
        </fieldset>
        <div class="sup-faq" id="sup-faq"></div>
        <label class="sup-campo">Seu nome <input id="sup-nome" type="text" autocomplete="name" placeholder="Como posso te chamar?"></label>
        <label class="sup-campo" id="sup-ret-l">Como te respondo? <input id="sup-ret" type="text" autocomplete="email" placeholder="E-mail ou telefone (opcional)"></label>
        <label class="sup-campo">Descreva <textarea id="sup-msg" rows="4" placeholder="Conte o que aconteceu ou o que você sugere"></textarea></label>
        <p class="sup-ctx" id="sup-ctx"></p>
        <p class="sup-st" id="sup-st" role="status" aria-live="polite"></p>
        <button class="sup-go sup-mail" id="sup-send" type="button" aria-disabled="true">Enviar mensagem</button>
        <a class="sup-go" id="sup-go" target="_blank" rel="noopener" role="button" aria-disabled="true">Enviar no WhatsApp</a>
        </div>
        <div id="sup-feito" class="sup-feito" hidden>
          <p class="sup-ok-t">✓ Mensagem enviada</p>
          <p id="sup-feito-t"></p>
          <button class="sup-go sup-mail" id="sup-outra" type="button">Enviar outra mensagem</button>
          <button class="sup-go sec" id="sup-fechar" type="button">Fechar</button>
        </div>
      </div>`;
    document.body.appendChild(raiz);
    return {
      fab: raiz.querySelector("#sup-fab"), bg: raiz.querySelector("#sup-bg"), painel: raiz.querySelector("#sup-panel"),
      x: raiz.querySelector("#sup-x"), faq: raiz.querySelector("#sup-faq"), nome: raiz.querySelector("#sup-nome"),
      msg: raiz.querySelector("#sup-msg"), ctx: raiz.querySelector("#sup-ctx"), go: raiz.querySelector("#sup-go"),
      ret: raiz.querySelector("#sup-ret"), retL: raiz.querySelector("#sup-ret-l"), st: raiz.querySelector("#sup-st"), send: raiz.querySelector("#sup-send"),
      form: raiz.querySelector("#sup-form"), feito: raiz.querySelector("#sup-feito"), feitoT: raiz.querySelector("#sup-feito-t"),
      outra: raiz.querySelector("#sup-outra"), fechar2: raiz.querySelector("#sup-fechar")
    };
  }

  function iniciar() {
    const e = montar();
    e.send.hidden = !chave; e.retL.hidden = !chave;     // sem chave: só o modo WhatsApp
    if (chave) { e.go.classList.add("sec"); e.go.textContent = "Prefiro falar no WhatsApp"; }
    if (chave && !num) e.go.hidden = true;
    const cat = () => { const r = e.painel.querySelector('input[name="sup-cat"]:checked'); return r ? cats.find(c => c.id === r.value) : null; };

    function atualizar() {
      const c = cat(), x = contexto();
      // respostas rápidas do assunto escolhido
      const lista = c ? faq.filter(f => (f.cat || ["*"]).includes("*") || (f.cat || []).includes(c.id)) : [];
      e.faq.innerHTML = lista.length ? `<p class="sup-faq-t">Talvez já resolva:</p>` + lista.map(f =>
        `<details><summary>${esc(f.p)}</summary><p>${esc(f.r)}</p></details>`).join("") : "";
      e.ctx.textContent = "Vai junto na mensagem: " + [x.produto ? "produto " + x.produto : "", "página atual", "tipo de aparelho"].filter(Boolean).join(", ") + ".";
      const pronto = !!c && e.msg.value.trim().length > 0;
      e.send.setAttribute("aria-disabled", pronto && !enviando ? "false" : "true");
      e.send.classList.toggle("off", !(pronto && !enviando));
      e.go.setAttribute("aria-disabled", pronto ? "false" : "true");
      e.go.classList.toggle("off", !pronto);
      if (!pronto) { e.go.removeAttribute("href"); return; }
      const nome = e.nome.value.trim();
      const texto = ["*Suporte · Catálogo MDTech*", "Assunto: " + c.nome, nome ? "Nome: " + nome : "",
        "", e.msg.value.trim(), "",
        "— Contexto —", x.produto ? "Produto: " + x.produto : "", "Página: " + x.pagina, "Aparelho: " + x.aparelho]
        .filter((l, i, a) => l !== "" || (a[i - 1] !== "" && i < a.length - 1)).join("\n");
      e.go.href = "https://wa.me/" + num + "?text=" + encodeURIComponent(texto);
    }

    let enviando = false;
    function zerar() {
      e.painel.querySelectorAll('input[name="sup-cat"]').forEach(r => { r.checked = false; });
      e.nome.value = ""; e.ret.value = ""; e.msg.value = ""; e.st.textContent = ""; e.st.className = "sup-st";
      e.form.hidden = false; e.feito.hidden = true;
    }
    async function enviar() {
      const c = cat(), x = contexto();
      if (enviando || !c || !e.msg.value.trim()) { if (!e.msg.value.trim()) e.msg.focus(); return; }
      const nome = e.nome.value.trim(), ret = e.ret.value.trim();
      const corpo = [e.msg.value.trim(), "", "— Contexto —", ret ? "Retorno: " + ret : "", x.produto ? "Produto: " + x.produto : "",
        "Página: " + x.pagina, "Aparelho: " + x.aparelho].filter((l, i, a) => l !== "" || a[i - 1] !== "").join("\n");
      enviando = true; e.st.className = "sup-st"; e.st.textContent = "Enviando…"; atualizar();
      try {
        await MD.enviarEmail({ assunto: "Suporte catálogo MDTech · " + c.nome, nome, contato: ret, corpo });
        e.feitoT.textContent = ret ? "Recebemos e vamos responder pelo contato informado."
          : "Recebemos. Como você não informou um contato de retorno, não conseguiremos responder.";
        zerar(); e.form.hidden = true; e.feito.hidden = false; e.outra.focus();
      } catch (err) {
        e.st.className = "sup-st erro";
        e.st.textContent = "Não foi possível enviar agora. Tente de novo" + (num ? " ou use o WhatsApp abaixo." : ".");
      }
      enviando = false; atualizar();
    }
    e.send.addEventListener("click", enviar);
    e.outra.addEventListener("click", () => { e.form.hidden = false; e.feito.hidden = true; atualizar(); e.painel.querySelector("input[type=radio]").focus(); });
    e.fechar2.addEventListener("click", () => fechar());

    let ultimo = null;
    const abrir = () => {
      ultimo = document.activeElement;
      e.painel.hidden = false; e.bg.hidden = false; e.fab.setAttribute("aria-expanded", "true");
      atualizar(); const p = e.painel.querySelector("input[type=radio]"); if (p) p.focus();
    };
    const fechar = () => {
      if (e.painel.hidden) return;
      e.painel.hidden = true; e.bg.hidden = true; e.fab.setAttribute("aria-expanded", "false");
      if (!e.feito.hidden) { e.form.hidden = false; e.feito.hidden = true; }
      (ultimo && ultimo.focus ? ultimo : e.fab).focus();
    };
    e.fab.addEventListener("click", () => e.painel.hidden ? abrir() : fechar());
    e.x.addEventListener("click", fechar);
    e.bg.addEventListener("click", fechar);
    document.addEventListener("keydown", ev => { if (ev.key === "Escape") fechar(); });
    e.painel.addEventListener("change", atualizar);
    e.msg.addEventListener("input", atualizar);
    e.nome.addEventListener("input", atualizar);
    e.go.addEventListener("click", ev => { if (e.go.getAttribute("aria-disabled") === "true") { ev.preventDefault(); e.msg.focus(); } });
  }
  document.addEventListener("DOMContentLoaded", iniciar);
})();
