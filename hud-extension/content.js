// content.js — injects the floating "what the bot is thinking" panel and
// keeps it live. Polls the background fetcher every 12s, renders the Storm
// Gauge + each book's read, and is draggable (position remembered).

(function () {
  if (window.__cryptobotHud) return; // guard against double-injection
  window.__cryptobotHud = true;

  const POLL_MS = 12000;
  const STALE_MS = 5 * 60 * 1000; // snapshot older than this = daemon likely down

  // ---- build the panel shell ------------------------------------------------
  const el = document.createElement("div");
  el.id = "cbhud";
  el.innerHTML = `
    <div id="cbhud-head">
      <span class="cbhud-live"><span class="cbhud-dot"></span>CRYPTOBOT</span>
      <span id="cbhud-price">—</span>
      <span id="cbhud-collapse" title="collapse">‹</span>
    </div>
    <div id="cbhud-body">
      <div class="cbhud-sec">
        <div class="cbhud-sec-h"><span>STORM GAUGE</span><span id="cbhud-weather" class="cbhud-badge">—</span></div>
        <div class="cbhud-row"><span>Market violence</span><span id="cbhud-viol" class="cbhud-mono">—</span></div>
        <div class="cbhud-row"><span>vs past year</span><span id="cbhud-pct" class="cbhud-mono">—</span></div>
        <div class="cbhud-row"><span>If you enter: size</span><span id="cbhud-size" class="cbhud-mono">—</span></div>
        <div class="cbhud-row"><span id="cbhud-ledger-lbl">On ledger</span><span id="cbhud-dollars" class="cbhud-mono">—</span></div>
        <div id="cbhud-action" class="cbhud-action">—</div>
      </div>
      <div class="cbhud-sec" id="cbhud-books"></div>
      <div class="cbhud-thought" id="cbhud-thought">—</div>
      <div class="cbhud-foot">Says how much — never when. Entries are your strategy's job.</div>
      <div class="cbhud-stamp" id="cbhud-stamp"></div>
    </div>`;
  document.documentElement.appendChild(el);

  // ---- restore saved position / collapsed state -----------------------------
  chrome.storage.local.get(["cbhud_pos", "cbhud_collapsed"], (s) => {
    const p = s.cbhud_pos;
    if (p && typeof p.left === "number") {
      el.style.left = p.left + "px";
      el.style.top = p.top + "px";
      el.style.right = "auto";
    }
    if (s.cbhud_collapsed) el.classList.add("collapsed");
  });

  // ---- collapse toggle ------------------------------------------------------
  document.getElementById("cbhud-collapse").addEventListener("click", (e) => {
    e.stopPropagation();
    el.classList.toggle("collapsed");
    chrome.storage.local.set({ cbhud_collapsed: el.classList.contains("collapsed") });
  });

  // ---- drag by the header ---------------------------------------------------
  const head = document.getElementById("cbhud-head");
  let dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
  head.addEventListener("mousedown", (e) => {
    if (e.target.id === "cbhud-collapse") return;
    dragging = true;
    const r = el.getBoundingClientRect();
    ox = r.left; oy = r.top; sx = e.clientX; sy = e.clientY;
    el.style.right = "auto";
    e.preventDefault();
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const nl = Math.max(0, Math.min(window.innerWidth - 60, ox + e.clientX - sx));
    const nt = Math.max(0, Math.min(window.innerHeight - 30, oy + e.clientY - sy));
    el.style.left = nl + "px";
    el.style.top = nt + "px";
  });
  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    const r = el.getBoundingClientRect();
    chrome.storage.local.set({ cbhud_pos: { left: r.left, top: r.top } });
  });

  // ---- render a snapshot ----------------------------------------------------
  const $ = (id) => document.getElementById(id);
  const wclass = { CALM: "calm", CHOPPY: "chop", STORM: "storm" };

  function render(d) {
    if (!d || !d.storm) { setStale("no data yet"); return; }
    const s = d.storm;
    $("cbhud-price").textContent = "BTC $" + (d.price || 0).toLocaleString();
    const w = $("cbhud-weather");
    w.textContent = s.weather;
    w.className = "cbhud-badge " + (wclass[s.weather] || "");
    $("cbhud-viol").textContent = `${s.violence}% / ${s.limit} limit`;
    $("cbhud-pct").textContent = `${s.percentile}%`;
    $("cbhud-size").textContent = `${(s.size_mult).toFixed(2)}x`;
    $("cbhud-ledger-lbl").textContent = `On $${Math.round(s.ledger).toLocaleString()} ledger`;
    $("cbhud-dollars").textContent = `$${(s.entry_dollars || 0).toLocaleString()}`;
    const a = $("cbhud-action");
    a.textContent = "▸ " + s.action;
    a.className = "cbhud-action " + (wclass[s.weather] || "");

    const books = $("cbhud-books");
    books.innerHTML = (d.books || []).map((b) =>
      `<div class="cbhud-book"><span class="cbhud-bdot ${b.armed ? "on" : ""}"></span>` +
      `<span class="cbhud-bname">${b.name}</span>` +
      `<span class="cbhud-bread">${b.read}</span></div>`
    ).join("");

    $("cbhud-thought").textContent = "💭 " + (d.thought || "");

    // freshness
    const age = d.ts ? Date.now() - new Date(d.ts).getTime() : Infinity;
    if (age > STALE_MS) {
      setStale(`snapshot ${Math.round(age / 60000)}m old — daemon may be down`);
    } else {
      const secs = Math.round(age / 1000);
      $("cbhud-stamp").textContent = `updated ${secs < 60 ? secs + "s" : Math.round(secs / 60) + "m"} ago`;
      el.classList.remove("stale");
    }
  }

  function setStale(msg) {
    el.classList.add("stale");
    $("cbhud-stamp").textContent = "⚠ " + msg;
  }

  // ---- poll loop ------------------------------------------------------------
  function tick() {
    chrome.runtime.sendMessage({ type: "cryptobot_read" }, (resp) => {
      if (chrome.runtime.lastError) { setStale("extension reloading…"); return; }
      if (resp && resp.ok) render(resp.data);
      else setStale("fetch failed");
    });
  }
  tick();
  setInterval(tick, POLL_MS);
})();
