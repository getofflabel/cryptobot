"""
step360_venue_scan.py — READ-ONLY venue scan for the S&P bot.

Asks BloFin (both the real host and the practice host) what it actually
lists, so we stop guessing. No orders. No account changes. Public
endpoints only.

Questions this answers:
  1. What is SPX-USDT, really?
  2. Is there any S&P-tracking or index-tracking contract on either host?
  3. For every candidate: contract size, price step, max leverage,
     is it alive, how much trades in 24h, and what it costs to trade.
"""
import json
import sys

import requests

PROD = "https://openapi.blofin.com"
DEMO = "https://demo-trading-openapi.blofin.com"

# words that would appear in an index-tracking or equity-tracking ticker
INDEX_WORDS = ("SPX", "SPY", "SP500", "ES", "US500", "NDX", "QQQ", "NAS",
               "DJI", "DOW", "RUT", "IWM", "VIX", "VOO", "IVV")


def get(host, path, **params):
    try:
        r = requests.get(f"{host}{path}", params=params, timeout=20)
        j = r.json()
        if j.get("code") not in ("0", 0):
            return None, f"code={j.get('code')} msg={j.get('msg')}"
        return j.get("data"), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def scan(host, label):
    print(f"\n{'=' * 70}\n{label}  ({host})\n{'=' * 70}")
    out = {}
    for inst_type in ("SWAP",):
        data, err = get(host, "/api/v1/market/instruments", instType=inst_type)
        if err:
            print(f"  instruments {inst_type}: FAILED {err}")
            continue
        print(f"  {inst_type}: {len(data)} instruments listed")
        out[inst_type] = data
        hits = [d for d in data
                if any(w in d["instId"].upper().split("-")[0] for w in INDEX_WORDS)]
        print(f"  index-word matches: {[d['instId'] for d in hits]}")
        for d in hits:
            print(f"    {d['instId']}: contractValue={d.get('contractValue')} "
                  f"tickSize={d.get('tickSize')} minSize={d.get('minSize')} "
                  f"lotSize={d.get('lotSize')} maxLeverage={d.get('maxLeverage')} "
                  f"state={d.get('state')} maxMarketSize={d.get('maxMarketSize')} "
                  f"listTime={d.get('listTime')}")
    return out


def ticker(host, inst_id):
    data, err = get(host, "/api/v1/market/tickers", instId=inst_id)
    if err or not data:
        return None, err or "empty"
    return data[0], None


def main():
    prod = scan(PROD, "REAL HOST (money host)")
    demo = scan(DEMO, "PRACTICE HOST (the one our bot trades)")

    prod_ids = {d["instId"] for d in prod.get("SWAP", [])}
    demo_ids = {d["instId"] for d in demo.get("SWAP", [])}
    print(f"\nlisted on real host only: {len(prod_ids - demo_ids)}")
    print(f"listed on practice host only: {len(demo_ids - prod_ids)}")

    print(f"\n{'=' * 70}\nWHAT IS IT REALLY? live prices vs the real world\n{'=' * 70}")
    for sym in ("SPX-USDT", "SPY-USDT", "QQQ-USDT", "NVDA-USDT", "TSLA-USDT",
                "AAPL-USDT", "BTC-USDT"):
        for host, label in ((PROD, "real"), (DEMO, "practice")):
            t, err = ticker(host, sym)
            if err:
                print(f"  {sym:12s} {label:9s} NOT SERVED ({err})")
            else:
                print(f"  {sym:12s} {label:9s} last={t.get('last')} "
                      f"24h_quote_volume={t.get('volCurrency24h')} "
                      f"bid={t.get('bidPrice')} ask={t.get('askPrice')}")

    # a full dump so we can grep later without re-hitting the exchange
    with open("/Users/wallacechen/cryptobot/step360_instruments.json", "w") as fh:
        json.dump({"prod": prod, "demo": demo}, fh, indent=1)
    print("\nfull instrument dump -> step360_instruments.json")


if __name__ == "__main__":
    sys.exit(main())
