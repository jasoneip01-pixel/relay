#!/usr/bin/env python3
"""Yahoo Finance Relay — fetches stock quotes via yfinance from US GitHub runner.
Usage: python3 yfinance_relay.py [SYM1,SYM2,...]"""

import json, os, sys, argparse
from datetime import datetime, timezone

# Default symbols if none provided
DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META',
                   'SPY', 'QQQ', 'IWM', 'XLF', 'XLE', 'XLK', 'GLD', 'TLT']

def fetch_quotes(symbols):
    try:
        import yfinance as yf
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yfinance'], check=True)
        import yfinance as yf

    results = []
    errors = []
    for sym in symbols:
        sym = sym.strip().upper()
        if not sym:
            continue
        try:
            tk = yf.Ticker(sym)
            info = tk.fast_info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            prev_close = info.get('previousClose')
            change = round(price - prev_close, 2) if price and prev_close else None
            change_pct = round((price / prev_close - 1) * 100, 2) if price and prev_close else None

            results.append({
                'symbol': sym,
                'price': price,
                'change': change,
                'change_pct': change_pct,
                'prev_close': prev_close,
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'name': info.get('longName') or info.get('shortName') or sym,
                'currency': info.get('currency', 'USD'),
                'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
            print(f'  ✅ {sym}: {price} ({change_pct}%)')
        except Exception as e:
            errors.append({'symbol': sym, 'error': str(e)})
            print(f'  ❌ {sym}: {e}')

    return {'quotes': results, 'errors': errors, 'count': len(results), 'ts': datetime.now(timezone.utc).isoformat()}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('symbols', nargs='?', default='')
    parser.add_argument('--out', default='')
    args = parser.parse_args()

    if args.symbols:
        syms = [s.strip().upper() for s in args.symbols.split(',') if s.strip()]
    else:
        syms = DEFAULT_SYMBOLS

    print(f'Fetching {len(syms)} symbols via yfinance...')
    data = fetch_quotes(syms)

    out_dir = args.out or f"data/yfinance/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/quotes.json"
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'\nSaved: {out_path} ({data["count"]} quotes)')

    # Also output summary for stdout (usable by caller)
    for q in data['quotes']:
        print(f'RESULT: {q["symbol"]} {q["price"]} {q["change"]} {q["change_pct"]}')
