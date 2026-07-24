# THE PNL SHEET

Live trading dashboard for the cryptobot. Single self-contained file
(`index.html`, no build step, no external libraries/fonts/CDNs) deployed as
a static site on Render.

**Live URL once deployed:** https://cryptobot-pnl.onrender.com

## How data flows

```
browser (index.html)
  --30s poll-->  POST https://gpgjujfkktxghqeqvrvh.supabase.co/rest/v1/rpc/cryptobot_pnl_sheet
                 headers: apikey / Authorization: Bearer <anon key>, body {}
  <--json-----   { generated_at, equity, goal, open: {...}, events: [...] }
```

The anon key embedded in `index.html` is the same public, read-only anon
key already shipped in `hud-extension/background.js` — safe to expose in
client-side code, it can only call the read-only `cryptobot_pnl_sheet` RPC.

Everything else happens client-side, in the browser, on every poll:

1. **Pairing** — `events` come back newest-first. The page walks them in
   chronological order and, per `(book, symbol)`, FIFO-matches every
   `*_enter` action to the next `*_exit` action for that same book+symbol,
   producing a `TRADE` (entry price/time, exit price/time, pnl, trigger,
   headline). An entry left over with no matching exit is an **open**
   trade for that market/book.
2. **Cross-check** — the RPC's `open` object (`ride/strikes/eth/lab/news/gold/pick`)
   is merged in for any book that has a live position but wasn't already
   captured by pairing (e.g. right after the ledger reset, where the
   entry event itself may predate the events window returned).
3. **Side inference** — the RPC doesn't send LONG/SHORT directly, so the
   page infers it from whether pnl agrees with the direction of price
   movement, falling back to "Shorts Lab is always short" / trigger text
   containing "short" when pnl or prices are missing (e.g. an open
   position).
4. **Windowing** — 1D/7D/30D/3M/6M/1Y filters closed trades by **exit
   time** relative to the browser's `Date.now()`. Open trades are always
   shown (pinned at the top of a drawer) since they're live regardless of
   window.

No server, no database, no build step on this side — just a static HTML
file polling a public read-only endpoint.

## Render service

Added to `render.yaml` as a second service, alongside the existing
`cryptobot-daemon` worker (untouched):

```yaml
  - type: web
    name: cryptobot-pnl
    runtime: static
    buildCommand: ""
    staticPublishPath: ./dashboard
```

Render serves `dashboard/index.html` directly at the site root, no
`envVars` needed since the only credential in play is the public anon key
already embedded in the file.
