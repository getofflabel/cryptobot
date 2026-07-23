// background.js — two jobs, both done here (service worker) so the page's
// CSP can never block them:
//   1. the bot's STATE snapshot from Supabase (anon key only — no secrets)
//   2. the LIVE BTC price straight from BloFin's public ticker, so the panel
//      ticks with the market instead of our 60s publish clock.

const SUPABASE_URL = "https://gpgjujfkktxghqeqvrvh.supabase.co";
const ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwZ2p1amZra3R4Z2hxZXF2cnZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4MzUzNjQsImV4cCI6MjA5ODQxMTM2NH0.J6x9aJ83axmEHCn0cZNev7HnU37D2SY6EedqO_zwhqg";
const BLOFIN_TICKER =
  "https://openapi.blofin.com/api/v1/market/tickers?instId=BTC-USDT";

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

const BINANCE_TICKER =
  "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT";

async function fetchPrice() {
  // BloFin first (exact match to the BloFin chart); Binance as the always-up
  // fallback if BloFin throttles or returns its HTML interstitial.
  try {
    const r = await fetch(BLOFIN_TICKER);
    const txt = await r.text();
    const j = JSON.parse(txt); // throws if HTML interstitial
    const t = (j.data && j.data[0]) || {};
    const last = parseFloat(t.last);
    if (!isNaN(last)) return { last, open24h: parseFloat(t.open24h), src: "blofin" };
  } catch (_) { /* fall through to Binance */ }
  const r2 = await fetch(BINANCE_TICKER);
  const j2 = await r2.json();
  return {
    last: parseFloat(j2.lastPrice),
    open24h: parseFloat(j2.openPrice),
    src: "binance",
  };
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
    fetchPrice()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
});
