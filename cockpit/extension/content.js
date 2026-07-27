/*
 * content.js — the panel on the chart.
 *
 * THE ONE RULE
 *   Stale or missing must never render as fine. Everything below follows
 *   from that:
 *
 *   - Ages are counted from ABSOLUTE timestamps against this browser's own
 *     clock, and they are recomputed four times a second. So if the service
 *     stops answering, the numbers on screen do not freeze looking healthy —
 *     every age keeps climbing and the panel greys itself out.
 *   - A value we do not have is never drawn as a blank or a zero. It is
 *     drawn as the sentence saying why we do not have it.
 *   - Every price says how old it is IN SECONDS on its face. Past a few
 *     seconds it stops looking live; past half a minute it is marked stale
 *     outright. The number is never hidden to make the panel look calmer.
 *
 * THE TWO PRICES
 *   TradingView's own, read off the page, is what his eyes are on. The
 *   bot's feed is what the alert was worked out from. Both are shown, both
 *   labelled, and the gap between them is stated rather than smoothed over —
 *   on US stocks our plan only sees one exchange, so a gap is expected and
 *   he should be looking at it, not protected from it.
 *
 * SAFETY
 *   This script reads the page and draws a box. It does not click, type
 *   into, or submit anything on TradingView, and there is no code path here
 *   that could place, change or cancel an order.
 */

