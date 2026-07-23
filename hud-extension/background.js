// background.js — fetches the bot's live snapshot from Supabase and relays it
// to the on-page panel. Done here (service worker) rather than in the content
// script so the page's own CSP can never block the request. Uses ONLY the
// public anon key — never the master state secret — so nothing sensitive
// ships in this extension.

const SUPABASE_URL = "https://gpgjujfkktxghqeqvrvh.supabase.co";
const ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwZ2p1amZra3R4Z2hxZXF2cnZoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI4MzUzNjQsImV4cCI6MjA5ODQxMTM2NH0.J6x9aJ83axmEHCn0cZNev7HnU37D2SY6EedqO_zwhqg";

async function fetchRead() {
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

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "cryptobot_read") {
    fetchRead()
      .then((data) => sendResponse({ ok: true, data }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true; // keep the message channel open for the async response
  }
});
