/*
 * background.js — the one place the panel talks to the local service.
 *
 * WHY IT IS HERE AND NOT IN THE PANEL
 *   A content script's fetch runs under tradingview.com's own origin and is
 *   subject to their rules. The service worker runs under the extension's,
 *   where the loopback address is an explicitly granted host. Routing every
 *   request through here means one reliable path and one place a failure can
 *   be seen, rather than a request that works today and is blocked by a
 *   header change tomorrow.
 *
 * WHAT IT WILL AND WILL NOT DO
 *   GET, to 127.0.0.1, and nothing else. There is no POST here and the
 *   service refuses one anyway. The extension holds no keys, no tokens and
 *   no account details: everything that knows anything stays on the machine,
 *   behind this one read-only address.
 *
 * A FAILURE IS AN ANSWER
 *   When the service is not running, this returns { ok: false } with the
 *   reason in words and the panel puts that on screen. It never returns the
 *   last thing it saw, because a panel that keeps drawing the previous
 *   answer is exactly the failure this whole thing exists to prevent.
 */

const BASE = "http://127.0.0.1:8787";
const TIMEOUT_MS = 4000;

async function ask(symbol) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const url = BASE + "/cockpit?symbol=" + encodeURIComponent(symbol || "");
    const r = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
    if (!r.ok) {
      return { ok: false, why: "the cockpit service answered " + r.status };
    }
    const data = await r.json();
    return { ok: true, data, receivedAt: Date.now() / 1000 };
  } catch (e) {
    const aborted = e && e.name === "AbortError";
    return {
      ok: false,
      why: aborted
        ? "the cockpit service did not answer within 4 seconds"
        : "the cockpit service is not running. In a terminal:  cd ~/cryptobot && python3 -m cockpit.service"
    };
  } finally {
    clearTimeout(timer);
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === "cockpit") {
    ask(msg.symbol).then(reply);
    return true; // the answer comes later
  }
  return false;
});
