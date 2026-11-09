/* Botão "Suporte": menu guiado antes do WhatsApp (sem backend, funciona em qualquer hospedagem).
   Fluxo: escolher o assunto -> ver respostas rápidas -> descrever -> abrir o WhatsApp com a mensagem pronta
   (assunto, nome, descrição e contexto: página, produto, dispositivo). Textos e categorias em config.js (suporte).
   O markup é criado aqui, não depende de nada no HTML. Sem WhatsApp configurado, o botão não aparece. */
(function () {
  const C = window.MDTECH || {}, S = C.suporte || {};
  const num = ((C.contato && C.contato.whatsapp) || "").replace(/\D/g, "");
  if (S.ativo === false || !num) return;
  const esc = s => (window.MD && MD.esc) ? MD.esc(s) : String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cats = S.categorias || [], faq = S.faq || [];
  const CHAVE_NOME = "mdtech_suporte_nome";
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sem storage */ } };
  const ler = k => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };

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
        <fieldset class="sup-cats"><legend>Sobre o que é?</legend>
          ${cats.map((c, i) => `<label class="sup-cat"><input type="radio" name="sup-cat" value="${esc(c.id)}">
            <span><b>${esc(c.nome)}</b>${c.dica ? `<small>${esc(c.dica)}</small>` : ""}</span></label>`).join("")}
        </fieldset>
        <div class="sup-faq" id="sup-faq"></div>
        <label class="sup-campo">Seu nome <input id="sup-nome" type="text" autocomplete="name" placeholder="Como posso te chamar?"></label>
        <label class="sup-campo">Descreva <textarea id="sup-msg" rows="4" placeholder="Conte o que aconteceu ou o que você sugere"></textarea></label>
        <p class="sup-ctx" id="sup-ctx"></p>
        <a class="sup-go" id="sup-go" target="_blank" rel="noopener" role="button" aria-disabled="true">Enviar no WhatsApp</a>
      </div>`;
    document.body.appendChild(raiz);
    return {
      fab: raiz.querySelector("#sup-fab"), bg: raiz.querySelector("#sup-bg"), painel: raiz.querySelector("#sup-panel"),
      x: raiz.querySelector("#sup-x"), faq: raiz.querySelector("#sup-faq"), nome: raiz.querySelector("#sup-nome"),
      msg: raiz.querySelector("#sup-msg"), ctx: raiz.querySelector("#sup-ctx"), go: raiz.querySelector("#sup-go")
    };
  }

  function iniciar() {
    const e = montar();
    e.nome.value = ler(CHAVE_NOME);
    const cat = () => { const r = e.painel.querySelector('input[name="sup-cat"]:checked'); return r ? cats.find(c => c.id === r.value) : null; };

    function atualizar() {
      const c = cat(), x = contexto();
      // respostas rápidas do assunto escolhido
      const lista = c ? faq.filter(f => (f.cat || ["*"]).includes("*") || (f.cat || []).includes(c.id)) : [];
      e.faq.innerHTML = lista.length ? `<p class="sup-faq-t">Talvez já resolva:</p>` + lista.map(f =>
        `<details><summary>${esc(f.p)}</summary><p>${esc(f.r)}</p></details>`).join("") : "";
      e.ctx.textContent = "Vai junto na mensagem: " + [x.produto ? "produto " + x.produto : "", "página atual", "tipo de aparelho"].filter(Boolean).join(", ") + ".";
      const pronto = !!c && e.msg.value.trim().length > 0;
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

    let ultimo = null;
    const abrir = () => {
      ultimo = document.activeElement;
      e.painel.hidden = false; e.bg.hidden = false; e.fab.setAttribute("aria-expanded", "true");
      atualizar(); const p = e.painel.querySelector("input[type=radio]"); if (p) p.focus();
    };
    const fechar = () => {
      if (e.painel.hidden) return;
      e.painel.hidden = true; e.bg.hidden = true; e.fab.setAttribute("aria-expanded", "false");
      (ultimo && ultimo.focus ? ultimo : e.fab).focus();
    };
    e.fab.addEventListener("click", () => e.painel.hidden ? abrir() : fechar());
    e.x.addEventListener("click", fechar);
    e.bg.addEventListener("click", fechar);
    document.addEventListener("keydown", ev => { if (ev.key === "Escape") fechar(); });
    e.painel.addEventListener("change", atualizar);
    e.msg.addEventListener("input", atualizar);
    e.nome.addEventListener("input", () => { guardar(CHAVE_NOME, e.nome.value.trim()); atualizar(); });
    e.go.addEventListener("click", ev => { if (e.go.getAttribute("aria-disabled") === "true") { ev.preventDefault(); e.msg.focus(); } });
  }
  document.addEventListener("DOMContentLoaded", iniciar);
})();
