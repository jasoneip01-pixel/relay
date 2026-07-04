#!/usr/bin/env python3
"""News Relay Collector — run inside GitHub Actions (US servers)
Collects from sources blocked/bypassed by GFW and writes structured JSON."""

import json, os, re, html
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', 'lxml'], check=True)
    import requests

OUT = f"data/news/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (X11; Linux x86_64) NewsRelay/1.0'

def save(name, data):
    path = f"{OUT}/{name}.json"
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  wrote {path} ({len(data.get('items',[]))} items)")

# ── 1. WSJ US Business RSS ──
print("[1/5] WSJ RSS...")
try:
    r = requests.get('https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
                     headers={'User-Agent': UA}, timeout=20)
    items = []
    for m in re.finditer(r'<item>.*?</item>', r.text, re.DOTALL):
        item = m.group()
        def ex(tag):
            mm = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', item, re.DOTALL)
            return html.unescape(mm.group(1).strip()) if mm else ''
        items.append({
            'title': ex('title'),
            'desc': re.sub(r'<[^>]+>', '', ex('description'))[:500],
            'link': ex('link'),
            'pubDate': ex('pubDate'),
            'creator': ex('dc:creator'),
        })
    save('wsj', {'source': 'WSJ.com US Business RSS', 'ts': r.headers.get('Date',''), 'items': items})
except Exception as e:
    save('wsj', {'source': 'WSJ RSS', 'error': str(e), 'items': []})

# ── 2. AP News ──
print("[2/5] AP News...")
try:
    r = requests.get('https://apnews.com', headers={'User-Agent': UA}, timeout=20)
    text = re.sub(r'<script[^>]*>.*?</script>', '', r.text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Extract likely headlines (capitalized phrases)
    lines = [l.strip() for l in text.split('.') if len(l.strip()) > 40]
    save('apnews', {'source': 'AP News', 'ts': r.headers.get('Date',''), 'snippets': lines[:30]})
except Exception as e:
    save('apnews', {'source': 'AP News', 'error': str(e), 'snippets': []})

# ── 3. Federal Reserve ──
print("[3/5] Federal Reserve...")
try:
    r = requests.get('https://www.federalreserve.gov/newsevents/pressreleases.htm',
                     headers={'User-Agent': UA}, timeout=20)
    releases = re.findall(r'<a\s+href="([^"]+press[^"]*)">\s*([^<]+)', r.text)
    items = [{'title': t.strip(), 'link': 'https://www.federalreserve.gov' + u if u.startswith('/') else u}
             for u, t in releases[:20]]
    save('fed', {'source': 'Federal Reserve', 'ts': r.headers.get('Date',''), 'items': items})
except Exception as e:
    save('fed', {'source': 'Fed', 'error': str(e), 'items': []})

# ── 4. FRED economic data ──
print("[4/5] FRED data...")
fred_series = [
    ('GDP', 'GDP'), ('UNRATE', 'Unemployment'), ('CPIAUCSL', 'CPI'),
    ('FEDFUNDS', 'Fed Funds Rate'), ('SP500', 'S&P 500'),
]
series_data = []
for sid, name in fred_series:
    try:
        r = requests.get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?series_id={sid}',
                         headers={'User-Agent': UA}, timeout=15)
        lines = r.text.strip().split('\n')
        if len(lines) >= 2:
            last = lines[-1].split(',')
            series_data.append({'id': sid, 'name': name, 'latest_value': last[-1] if len(last) > 1 else 'N/A', 'date': last[0]})
    except:
        series_data.append({'id': sid, 'name': name, 'error': 'failed'})
save('fred', {'source': 'FRED', 'series': series_data})

# ── 5. Alpha Vantage market snapshot ──
print("[5/5] Alpha Vantage (demo)...")
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'SPY', 'QQQ']
quotes = []
for t in tickers:
    try:
        r = requests.get(
            f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={t}&apikey=demo',
            headers={'User-Agent': UA}, timeout=15
        )
        d = r.json()
        gq = d.get('Global Quote', {})
        quotes.append({
            'symbol': t,
            'price': gq.get('05. price', 'N/A'),
            'change_pct': gq.get('10. change percent', 'N/A'),
            'volume': gq.get('06. volume', 'N/A'),
        })
    except:
        quotes.append({'symbol': t, 'error': 'failed'})
save('market', {'source': 'Alpha Vantage', 'ts': datetime.now(timezone.utc).isoformat(), 'quotes': quotes})

print(f"\nDone. All saved to {OUT}/")
