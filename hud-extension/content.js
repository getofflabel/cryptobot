// content.js — the floating panel. Ticks the live price for whatever
// symbol is DETECTED on screen every 2s and does the P&L / distance math
// locally so the money moves with the market. The bot's STATE (position
// levels, what each book is waiting for) refreshes every 10s.
//
// v3 (2026-07-23): SYMBOL-AWARE. The bug this fixes: the panel used to show
// Bitcoin's price and a Bitcoin news trade while the owner was looking at
// BloFin's XAUT-USDT (gold) page. Now the panel DETECTS what's on screen
// (BloFin URL / TradingView title) and renders that symbol's own content
// from the server's state.symbols[instId] map, re-checking every 3s so an
// in-page SPA navigation (switching charts without a full page reload)
// picks it up without a refresh.

(function () {
  if (window.__cryptobotHud) return;
  window.__cryptobotHud = true;

  const PRICE_MS = 2000;
  const STATE_MS = 10000;
  const DETECT_MS = 3000;
  const STALE_MS = 5 * 60 * 1000;

  // instId -> display name, used only if the server snapshot hasn't caught
  // up yet (state.symbols missing that key) — the server is the source of
  // truth for display names once it responds.
  const DISPLAY_FALLBACK = {
    "BTC-USDT": "Bitcoin", "XAUT-USDT": "Gold", "ETH-USDT": "Ethereum",
    "SOL-USDT": "Solana", "TSLA-USDT": "Tesla",
  };
  // Rough price precision per symbol — BTC/gold move in whole dollars on
  // this panel, SOL/TSLA are cheap enough that whole dollars hides the move.
  const PRICE_DECIMALS = {
    "BTC-USDT": 0, "XAUT-USDT": 1, "ETH-USDT": 1, "SOL-USDT": 2, "TSLA-USDT": 2,
  };

  const el = document.createElement("div");
  el.id = "cbhud";
  el.innerHTML = `
    <div id="cbhud-head">
      <span class="cbhud-live"><span class="cbhud-dot"></span>CRYPTOBOT</span>
      <span id="cbhud-sym" class="cbhud-sym"></span>
      <span id="cbhud-mkt" class="cbhud-mkt"></span>
      <span id="cbhud-collapse" title="collapse">‹</span>
    </div>
    <div id="cbhud-price-wrap">
      <span id="cbhud-price">—</span>
      <span id="cbhud-chg" class="cbhud-chg"></span>
      <span id="cbhud-delayed" class="cbhud-delayed" style="display:none">delayed</span>
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

  // ---- symbol detection -------------------------------------------------
  // BloFin: any [A-Z0-9]{2,10}-USDT token anywhere in the URL — covers
  // both /futures/BTC-USDT style paths and demo-host variants we haven't
  // inventoried by hand. Falls back to the same token pattern in the page
  // title if the URL doesn't carry it.
  const SYMBOL_TOKEN_RE = /\b([A-Z0-9]{2,10}-USDT)\b/i;

  function detectFromBlofin() {
    let m = location.href.match(SYMBOL_TOKEN_RE);
    if (m) return m[1].toUpperCase();
    m = (document.title || "").match(SYMBOL_TOKEN_RE);
    if (m) return m[1].toUpperCase();
    return null;
  }

  // TradingView: the leading symbol in document.title, e.g. "BTCUSDT",
  // "XAUUSD", "TSLA". Mapped by prefix since TradingView's own suffix
  // varies (USD vs USDT vs nothing for a stock ticker).
  function mapTradingViewToken(tok) {
    if (!tok) return null;
    tok = tok.toUpperCase();
    if (tok.startsWith("BTCUSD")) return "BTC-USDT";
    if (tok.startsWith("XAU")) return "XAUT-USDT";
    if (tok.startsWith("ETH")) return "ETH-USDT";
    if (tok.startsWith("SOL")) return "SOL-USDT";
    if (tok.startsWith("TSLA")) return "TSLA-USDT";
    return null;
  }

  function detectFromTradingView() {
    const m = (document.title || "").match(/^\s*([A-Z0-9]{2,10})/i);
    if (!m) return null;
    return mapTradingViewToken(m[1]);
  }

  function detectSymbol() {
    const host = location.hostname;
    let instId = null;
    if (host.includes("blofin.com")) {
      instId = detectFromBlofin();
    } else if (host.includes("tradingview.com")) {
      instId = detectFromTradingView();
    }
    if (!instId) return { instId: "BTC-USDT", hint: "showing Bitcoin" };
    return { instId, hint: null };
  }

  let detected = detectSymbol();

  // ---- live state --------------------------------------------------------
  let state = null;          // last bot snapshot
  let livePrice = null;      // last live tick, FOR THE CURRENTLY DETECTED SYMBOL ONLY
  let open24h = null;
  let priceDelayed = false;  // true when the last fetch couldn't get a fresh tick

  function currentSymbolData() {
    return (state && state.symbols && state.symbols[detected.instId]) || null;
  }

  function displayName() {
    const sd = currentSymbolData();
    return (sd && sd.display) || DISPLAY_FALLBACK[detected.instId] || detected.instId;
  }

  function fmtLocalTime(iso) {
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    } catch (_) { return null; }
  }

  // ---- live price header ----------------------------------------------------
  function paintPrice() {
    $("cbhud-sym").textContent = "· " + displayName();

    // Never fall back to a DIFFERENT symbol's price — that is the exact bug
    // this rewrite fixes. Only BTC-USDT has a same-symbol server fallback
    // (the legacy top-level state.price); everything else shows "—" until
    // its own live tick arrives.
    let p = livePrice;
    if (p == null && detected.instId === "BTC-USDT" && state) p = state.price;

    $("cbhud-price").textContent = p != null ? "$" + fmt(p, PRICE_DECIMALS[detected.instId] ?? 2) : "—";
    const chg = $("cbhud-chg");
    if (p != null && open24h) {
      const pct = (p / open24h - 1) * 100;
      chg.textContent = (pct >= 0 ? "▲ " : "▼ ") + Math.abs(pct).toFixed(2) + "%";
      chg.className = "cbhud-chg " + (pct >= 0 ? "up" : "down");
    } else {
      chg.textContent = "";
    }
    $("cbhud-delayed").style.display = priceDelayed ? "" : "none";
  }

  // ---- position card (shared shape for every symbol) --------------------
  function renderPositionCard(pos, price, thoughtLine) {
    const size = pos.contracts * pos.contract_size;
    const pnl = (price - pos.entry) * size * pos.dir;
    const pnlPct = ((price / pos.entry - 1) * 100) * pos.dir;
    const win = pnl >= 0;
    const cls = win ? "up" : "down";
    const dist = (lvl) => lvl ? (((lvl / price - 1) * 100)).toFixed(2) + "%" : "—";
    let prog = 0;
    if (pos.target) {
      const span = Math.abs(pos.target - pos.entry) || 1;
      prog = Math.max(0, Math.min(100, (Math.abs(price - pos.entry) / span) * 100 * (win ? 1 : 0)));
    }
    const targetLabel = pos.target_label || "trail";
    return `
      <div class="cbhud-postop">
        <span class="cbhud-side ${pos.dir < 0 ? "short" : "long"}">${pos.side}</span>
        <span class="cbhud-book">${pos.book}</span>
      </div>
      <div class="cbhud-pnl ${cls}">${win ? "+" : "−"}$${fmt(Math.abs(pnl), 2)}
        <span class="cbhud-pnlpct">${win ? "+" : ""}${pnlPct.toFixed(2)}%</span></div>
      <div class="cbhud-lvls">
        <div class="cbhud-lvl"><span>entry</span><b>$${fmt(pos.entry, 0)}</b></div>
        <div class="cbhud-lvl"><span>stop</span><b>$${fmt(pos.stop, 0)}</b><i>${dist(pos.stop)}</i></div>
        <div class="cbhud-lvl"><span>target</span><b>${pos.target ? "$" + fmt(pos.target, 0) : targetLabel}</b><i>${dist(pos.target)}</i></div>
      </div>
      ${pos.target ? `<div class="cbhud-bar"><div class="cbhud-bar-fill ${cls}" style="width:${prog}%"></div></div>` : ""}
      <div class="cbhud-thought">${thoughtLine || ""}</div>`;
  }

  // ---- the cross-symbol "a BTC news trade is armed" strip ---------------
  // Purely informational — no click handler, no hover affordance. Only
  // shown when the viewer is NOT on BTC-USDT and a BTC news trade is armed,
  // so nobody mistakes it for THEIR symbol's news.
  function renderArmedStrip(armedGlobal) {
    if (!armedGlobal) return "";
    const when = fmtLocalTime(armedGlobal.decision_ts);
    return `<div class="cbhud-newsstrip">📰 BTC news trade armed${when ? " · decides " + when : ""}</div>`;
  }

  // ---- body: position (live P&L) or the symbol's own flat card ----------
  function paintBody() {
    if (!state) { $("cbhud-body").innerHTML = `<div class="cbhud-flat">connecting…</div>`; return; }

    const marketWeather = (state.global && state.global.market) || state.market;
    const mkt = $("cbhud-mkt");
    mkt.textContent = marketWeather || "";
    mkt.className = "cbhud-mkt " + (wclass[marketWeather] || "");

    const instId = detected.instId;
    const symData = currentSymbolData();
    const armedGlobal = (state.global && state.global.armed) || state.armed || null;

    let p = livePrice;
    if (p == null && instId === "BTC-USDT") p = state.price;

    const pos = symData && symData.position;
    let strip = instId !== "BTC-USDT" ? renderArmedStrip(armedGlobal) : "";
    let html = "";

    if (pos && pos.entry && p != null) {
      const thoughtLine = `In a ${pos.side.toLowerCase()} (${pos.book}), managing it.`;
      html = renderPositionCard(pos, p, thoughtLine);
    } else if (instId === "BTC-USDT") {
      // BTC keeps its full existing behavior: armed news card, or the
      // "if I traded now" thesis card, or a plain flat card.
      const thought = (state.global && state.global.thought) || state.thought;
      if (armedGlobal) {
        let when = "at the bar close";
        if (armedGlobal.decision_ts) {
          const d = fmtLocalTime(armedGlobal.decision_ts);
          if (d) when = "at " + d;
        }
        html = `
          <div class="cbhud-flat">📰 NEWS TRADE ARMED</div>
          <div class="cbhud-why" style="margin-top:2px">${(armedGlobal.headline || "").replace(/^\[WatcherGuru\]\s*/, "")}</div>
          <div class="cbhud-mini" style="margin-top:8px">Direction decides ${when}, then it enters with a 1.2% stop, 2.4% target.</div>
          <div class="cbhud-thought">${thought || ""}</div>`;
      } else if (symData && symData.thesis) {
        const th = symData.thesis;
        const convCls = th.conviction >= 60 ? "hi" : (th.conviction >= 40 ? "mid" : "lo");
        html = `
          <div class="cbhud-flat">IF I TRADED NOW</div>
          <div class="cbhud-postop">
            <span class="cbhud-side ${th.side === "SHORT" ? "short" : "long"}">${th.side}</span>
            <span class="cbhud-book">${th.book}</span>
            <span class="cbhud-rr">R:R ${th.rr}:1</span>
          </div>
          <div class="cbhud-lvls">
            <div class="cbhud-lvl"><span>entry</span><b>$${fmt(th.entry, 0)}</b><i>market</i></div>
            <div class="cbhud-lvl"><span>TP</span><b>$${fmt(th.tp, 0)}</b><i class="up">${th.side === "SHORT" ? "−" : "+"}${th.reward_pct}%</i></div>
            <div class="cbhud-lvl"><span>SL</span><b>$${fmt(th.sl, 0)}</b><i class="down">${th.side === "SHORT" ? "+" : "−"}${th.risk_pct}%</i></div>
          </div>
          <div class="cbhud-conv">
            <div class="cbhud-conv-h"><span>conviction</span><b class="${convCls}">${th.conviction}%</b></div>
            <div class="cbhud-pbar"><div class="cbhud-pbar-fill ${convCls}" style="width:${th.conviction}%"></div></div>
          </div>
          <div class="cbhud-why">${th.why}</div>
          <div class="cbhud-thought">${thought || ""}</div>`;
      } else {
        html = `<div class="cbhud-flat">FLAT · watching the tape</div><div class="cbhud-thought">${thought || ""}</div>`;
      }
    } else if (instId === "XAUT-USDT") {
      const status = symData && symData.status;
      if (status && status.mode === "waiting_breakout") {
        html = `
          <div class="cbhud-flat">GOLD · WAITING FOR BREAKOUT</div>
          <div class="cbhud-lvls">
            <div class="cbhud-lvl"><span>buy above</span><b>$${fmt(status.level_55d, 0)}</b></div>
            <div class="cbhud-lvl"><span>trend line</span><b>$${fmt(status.ema20, 0)}</b></div>
          </div>
          <div class="cbhud-thought">${status.text || ""}</div>`;
      } else {
        html = `<div class="cbhud-flat">GOLD</div><div class="cbhud-thought">watching XAUT-USDT. levels unavailable right now.</div>`;
      }
    } else if (symData) {
      // ETH-USDT / SOL-USDT / TSLA-USDT / any other Daily Pick symbol,
      // flat: just their own status text.
      const status = symData.status;
      html = `<div class="cbhud-flat">${(symData.display || instId).toUpperCase()}</div><div class="cbhud-thought">${(status && status.text) || "watching the tape"}</div>`;
    } else {
      html = `<div class="cbhud-flat">${detected.hint ? detected.hint.toUpperCase() : instId}</div><div class="cbhud-thought">no read for this symbol yet.</div>`;
    }

    // freshness (whole-snapshot age — the 60s heartbeat, not per-symbol)
    const age = state.ts ? Date.now() - new Date(state.ts).getTime() : Infinity;
    html += age > STALE_MS
      ? `<div class="cbhud-stamp warn">⚠ bot snapshot ${Math.round(age/60000)}m old — daemon may be down</div>`
      : `<div class="cbhud-stamp">bot read ${age < 60000 ? Math.round(age/1000)+"s" : Math.round(age/60000)+"m"} ago · price live</div>`;
    el.classList.toggle("stale", age > STALE_MS);
    $("cbhud-body").innerHTML = strip + html;
  }

  // ---- pollers --------------------------------------------------------------
  function pollPrice() {
    const instId = detected.instId;
    chrome.runtime.sendMessage({ type: "cryptobot_price", instId }, (r) => {
      if (chrome.runtime.lastError) return;
      if (instId !== detected.instId) return; // symbol changed while in flight
      if (r && r.ok && r.data) {
        if (r.data.delayed) {
          priceDelayed = true;
        } else if (!isNaN(r.data.last)) {
          livePrice = r.data.last;
          if (r.data.open24h) open24h = r.data.open24h;
          priceDelayed = false;
        }
        paintPrice(); paintBody();
      }
    });
  }
  function pollState() {
    chrome.runtime.sendMessage({ type: "cryptobot_state" }, (r) => {
      if (chrome.runtime.lastError) return;
      if (r && r.ok && r.data && (r.data.thought !== undefined || r.data.symbols)) { state = r.data; paintPrice(); paintBody(); }
    });
  }

  // ---- re-detect on SPA navigation / tab refocus -------------------------
  function checkSymbolChange() {
    const next = detectSymbol();
    if (next.instId !== detected.instId) {
      detected = next;
      // a fresh symbol never inherits the old one's price/24h — that gap
      // shows "—" for a beat rather than briefly showing the wrong asset.
      livePrice = null; open24h = null; priceDelayed = false;
      paintPrice(); paintBody();
      pollPrice();
    }
  }
  setInterval(checkSymbolChange, DETECT_MS);
  document.addEventListener("visibilitychange", checkSymbolChange);

  pollState(); pollPrice();
  setInterval(pollPrice, PRICE_MS);
  setInterval(pollState, STATE_MS);
})();
