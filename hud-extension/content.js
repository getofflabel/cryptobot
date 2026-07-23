// content.js — the floating panel. Ticks the live BloFin price every 2s and
// does the P&L / distance math locally so the money moves with the market.
// The bot's STATE (position levels, what it's waiting for) refreshes every 10s.

(function () {
  if (window.__cryptobotHud) return;
  window.__cryptobotHud = true;

  const PRICE_MS = 2000;
  const STATE_MS = 10000;
  const STALE_MS = 5 * 60 * 1000;

  const el = document.createElement("div");
  el.id = "cbhud";
  el.innerHTML = `
    <div id="cbhud-head">
      <span class="cbhud-live"><span class="cbhud-dot"></span>CRYPTOBOT</span>
      <span id="cbhud-mkt" class="cbhud-mkt"></span>
      <span id="cbhud-collapse" title="collapse">‹</span>
    </div>
    <div id="cbhud-price-wrap">
      <span id="cbhud-price">—</span>
      <span id="cbhud-chg" class="cbhud-chg"></span>
    </div>
    <div id="cbhud-body"></div>`;
  document.documentElement.appendChild(el);

  chrome.storage.local.get(["cbhud_pos", "cbhud_collapsed"], (s) => {
    const p = s.cbhud_pos;
    if (p && typeof p.left === "number") {
      el.style.left = p.left + "px"; el.style.top = p.top + "px"; el.style.right = "auto";
    }
    if (s.cbhud_collapsed) el.classList.add("collapsed");
  });

  document.getElementById("cbhud-collapse").addEventListener("click", (e) => {
    e.stopPropagation();
    el.classList.toggle("collapsed");
    chrome.storage.local.set({ cbhud_collapsed: el.classList.contains("collapsed") });
  });

  // drag by header
  const head = document.getElementById("cbhud-head");
  let dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
  head.addEventListener("mousedown", (e) => {
    if (e.target.id === "cbhud-collapse") return;
    dragging = true;
    const r = el.getBoundingClientRect();
    ox = r.left; oy = r.top; sx = e.clientX; sy = e.clientY;
    el.style.right = "auto"; e.preventDefault();
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    el.style.left = Math.max(0, Math.min(window.innerWidth - 60, ox + e.clientX - sx)) + "px";
    el.style.top = Math.max(0, Math.min(window.innerHeight - 30, oy + e.clientY - sy)) + "px";
  });
  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    const r = el.getBoundingClientRect();
    chrome.storage.local.set({ cbhud_pos: { left: r.left, top: r.top } });
  });

  const $ = (id) => document.getElementById(id);
  const fmt = (n, d = 0) => (n == null ? "—" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
  const wclass = { CALM: "calm", CHOPPY: "chop", STORM: "storm" };

  let state = null;      // last bot snapshot
  let livePrice = null;  // last live tick
  let open24h = null;

  // ---- live price header ----------------------------------------------------
  function paintPrice() {
    const p = livePrice != null ? livePrice : (state && state.price);
    $("cbhud-price").textContent = p != null ? "$" + fmt(p, 0) : "—";
    const chg = $("cbhud-chg");
    if (p != null && open24h) {
      const pct = (p / open24h - 1) * 100;
      chg.textContent = (pct >= 0 ? "▲ " : "▼ ") + Math.abs(pct).toFixed(2) + "%";
      chg.className = "cbhud-chg " + (pct >= 0 ? "up" : "down");
    } else chg.textContent = "";
  }

  // ---- body: position (live P&L) or flat (what it's waiting for) ------------
  function paintBody() {
    if (!state) { $("cbhud-body").innerHTML = `<div class="cbhud-flat">connecting…</div>`; return; }
    const p = livePrice != null ? livePrice : state.price;
    const mkt = $("cbhud-mkt");
    mkt.textContent = state.market || "";
    mkt.className = "cbhud-mkt " + (wclass[state.market] || "");

    const pos = state.position;
    let html = "";
    if (pos && pos.entry) {
      // live P&L: LONG gains as price rises, SHORT as it falls
      const size = pos.contracts * pos.contract_size;
      const pnl = (p - pos.entry) * size * pos.dir;
      const pnlPct = ((p / pos.entry - 1) * 100) * pos.dir;
      const win = pnl >= 0;
      const cls = win ? "up" : "down";
      const dist = (lvl) => lvl ? (((lvl / p - 1) * 100)).toFixed(2) + "%" : "—";
      // progress entry -> target (how far along the trade is)
      let prog = 0;
      if (pos.target) {
        const span = Math.abs(pos.target - pos.entry) || 1;
        prog = Math.max(0, Math.min(100, (Math.abs(p - pos.entry) / span) * 100 * (win ? 1 : 0)));
      }
      html = `
        <div class="cbhud-postop">
          <span class="cbhud-side ${pos.dir < 0 ? "short" : "long"}">${pos.side}</span>
          <span class="cbhud-book">${pos.book}</span>
        </div>
        <div class="cbhud-pnl ${cls}">${win ? "+" : "−"}$${fmt(Math.abs(pnl), 2)}
          <span class="cbhud-pnlpct">${win ? "+" : ""}${pnlPct.toFixed(2)}%</span></div>
        <div class="cbhud-lvls">
          <div class="cbhud-lvl"><span>entry</span><b>$${fmt(pos.entry, 0)}</b></div>
          <div class="cbhud-lvl"><span>stop</span><b>$${fmt(pos.stop, 0)}</b><i>${dist(pos.stop)}</i></div>
          <div class="cbhud-lvl"><span>target</span><b>${pos.target ? "$" + fmt(pos.target, 0) : "trail"}</b><i>${dist(pos.target)}</i></div>
        </div>
        ${pos.target ? `<div class="cbhud-bar"><div class="cbhud-bar-fill ${cls}" style="width:${prog}%"></div></div>` : ""}
        <div class="cbhud-thought">${state.thought || ""}</div>`;
    } else {
      html = `<div class="cbhud-flat">FLAT · watching the tape</div><div class="cbhud-waits">`;
      (state.waiting || []).forEach((w) => {
        let extra = "";
        if (w.kind === "funding" && w.now != null) {
          const pctReady = Math.max(0, Math.min(100, (w.now / w.need) * 100));
          extra = `<div class="cbhud-mini">now ${w.now > 0 ? "+" : ""}${w.now}bp
            <div class="cbhud-pbar"><div class="cbhud-pbar-fill ${w.ready ? "on" : ""}" style="width:${pctReady}%"></div></div></div>`;
          if (w.level) {
            const above = ((p / w.level - 1) * 100);
            extra += `<div class="cbhud-mini2">price ${above >= 0 ? above.toFixed(2) + "% above" : Math.abs(above).toFixed(2) + "% below"} breakdown $${fmt(w.level, 0)}</div>`;
          }
        } else if (w.kind === "rsi_below" && w.now != null) {
          extra = `<div class="cbhud-mini">RSI3 now ${w.now} · fires under ${w.need}</div>`;
        }
        html += `<div class="cbhud-wait"><span class="cbhud-wdot ${w.ready ? "on" : ""}"></span>
          <div class="cbhud-wtxt"><b>${w.name}</b><span>${w.text}</span>${extra}</div></div>`;
      });
      html += `</div><div class="cbhud-thought">${state.thought || ""}</div>`;
    }
    // freshness
    const age = state.ts ? Date.now() - new Date(state.ts).getTime() : Infinity;
    html += age > STALE_MS
      ? `<div class="cbhud-stamp warn">⚠ bot snapshot ${Math.round(age/60000)}m old — daemon may be down</div>`
      : `<div class="cbhud-stamp">bot read ${age < 60000 ? Math.round(age/1000)+"s" : Math.round(age/60000)+"m"} ago · price live</div>`;
    el.classList.toggle("stale", age > STALE_MS);
    $("cbhud-body").innerHTML = html;
  }

  // ---- pollers --------------------------------------------------------------
  function pollPrice() {
    chrome.runtime.sendMessage({ type: "cryptobot_price" }, (r) => {
      if (chrome.runtime.lastError) return;
      if (r && r.ok && r.data && !isNaN(r.data.last)) {
        livePrice = r.data.last;
        if (r.data.open24h) open24h = r.data.open24h;
        paintPrice(); paintBody();
      }
    });
  }
  function pollState() {
    chrome.runtime.sendMessage({ type: "cryptobot_state" }, (r) => {
      if (chrome.runtime.lastError) return;
      if (r && r.ok && r.data && r.data.thought !== undefined) { state = r.data; paintPrice(); paintBody(); }
    });
  }
  pollState(); pollPrice();
  setInterval(pollPrice, PRICE_MS);
  setInterval(pollState, STATE_MS);
})();
