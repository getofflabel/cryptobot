"""
step361_spy_usdt_probe.py — READ-ONLY deep probe of the S&P-tracking
contract on BloFin's real host (SPY-USDT), plus the practice-host list.

No orders. No account changes. Public endpoints only.

Answers:
  - does SPY-USDT trade round the clock or only in US market hours?
  - how wide is the spread (that IS the cost of a market order)?
  - what does it cost to hold overnight (funding)?
  - does its price actually track the real S&P tracker?
  - what does the practice host list at all?
"""
import datetime as dt
import json

import pandas as pd
import requests

PROD = "https://openapi.blofin.com"
DEMO = "https://demo-trading-openapi.blofin.com"


def get(host, path, **params):
    r = requests.get(f"{host}{path}", params=params, timeout=25)
    j = r.json()
    if j.get("code") not in ("0", 0):
        raise RuntimeError(f"{path} code={j.get('code')} msg={j.get('msg')}")
    return j.get("data")


def candles(host, inst, bar="1H", limit=1000):
    rows = get(host, "/api/v1/market/candles", instId=inst, bar=bar, limit=limit)
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close",
                                     "vol", "volCurrency", "volCurrencyQuote",
                                     "confirm"][:len(rows[0])])
    df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "vol"):
        df[c] = df[c].astype(float)
    return df.sort_values("ts").reset_index(drop=True)


def main():
    print("=" * 72)
    print("PRACTICE HOST — everything it lists")
    print("=" * 72)
    demo_inst = get(DEMO, "/api/v1/market/instruments", instType="SWAP")
    ids = sorted(d["instId"] for d in demo_inst)
    print(f"{len(ids)} contracts:")
    for i in range(0, len(ids), 8):
        print("   " + "  ".join(ids[i:i + 8]))
    non_crypto = [i for i in ids if i.split("-")[0] in
                  {"SPY", "QQQ", "IWM", "TSLA", "NVDA", "AAPL", "MSFT", "META",
                   "AMZN", "GOOGL", "COIN", "HOOD", "MSTR", "XAUT", "PAXG",
                   "WTIOIL", "GOLD", "SILVER"}]
    print(f"\nnon-crypto-looking contracts on practice host: {non_crypto}")

    print("\n" + "=" * 72)
    print("SPY-USDT on the real host — spread, hours, funding, tracking")
    print("=" * 72)
    for sym in ("SPY-USDT", "QQQ-USDT", "IWM-USDT"):
        t = get(PROD, "/api/v1/market/tickers", instId=sym)[0]
        bid, ask, last = float(t["bidPrice"]), float(t["askPrice"]), float(t["last"])
        spread_pct = (ask - bid) / ((ask + bid) / 2) * 100
        base_vol = float(t.get("volCurrency24h", 0))
        print(f"\n{sym}")
        print(f"  last {last}  bid {bid}  ask {ask}")
        print(f"  spread = {spread_pct:.4f}% of price  "
              f"(crossing it once costs that, twice for a round trip)")
        print(f"  24h volume: {base_vol:,.1f} units = ${base_vol * last:,.0f}")
        print(f"  bid size {t.get('bidSize')}  ask size {t.get('askSize')}")

        try:
            fr = get(PROD, "/api/v1/market/funding-rate", instId=sym)[0]
            print(f"  funding right now: {float(fr['fundingRate']) * 100:.4f}% "
                  f"per period, next {dt.datetime.fromtimestamp(int(fr['fundingTime']) / 1000, dt.UTC)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  funding: {exc}")
        try:
            hist = get(PROD, "/api/v1/market/funding-rate-history",
                       instId=sym, limit=200)
            rates = [float(h["fundingRate"]) for h in hist]
            s = pd.Series(rates)
            print(f"  funding history n={len(rates)}: median {s.median() * 100:.4f}% "
                  f"per period, mean {s.mean() * 100:.4f}%, "
                  f"annualised at 3/day = {s.mean() * 3 * 365 * 100:.1f}%")
        except Exception as exc:  # noqa: BLE001
            print(f"  funding history: {exc}")

        try:
            df = candles(PROD, sym, "1H", 500)
            df["hour_utc"] = df.ts.dt.hour
            df["dow"] = df.ts.dt.dayofweek
            live = df[df.vol > 0]
            print(f"  hourly bars pulled: {len(df)}, span {df.ts.min()} -> {df.ts.max()}")
            print(f"  bars with any volume: {len(live)} ({len(live) / len(df) * 100:.1f}%)")
            by_h = df.groupby("hour_utc")["vol"].median()
            active = by_h[by_h > 0].index.tolist()
            print(f"  UTC hours with non-zero median volume: {active}")
            wknd = df[df.dow >= 5]
            print(f"  weekend bars: {len(wknd)}, of which traded: {(wknd.vol > 0).sum()}")
        except Exception as exc:  # noqa: BLE001
            print(f"  candles: {exc}")

    print("\n" + "=" * 72)
    print("DOES SPY-USDT ACTUALLY TRACK THE REAL S&P TRACKER?")
    print("=" * 72)
    try:
        spy = pd.read_parquet("/Users/wallacechen/cryptobot/data_spx_SPY_1d.parquet")
        print(f"  our SPY daily file: {spy.shape}, last rows:")
        print(spy.tail(3).to_string())
    except Exception as exc:  # noqa: BLE001
        print(f"  local SPY file: {exc}")

    out = {"demo_ids": ids}
    with open("/Users/wallacechen/cryptobot/step361_probe.json", "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
