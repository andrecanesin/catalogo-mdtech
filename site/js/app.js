/* App (PWA) do lado da página: aviso de conexão, convite para instalar (só vendedores conectados) e fotos para usar sem internet.
   O service worker (sw.js) é registrado em dados.js; aqui só a parte que o vendedor vê. Criado via JS: não depende de markup fixo. */
(function () {
  const ls = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sem armazenamento */ } }
  };
  const instalado = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  // ---------- 1) faixa de conexão, dentro do topo (fixo): não cobre nada, empurra o conteúdo ----------
  // sem internet: azul bem claro, fica enquanto durar; conexão de volta / pedido enviado: azul MDTech, some sozinha
  const ICONE_FAIXA = {
    off: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M7 18h10a4 4 0 0 0 .9-7.9A6 6 0 0 0 6.3 9 4.5 4.5 0 0 0 7 18z"/><path d="M3 3l18 18"/></svg>',
    on: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
  };
  let faixa = null, tempo = null;
  function mostrarFaixa(texto, tipo, ms) {
    if (!faixa) {
      faixa = document.createElement("div");
      faixa.className = "app-faixa"; faixa.setAttribute("role", "status"); faixa.setAttribute("aria-live", "polite");
      const topo = document.querySelector("header.top");
      if (topo) topo.appendChild(faixa); else document.body.prepend(faixa);
    }
    faixa.innerHTML = ICONE_FAIXA[tipo] + "<span></span>";
    faixa.querySelector("span").textContent = texto;
    faixa.dataset.tipo = tipo; faixa.hidden = false;
    clearTimeout(tempo);
    if (ms) tempo = setTimeout(() => { faixa.hidden = true; }, ms);
  }
  function dataCatalogo() {
    const t = Number(ls.get("mdtech_catalogo_em"));
    return t ? new Date(t).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : "";
  }
  function semInternet() {
    if (navigator.onLine) return;
    const d = dataCatalogo();
    mostrarFaixa("Sem internet" + (d ? " · catálogo de " + d : ""), "off");
  }
  window.addEventListener("offline", semInternet);
  window.addEventListener("online", async () => {
    mostrarFaixa("Conectado · catálogo atualizado", "on", 4000);   // antes: o aviso de pedido enviado (se houver) vem depois
    try { await fetch("produtos.json", { cache: "no-store" }); ls.set("mdtech_catalogo_em", String(Date.now())); } catch (e) { /* ainda instável */ }
    guardarFotos();
  });
  document.addEventListener("envios:enviados", e => {
    const n = (e.detail && e.detail.n) || 1;
    mostrarFaixa(n === 1 ? "Pedido guardado sem internet: enviado" : n + " pedidos guardados sem internet: enviados", "on", 5000);
  });
  document.addEventListener("DOMContentLoaded", semInternet);

  // ---------- 2) fotos para usar sem internet (~5 MB): só vendedor ou app instalado (clientes não baixam tudo à toa) ----------
  async function guardarFotos() {
    if (!("serviceWorker" in navigator) || !navigator.onLine) return;
    if (!((window.MD && MD.ehVendedor && MD.ehVendedor()) || instalado())) return;
    try {
      const prod = await (await fetch("produtos.json")).json();
      const urls = [];
      prod.forEach(p => { if (p.foto_thumb) urls.push(p.foto_thumb); if (p.foto) urls.push(p.foto); });
      const reg = await navigator.serviceWorker.ready;
      if (reg.active) reg.active.postMessage({ tipo: "fotos", urls });
    } catch (e) { /* tenta de novo na próxima visita */ }
  }
  window.addEventListener("load", () => setTimeout(guardarFotos, 3000));

  // ---------- 3) convite para instalar: só vendedor conectado; "Agora não" esconde por 30 dias; some se já instalado ----------
  let pedido = null, vendedor = false;
  window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); pedido = e; convidar(); });
  window.addEventListener("appinstalled", () => { fechar(); pedido = null; });
  document.addEventListener("conta:pronta", e => { vendedor = !!(e.detail && e.detail.status === 200); convidar(); });

  // Celular e tablet (toque, sem mouse). No computador o convite não aparece: lá fica só o botão de instalar do próprio navegador.
  // (alguns Android, ex.: Samsung, dizem ter "hover"; por isso vale também o aparelho se identificar como celular/tablet)
  const movel = () => window.matchMedia("(hover: none) and (pointer: coarse)").matches || ios
    || !!(navigator.userAgentData && navigator.userAgentData.mobile) || /Android|Mobi|iPhone|iPad|iPod/i.test(navigator.userAgent);
  function convidar() {
    if (!vendedor || !movel() || instalado() || document.querySelector(".app-convite")) return;
    if (Date.now() < Number(ls.get("mdtech_instalar_depois") || 0)) return;
    const tipo = pedido ? "android" : ios ? "ios" : "";
    if (tipo) setTimeout(() => { if (!document.querySelector(".app-convite") && !instalado()) montar(pedido ? "android" : tipo); }, 1200);
    else if (android && !esperandoMenu) {
      // Android sem o aviso "dá para instalar" do navegador (ex.: Samsung Internet, que não o envia): depois de alguns segundos,
      // mostra o passo a passo pelo menu do próprio navegador. Se o aviso chegar antes, vale o botão "Instalar o app".
      esperandoMenu = true;
      setTimeout(() => {
        if (pedido || document.querySelector(".app-convite") || instalado()) return;
        if (Date.now() < Number(ls.get("mdtech_instalar_depois") || 0)) return;
        montar(/SamsungBrowser/i.test(navigator.userAgent) ? "samsung" : "menu");
      }, 8000);
    }
  }
  const android = /Android/i.test(navigator.userAgent);
  let esperandoMenu = false;
  let soltarFoco = null, focoAntes = null;
  function fechar() {
    const c = document.querySelector(".app-convite");
    if (!c) return;
    c.remove();
    document.documentElement.classList.remove("app-conv-aberto");
    if (soltarFoco) { soltarFoco(); soltarFoco = null; }
    if (focoAntes && focoAntes.focus) focoAntes.focus();
  }
  const adiar = () => { ls.set("mdtech_instalar_depois", String(Date.now() + 30 * 864e5)); fechar(); };

  // ícones em linha (traço, herdam a cor do texto)
  const svg = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICONE = {
    ok: svg('<path d="M5 12.5l4.5 4.5L19 7.5"/>'),
    compartilhar: svg('<path d="M12 3v12M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/>'),
    adicionar: svg('<rect x="3.5" y="3.5" width="17" height="17" rx="4"/><path d="M12 8v8M8 12h8"/>')
  };

  // Convite em tela cheia: fundo azul claro, ícone do app, o que ganha e como instalar (Android: botão; iPhone: passo a passo).
  function montar(tipo) {
    focoAntes = document.activeElement;
    const c = document.createElement("div");
    c.className = "app-convite"; c.setAttribute("role", "dialog"); c.setAttribute("aria-modal", "true");
    c.setAttribute("aria-labelledby", "app-conv-t"); c.setAttribute("aria-describedby", "app-conv-d");
    const PASSOS = {
      ios: [`Toque em <b>Compartilhar</b> <i>${ICONE.compartilhar}</i> na barra do Safari`,
            `Escolha <b>Adicionar à Tela de Início</b> <i>${ICONE.adicionar}</i>`, "Toque em <b>Adicionar</b>, no canto de cima"],
      samsung: ["Toque no menu <b>☰</b>, na barra de baixo", "Escolha <b>Adicionar página a</b> e depois <b>Tela inicial</b>",
                "Confirme em <b>Adicionar</b>"],
      menu: ["Toque no menu <b>⋮</b>, no canto de cima", "Escolha <b>Instalar app</b> ou <b>Adicionar à tela inicial</b>",
             "Confirme em <b>Instalar</b>"]
    };
    const LISTA = `<ul class="app-conv-lista">
          <li><i>${ICONE.ok}</i>Catálogo, fotos e busca sem internet</li>
          <li><i>${ICONE.ok}</i>Preços de tabela à mão, também offline</li>
          <li><i>${ICONE.ok}</i>Atualiza sozinho quando conecta</li>
        </ul>`;
    c.innerHTML = `
      <button type="button" class="app-conv-x" aria-label="Fechar">${svg('<path d="M6 6l12 12M18 6L6 18"/>')}</button>
      <div class="app-conv-corpo">
        <img class="app-conv-ic" src="img/app/icone-192.png" alt="" width="96" height="96">
        <p class="app-conv-sobre">App MDTech · vendedores</p>
        <h2 id="app-conv-t">Leve o catálogo<br>no seu celular</h2>
        <p class="app-conv-sub" id="app-conv-d">Abre direto da tela inicial, como um app, e funciona mesmo sem internet.</p>
        ${PASSOS[tipo] ? "" : LISTA}
        ${PASSOS[tipo] ? `<ol class="app-conv-passos" aria-label="Como instalar">${PASSOS[tipo].map((t, i) =>
          `<li><span class="n">${i + 1}</span><span>${t}</span></li>`).join("")}</ol>` : ""}
        ${PASSOS[tipo] ? LISTA : ""}
      </div>
      <div class="app-conv-acoes">
        ${tipo === "android" ? '<button type="button" class="app-instalar">Instalar o app</button>' : '<button type="button" class="app-ok">Entendi</button>'}
        <button type="button" class="app-depois">Agora não</button>
      </div>`;
    document.body.appendChild(c);
    document.documentElement.classList.add("app-conv-aberto");
    c.querySelector(".app-depois").onclick = adiar;
    c.querySelector(".app-conv-x").onclick = adiar;
    const ok = c.querySelector(".app-ok"); if (ok) ok.onclick = adiar;
    const bt = c.querySelector(".app-instalar");
    if (bt) bt.onclick = async () => {
      if (!pedido) return fechar();
      pedido.prompt();
      try { await pedido.userChoice; } catch (e) { /* ok */ }
      pedido = null; fechar();
    };
    c.addEventListener("keydown", e => { if (e.key === "Escape") adiar(); });
    if (window.MD && MD.prenderFoco) soltarFoco = MD.prenderFoco(c);
    (bt || ok).focus({ preventScroll: true });   // foco no botão principal, mas a tela começa no topo (ícone e título)
    c.scrollTop = 0;
  }
})();
