#!/usr/bin/env python3
"""News Relay — produces bilingual daily briefing as readable Markdown.
Format mirrors skyflyld/german-daily-news: YYYY/MM/YYYY-MM-DD.md"""

import json, os, re, html
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests', 'lxml'], check=True)
    import requests
    from lxml import html as lxml_html

UA = 'Mozilla/5.0 (X11; Linux x86_64) NewsRelay/1.0'
TODAY = datetime.now(timezone.utc)
DATE_STR = TODAY.strftime('%Y-%m-%d')
YEAR = TODAY.strftime('%Y')
MONTH = TODAY.strftime('%m')

OUT_DIR = f"news/{YEAR}/{MONTH}"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = f"{OUT_DIR}/{DATE_STR}.md"

# ── Collect news sections ──
sections = []

# ── 1. WSJ Business ──
print("[1/5] WSJ Business...")
wsj_items = []
try:
    r = requests.get('https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
                     headers={'User-Agent': UA}, timeout=20)
    for m in re.finditer(r'<item>.*?</item>', r.text, re.DOTALL):
        item = m.group()
        def ex(tag):
            mm = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', item, re.DOTALL)
            return html.unescape(mm.group(1).strip()) if mm else ''
        title = ex('title')
        desc = re.sub(r'<[^>]+>', '', ex('description'))[:300]
        link = ex('link')
        creator = ex('dc:creator')
        if title:
            wsj_items.append((title, desc, link, creator))
    sections.append(('💰 财经 / Business (WSJ)', wsj_items[:8]))
except Exception as e:
    sections.append(('💰 财经 / Business (WSJ)', [f'⚠️ 获取失败: {e}']))

# ── 2. AP News ──
print("[2/5] AP News...")
ap_items = []
try:
    import lxml.html
    r = requests.get('https://apnews.com', headers={'User-Agent': UA}, timeout=20)
    tree = lxml.html.fromstring(r.text)
    # Extract headlines from likely containers
    for el in tree.xpath('//a[contains(@href, "/article/")]'):
        txt = el.text_content().strip()
        href = el.get('href', '')
        if len(txt) > 30 and not href.startswith('http'):
            href = 'https://apnews.com' + href
        if len(txt) > 30 and txt not in [x[0] for x in ap_items]:
            ap_items.append((txt[:200], href))
    sections.append(('🌍 国际新闻 / AP News', ap_items[:10]))
except Exception as e:
    sections.append(('🌍 国际新闻 / AP News', [f'⚠️ 获取失败: {e}']))

# ── 3. Federal Reserve ──
print("[3/5] Federal Reserve...")
fed_items = []
try:
    r = requests.get('https://www.federalreserve.gov/newsevents/pressreleases.htm',
                     headers={'User-Agent': UA}, timeout=20)
    for m in re.finditer(r'<a\s+href="([^"]*press[^"]*)">\s*([^<]+)', r.text):
        u, t = m.group(1), m.group(2).strip()
        if not u.startswith('http'):
            u = 'https://www.federalreserve.gov' + u
        fed_items.append((t, u))
    sections.append(('🏛️ 美联储 / Federal Reserve', fed_items[:8]))
except Exception as e:
    sections.append(('🏛️ 美联储 / Federal Reserve', [f'⚠️ 获取失败: {e}']))

# ── 4. FRED Macro ──
print("[4/5] FRED data...")
fred_series = [
    ('GDP', 'GDP (Gross Domestic Product)'),
    ('UNRATE', 'Unemployment Rate'),
    ('CPIAUCSL', 'CPI (Consumer Price Index)'),
    ('FEDFUNDS', 'Fed Funds Rate'),
    ('SP500', 'S&P 500 (Index)'),
    ('DGS10', '10-Year Treasury'),
    ('T5YIE', '5-Year Breakeven Inflation'),
    ('M2SL', 'M2 Money Supply'),
]
macro_lines = []
for sid, name in fred_series:
    try:
        r = requests.get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?series_id={sid}',
                         headers={'User-Agent': UA}, timeout=15)
        lines = r.text.strip().split('\n')
        if len(lines) >= 2:
            last = lines[-1].split(',')
            val = last[-1] if len(last) > 1 else 'N/A'
            dt = last[0] if len(last) > 1 else ''
            macro_lines.append(f'- **{name}** ({sid}): {val} (as of {dt})')
    except:
        macro_lines.append(f'- **{name}** ({sid}): ⚠️ unavailable')

sections.append(('📊 宏观指标 / FRED Economic Data', macro_lines))

# ── 5. Market Snapshot ──
print("[5/5] Market snapshot...")
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'SPY', 'QQQ', 'DIA']
quote_lines = []
for t in tickers:
    try:
        r = requests.get(
            f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={t}&apikey=demo',
            headers={'User-Agent': UA}, timeout=15
        )
        d = r.json()
        gq = d.get('Global Quote', {})
        price = gq.get('05. price', 'N/A')
        change = gq.get('10. change percent', 'N/A')
        vol = gq.get('06. volume', 'N/A')
        if change != 'N/A':
            emoji = '🟢' if float(change.replace('%','')) >= 0 else '🔴'
        else:
            emoji = '⚪'
        quote_lines.append(f'- {emoji} **{t}**: ${price} ({change}) — Vol: {vol}')
    except:
        quote_lines.append(f'- ⚠️ **{t}**: failed')

sections.append(('📈 市场快照 / Market Snapshot', quote_lines))

# ── Build markdown ──
md = f"""# 📡 每日新闻简报 / Daily News Briefing
**{DATE_STR} ({TODAY.strftime('%A')})** — 来源: WSJ · AP News · Federal Reserve · FRED · Alpha Vantage

---

"""

for section_title, items in sections:
    md += f"## {section_title}\n\n"
    for item in items:
        if isinstance(item, tuple):
            title, desc, link, creator = item if len(item) == 4 else (*item, '', '')
            md += f"**{title}**"
            if creator:
                md += f" — *{creator}*"
            md += f"\n> {desc[:200]}"
            if link:
                md += f"\n🔗 {link}"
            md += "\n\n"
        elif isinstance(item, str):
            md += f"{item}\n\n"
        elif isinstance(item, tuple) and len(item) == 2:
            # (title, link) from AP/Fed
            md += f"- **{item[0]}**\n  🔗 {item[1]}\n\n"

md += f"""---

*自动采集于 {TODAY.strftime('%Y-%m-%d %H:%M UTC')} · 数据仅供个人参考*

*Powered by [jasoneip01-pixel/relay](https://github.com/jasoneip01-pixel/relay)*
"""

with open(OUT_PATH, 'w') as f:
    f.write(md)
print(f"✅ Wrote {OUT_PATH} ({len(md)} chars)")

# ── Update news/README.md index ──
idx_path = 'news/README.md'
if os.path.exists(idx_path):
    with open(idx_path) as f:
        idx = f.read()
    if DATE_STR not in idx:
        # Insert new link row right after the table header (find "|---|")
        link_line = f"| {DATE_STR} | [{DATE_STR}.md]({YEAR}/{MONTH}/{DATE_STR}.md) |\n"
        marker = '|---|\n'
        if marker in idx:
            pos = idx.index(marker) + len(marker)
            idx = idx[:pos] + link_line + idx[pos:]
        else:
            idx += link_line
        with open(idx_path, 'w') as f:
            f.write(idx)
        print(f"✅ Updated {idx_path}")