(() => {
  "use strict";
  if (window.__tradingCockpit) return;
  window.__tradingCockpit = true;

  const POLL_MS = 1000;   // ask the service once a second
  const DRAW_MS = 250;    // redraw four times a second so ages tick

  // How old a price is allowed to be before it stops looking live. These are
  // deliberately tight: the whole point is that a number he glances at while
  // placing a trade must not be able to lie to him about being current.
  const FRESH_S = 5;
  const WARN_S = 30;

  // The entry window this method gives is about forty minutes wide. Past an
  // hour, the setup has been and gone and the panel says so rather than
  // leaving yesterday's alert sitting under a heading that reads THE SIGNAL.
  const STALE_SIGNAL_S = 60 * 60;

  const state = {
    ans: null,          // the last answer from the service
    at: 0,              // when that answer arrived (epoch seconds)
    err: null,          // why the last attempt failed
    tv: { sym: "", price: null, seenAt: 0, changedAt: 0 },
    collapsed: false,
    showMsg: false
  };

  // ------------------------------------------------------------- helpers
  const now = () => Date.now() / 1000;

  // "1 minutes ago" on a panel he reads while placing a trade is the kind of
  // sloppiness that makes him doubt the numbers next to it.
  function count(n, word) {
    const r = Math.round(n);
    return r + " " + word + (r === 1 ? "" : "s");
  }

  function seconds(s) {
    if (s == null || !isFinite(s)) return "age unknown";
    if (s < 90) return count(s, "second") + " old";
    if (s < 5400) return count(s / 60, "minute") + " old";
    if (s < 172800) return (s / 3600).toFixed(1) + " hours old";
    return (s / 86400).toFixed(1) + " days old";
  }

  function ago(s) {
    if (s == null || !isFinite(s)) return "at an unknown time";
    if (s < 45) return count(s, "second") + " ago";
    if (s < 5400) return count(s / 60, "minute") + " ago";
    if (s < 172800) return (s / 3600).toFixed(1) + " hours ago";
    return (s / 86400).toFixed(1) + " days ago";
  }

  function freshness(s) {
    if (s == null || !isFinite(s)) return "dead";
    if (s <= FRESH_S) return "live";
    if (s <= WARN_S) return "aging";
    return "dead";
  }

  const esc = (t) =>
    String(t == null ? "" : t).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ------------------------------------- what is on his screen right now
  //
  // document.title is TradingView's own, kept up to date by TradingView, and
  // it survives every redesign of the chart's internals. It reads
  // "BTCUSDT 64,402.01 ▲ +0.41%". The header element is used for the symbol
  // when it is there because it is unambiguous, and the title is the price.
  function readChart() {
    const m = /^([^\s]+)\s+([\d,]+\.?\d*)/.exec(document.title || "");
    const header = document.querySelector("#header-toolbar-symbol-search");
    const sym =
      (header && header.textContent.trim()) || (m && m[1]) || "";
    const price = m ? parseFloat(m[2].replace(/,/g, "")) : null;
    const t = now();
    if (price != null && isFinite(price)) {
      if (state.tv.price !== price) state.tv.changedAt = t;
      state.tv.price = price;
      state.tv.seenAt = t;
    }
    // The exchange prefix matters — BINANCE:BTCUSDT and COINBASE:BTCUSD are
    // different instruments — and the URL carries it as "BINANCE:BTCUSDT".
    // It is only used when its ticker still matches the one in the header,
    // because the URL lags by a moment when he switches symbol, and a stale
    // exchange glued to a fresh ticker would name an instrument that is on
    // neither.
    let out = sym;
    try {
      const u = new URLSearchParams(location.search).get("symbol") || "";
      if (u.includes(":") && u.split(":")[1].toUpperCase() === sym.toUpperCase()) {
        out = u;
      }
    } catch (e) { /* the ticker on its own is enough for the service */ }
    state.tv.sym = sym;
    return out;
  }

  // ------------------------------------------------------------ the box
  const root = document.createElement("div");
  root.className = "tc-root";
  root.innerHTML =
    '<div class="tc-head">' +
    '<span class="tc-dot" id="tc-dot"></span>' +
    '<span class="tc-name">COCKPIT</span>' +
    '<span class="tc-grip" id="tc-grip">drag</span>' +
    '<button class="tc-fold" id="tc-fold" type="button">hide</button>' +
    "</div>" +
    '<div class="tc-body" id="tc-body"></div>';
  document.documentElement.appendChild(root);

  const body = root.querySelector("#tc-body");
  const dot = root.querySelector("#tc-dot");
  const fold = root.querySelector("#tc-fold");

  fold.addEventListener("click", () => {
    state.collapsed = !state.collapsed;
    fold.textContent = state.collapsed ? "show" : "hide";
    root.classList.toggle("tc-collapsed", state.collapsed);
    chrome.storage.local.set({ collapsed: state.collapsed });
  });

  // Dragging, because on some layouts the top right corner is where his
  // order ticket lives. It moves the panel and it remembers where he put it.
  (() => {
    const grip = root.querySelector("#tc-grip");
    let from = null;
    grip.addEventListener("mousedown", (e) => {
      from = { x: e.clientX, y: e.clientY, top: root.offsetTop, left: root.offsetLeft };
      e.preventDefault();
    });
    window.addEventListener("mousemove", (e) => {
      if (!from) return;
      const top = Math.max(0, from.top + e.clientY - from.y);
      const left = Math.max(0, from.left + e.clientX - from.x);
      root.style.top = top + "px";
      root.style.left = left + "px";
      root.style.right = "auto";
    });
    window.addEventListener("mouseup", () => {
      if (from) chrome.storage.local.set({ top: root.style.top, left: root.style.left });
      from = null;
    });
  })();

  chrome.storage.local.get(["top", "left", "collapsed"], (v) => {
    if (v.top) { root.style.top = v.top; root.style.left = v.left; root.style.right = "auto"; }
    if (v.collapsed) {
      state.collapsed = true;
      root.classList.add("tc-collapsed");
      fold.textContent = "show";
    }
  });

  // --------------------------------------------------------- the drawing
  function row(label, value, cls) {
    return (
      '<div class="tc-row ' + (cls || "") + '">' +
      '<span class="tc-k">' + esc(label) + "</span>" +
      '<span class="tc-v">' + esc(value) + "</span>" +
      "</div>"
    );
  }

  function note(text, cls) {
    return '<div class="tc-note ' + (cls || "") + '">' + esc(text) + "</div>";
  }

  function drawSignal(d) {
    let h = '<div class="tc-sec">THE SIGNAL</div>';
    if (!d.signal) {
      return h + note(d.signal_why || "no signal recorded.", "tc-quiet");
    }
    const s = d.signal;
    const age = now() - (s.fired_at || 0);

    // A SIGNAL FROM YESTERDAY IS NOT A TRADE TO PLACE THIS MORNING. The
    // entry window this method gives is about forty minutes wide, so past an
    // hour the setup has been and gone. It is still shown — he may want to
    // see what the last one was — but it is labelled so it cannot be
    // mistaken for something live, and the whole block is dimmed.
    const gone = age > STALE_SIGNAL_S;
    if (gone) {
      h += note("THIS ONE HAS BEEN AND GONE — it fired " + ago(age) +
                " and the moment to take it has passed. It is here so you " +
                "can see what the last alert was, not to place now.",
                "tc-bad");
    }
    if (s.agrees_with_phone === false) {
      h += note(
        "THESE NUMBERS DO NOT MATCH THE MESSAGE SENT TO YOUR PHONE. " +
        "Trust the phone, not this panel.", "tc-bad");
    }
    s.trades.forEach((t) => {
      if (t.broken) { h += note(t.broken, "tc-bad"); return; }
      h +=
        '<div class="tc-trade' + (gone ? " tc-gone" : "") + '">' +
        '<div class="tc-side tc-' + (t.side === "BUY" ? "buy" : "sell") + '">' +
        esc(t.side) + " " + esc(t.symbol) +
        '<span class="tc-when">' + esc(t.market_label) + " · fired " +
        esc(ago(age)) + "</span></div>";
      h += row("Enter around", t.entry);
      h += row("Stop", t.stop);
      h += note(t.stop_away + " — it sits " + t.stop_sits_on, "tc-sub");
      t.targets.forEach((tg, i) => {
        h += row(["First target", "Second target", "Third target", "Fourth target"][i], tg.price);
        h += note(tg.away + (tg.sits_on ? ", " + tg.sits_on : ""), "tc-sub");
      });
      if (!t.targets.length) {
        h += note("the chart offers nowhere ahead to take profit — run it " +
                  "to the stop or to the close", "tc-sub");
      }
      if (t.size_lines) {
        h += '<div class="tc-size">' +
             t.size_lines.map((l) => '<div>' + esc(l) + "</div>").join("") +
             "</div>";
      } else {
        h += note("NO SIZE: " + (t.size_refused_because || "unknown"), "tc-bad");
      }
      if (t.venue_note) h += note(t.venue_note, "tc-warn");
      h += '<div class="tc-why"><b>Why:</b> ' + esc(t.why) + "</div>";
      h += "</div>";
    });
    if (s.account_used_note) h += note(s.account_used_note, "tc-warn");
    h += '<button class="tc-link" id="tc-msg" type="button">' +
         (state.showMsg ? "hide" : "show") +
         " the message that went to your phone</button>";
    if (state.showMsg) h += '<pre class="tc-msg">' + esc(s.message) + "</pre>";
    return h;
  }

  function drawPrice(d) {
    let h = '<div class="tc-sec">PRICE</div>';
    const p = d.price || {};
    const q = p.quote || {};

    // TradingView's own number, off the page he is looking at.
    const tv = state.tv;
    if (tv.price != null) {
      const readAge = now() - tv.seenAt;
      h += '<div class="tc-price ' + freshness(readAge) + '">' +
           '<span class="tc-big">' + esc(tv.price.toLocaleString()) + "</span>" +
           '<span class="tc-src">TradingView, read off this chart · ' +
           esc(seconds(readAge)) + "</span></div>";
      h += note("what you would actually be filled near", "tc-role");
      h += note("it last changed " + ago(now() - tv.changedAt) +
                " — if that keeps growing while the market is open, this " +
                "chart has stopped updating", "tc-sub");
    } else {
      h += note("could not read a price off this TradingView chart", "tc-bad");
    }

    // The bot's own feed, which is what the alert was worked out from.
    if (q.ok) {
      const age = q.age_seconds + (now() - (state.at || now()));
      h += '<div class="tc-price ' + freshness(age) + '">' +
           '<span class="tc-big">' +
           esc(q.price.toLocaleString(undefined, { maximumFractionDigits: 6 })) +
           "</span>" +
           '<span class="tc-src">' + esc(q.source) + " · " +
           esc(seconds(age)) +
           (freshness(age) === "dead" ? " · STALE" : "") +
           "</span></div>";
      h += note("what the bot works from — the feed the alert above was " +
                "measured on", "tc-role");
      h += note(q.source_note || "", "tc-sub");
      if (tv.price != null) {
        const gap = q.price - tv.price;
        const pct = (100 * gap) / tv.price;
        h += note(
          "that is " + (gap >= 0 ? "+" : "") + gap.toFixed(2) +
          " against the chart, a " + Math.abs(pct).toFixed(3) +
          "% DIFFERENCE IN THE PRICE between the two feeds", "tc-sub");
      }
    } else {
      h += note(q.why || "no price for this instrument", "tc-bad");
    }
    if (p.kind === "unknown") {
      h += note("the bot does not watch " + esc(p.symbol) +
                ", so nothing on this panel is about it", "tc-warn");
    }
    return h;
  }

  function drawAccount(d) {
    let h = '<div class="tc-sec">ACCOUNT</div>';
    const a = d.account;
    if (!a) return h + note(d.account_why || "balance unknown", "tc-bad");
    const age = a.age_seconds + (now() - (state.at || now()));
    h += '<div class="tc-price ' + (age > 86400 ? "dead" : "live") + '">' +
         '<span class="tc-big">$' +
         esc(a.equity.toLocaleString(undefined, { minimumFractionDigits: 2,
                                                  maximumFractionDigits: 2 })) +
         "</span>" +
         '<span class="tc-src">' + esc(a.route_words) + " · set " +
         esc(ago(age)) + "</span></div>";
    if (age > 86400) {
      h += note("THAT BALANCE IS MORE THAN A DAY OLD, and every size above " +
                "was worked out from it. Text the bot:  balance 105000",
                "tc-bad");
    }
    const r = d.risk_now;
    if (r && r.dollars != null) {
      h += note("this signal risks $" + r.dollars.toLocaleString() +
                " — that is " + r.pct_of_account +
                "% OF THE ACCOUNT (not a move in the price)", "tc-warn");
      if (r.note) h += note(r.note, "tc-sub");
    } else if (r) {
      // Never "$0". An unsized signal risks an unknown amount.
      h += note("WHAT THIS SIGNAL RISKS IS UNKNOWN — " + r.note, "tc-bad");
    }
    return h;
  }

  function drawOpen(d) {
    const o = d.open || { trades: [] };
    const list = o.trades || [];
    let h = '<div class="tc-sec">OPEN &mdash; what the bot believes you are in (' +
            list.length + ")</div>";
    if (!o.as_of) {
      return h + note("the bot has never recorded its open trades", "tc-quiet");
    }
    // An empty list that reads as "you are flat" when he is holding something
    // is the worst thing this section could imply, so the one case where that
    // can happen is called out before the list itself.
    if (o.may_be_incomplete) h += note(o.may_be_incomplete, "tc-bad");
    if (!list.length) {
      h += note("nothing open. Checked " + ago(now() - o.as_of) + ".",
                "tc-quiet");
      return h;
    }
    list.forEach((t) => {
      h += row(t.side + " " + t.symbol,
               "stop " + t.stop.toLocaleString() + (t.half_off ? " · half off already" : ""));
    });
    h += note("this is what the BOT thinks. It cannot see your broker — " +
              "if you skipped one of these, it is wrong. Checked " +
              ago(now() - o.as_of) + ".", "tc-sub");
    return h;
  }

  function drawDesk(d) {
    const k = d.desk || {};
    if (!k.alive) {
      return note("THE BOT IS NOT WATCHING. " + (k.why || "") +
                  " Nothing above will update.", "tc-bad");
    }
    let h = note("the bot is watching " + (k.markets || []).join(", ") +
                 ", last swept " + ago(now() - k.as_of) +
                 (k.note ? " · " + k.note : ""), "tc-quiet");
    // A market that could not be reached is NOT a market where nothing set
    // up. Silence from it means nothing at all, and the panel says which.
    (k.failed || []).forEach((f) => {
      h += note(f.name.toUpperCase() + " COULD NOT BE CHECKED on the last " +
                "sweep — " + (f.why || "no reason given") +
                ". Silence from it means nothing.", "tc-bad");
    });
    return h;
  }

  function draw() {
    if (state.collapsed) return;
    const stale = state.ans ? now() - state.at : null;

    if (!state.ans) {
      dot.className = "tc-dot tc-dead";
      body.innerHTML = note(
        state.err || "starting up — asking the cockpit service...",
        state.err ? "tc-bad" : "tc-quiet");
      return;
    }

    const broken = !!state.err;
    dot.className = "tc-dot " + (broken ? "tc-dead" : "tc-ok");
    root.classList.toggle("tc-stale", broken);

    let h = "";
    if (broken) {
      h += note("THE COCKPIT SERVICE IS NOT ANSWERING — " + state.err +
                " Everything below is from " + ago(stale) +
                " and is getting older.", "tc-bad");
    }
    // THE PRICE AND THE BALANCE COME FIRST, and that ordering is his.
    // "there's no point of anything if you don't know the live price", and
    // "you also have to always know how much is actually in my account".
    // Both are true whether or not a signal exists, and a signal block runs
    // long enough to push them off the bottom of the panel — so they sit
    // above it, where a glance always lands on them.
    const d = state.ans;
    h += drawPrice(d) + drawAccount(d) + drawSignal(d) + drawOpen(d) +
         drawDesk(d);
    body.innerHTML = h;

    const btn = body.querySelector("#tc-msg");
    if (btn) btn.addEventListener("click", () => { state.showMsg = !state.showMsg; draw(); });
  }

  // ------------------------------------------------------------- the loop
  function poll() {
    const sym = readChart();
    chrome.runtime.sendMessage({ type: "cockpit", symbol: sym }, (r) => {
      if (chrome.runtime.lastError || !r) {
        state.err = "the extension's background worker did not answer — " +
                    "reload the extension.";
        return;
      }
      if (r.ok) { state.ans = r.data; state.at = r.receivedAt; state.err = null; }
      else { state.err = r.why; }
    });
  }

  poll();
  setInterval(poll, POLL_MS);
  setInterval(() => { readChart(); draw(); }, DRAW_MS);
})();
