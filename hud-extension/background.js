// background.js — two jobs, both done here (service worker) so the page's
// CSP can never block them:
//   1. the bot's STATE snapshot from Supabase (anon key only — no secrets)
//   2. the LIVE price for whatever symbol the panel is currently showing,
//      straight from BloFin's public ticker, so the panel ticks with the
//      market instead of our 60s publish clock.
//
// v3 (2026-07-23): SYMBOL-AWARE. fetchPrice used to be hardcoded to
// BTC-USDT — the exact bug that showed Bitcoin's price on the owner's gold
// screen. It now takes the instId the content script detected and asks
// BloFin for THAT ticker. Binance is only a fallback for the three symbols
// that actually have a Binance twin (BTC/ETH/SOL); XAUT and TSLA have none,
// so on a BloFin throttle we tell the panel to keep showing its last known
// price rather than either blanking it or silently substituting BTC's.

const SUPABASE_URL = "https://gpgjujfkktxghqeqvrvh.supabase.co";
const ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwZ2p1amZra3R4Z2hxZXF2cnZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4MzUzNjQsImV4cCI6MjA5ODQxMTM2NH0.J6x9aJ83axmEHCn0cZNev7HnU37D2SY6EedqO_zwhqg";

async function fetchState() {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/rpc/cryptobot_live_read`, {
    method: "POST",
    headers: {
      apikey: ANON_KEY,
      Authorization: `Bearer ${ANON_KEY}`,
      "Content-Type": "application/json",
    },
    body: "{}",
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

const BLOFIN_TICKER_BASE = "https://openapi.blofin.com/api/v1/market/tickers";
const BINANCE_TICKER_BASE = "https://api.binance.com/api/v3/ticker/24hr";

// Only symbols with a real Binance twin get the fallback. Gold (XAUT-USDT)
// and Tesla (TSLA-USDT) don't trade on Binance at all — for those, a BloFin
// throttle just means "keep the last tick", handled by the caller.
const BINANCE_SYMBOL = {
  "BTC-USDT": "BTCUSDT",
  "ETH-USDT": "ETHUSDT",
  "SOL-USDT": "SOLUSDT",
};

async function fetchPrice(instId) {
  instId = instId || "BTC-USDT";

  // BloFin first (exact match to the BloFin chart, and the only source for
  // XAUT-USDT / TSLA-USDT at all).
  try {
    const r = await fetch(
      `${BLOFIN_TICKER_BASE}?instId=${encodeURIComponent(instId)}`
    );
    const txt = await r.text();
    const j = JSON.parse(txt); // throws if HTML interstitial
    const t = (j.data && j.data[0]) || {};
    const last = parseFloat(t.last);
    if (!isNaN(last)) {
      return {
        instId,
        last,
        open24h: parseFloat(t.open24h),
        src: "blofin",
      };
    }
  } catch (_) { /* fall through */ }

  // Binance fallback, only where a twin exists.
  const binSymbol = BINANCE_SYMBOL[instId];
  if (binSymbol) {
    try {
      const r2 = await fetch(`${BINANCE_TICKER_BASE}?symbol=${binSymbol}`);
      const j2 = await r2.json();
      const last = parseFloat(j2.lastPrice);
      if (!isNaN(last)) {
        return {
          instId,
          last,
          open24h: parseFloat(j2.openPrice),
          src: "binance",
        };
      }
    } catch (_) { /* fall through to delayed */ }
  }

  // No usable source right now. Tell the panel to keep its last price and
  // mark it delayed, instead of returning nothing or another symbol's tick.
  return { instId, delayed: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg) return;
  if (msg.type === "cryptobot_state") {
    fetchState()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
  if (msg.type === "cryptobot_price") {
    fetchPrice(msg.instId)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
});
