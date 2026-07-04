#!/usr/bin/env python3
"""YouTube Relay — fetches page metadata from GH US runner.
Multi-strategy extraction: HTML patterns → noembed → schema → oembed."""

import json, os, re, html, sys
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    import subprocess as sp
    sp.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
    import requests

OUT = f"data/youtube/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--url', required=True)
args = parser.parse_args()

url = args.url
vid_id = None
if 'watch?v=' in url:
    vid_id = url.split('watch?v=')[1].split('&')[0]
elif 'youtu.be/' in url:
    vid_id = url.split('youtu.be/')[1].split('?')[0]
elif '/live/' in url:
    vid_id = url.split('/live/')[1].split('?')[0]

slug = vid_id or url.split('/')[-1][:20]

result = {
    'url': url,
    'video_id': vid_id,
    'fetched_at': datetime.now(timezone.utc).isoformat(),
}

def try_oembed(vid):
    """Try multiple oembed providers."""
    urls_to_try = [
        f'https://noembed.com/embed?url=https://www.youtube.com/watch?v={vid}',
        f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json',
    ]
    for u in urls_to_try:
        try:
            r = requests.get(u, headers={'User-Agent': UA}, timeout=15)
            if r.status_code == 200:
                d = r.json()
                if d.get('title'):
                    return {
                        'provider': u.split('/')[2],
                        'title': d.get('title', ''),
                        'author': d.get('author_name', ''),
                        'html': d.get('html', '')[:200],
                        'thumbnail': d.get('thumbnail_url', ''),
                    }
        except Exception as e:
            continue
    return None

try:
    # Strategy 1: noembed.com (most reliable, free, no API key)
    if vid_id:
        oembed = try_oembed(vid_id)
        if oembed:
            result['title'] = oembed['title']
            result['channel'] = oembed['author']
            result['oembed_provider'] = oembed['provider']
            if oembed.get('thumbnail'):
                result['thumbnail'] = oembed['thumbnail']
    
    # Strategy 2: Fetch the YouTube page for additional metadata  
    r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}, timeout=20)
    result['status_code'] = r.status_code
    result['response_size'] = len(r.text)
    
    page = r.text[:5000]
    
    # Detect bot wall
    bot_markers = ['captcha', 'recaptcha', 'verify you are human', 'Before you continue',
                   'unusual traffic', 'Sign in to confirm']
    result['bot_wall'] = any(m.lower() in page.lower() for m in bot_markers)
    
    # Try OG meta (may not exist in JS-rendered page but try anyway)
    for meta_key, field in [('og:title', 'og_title'), ('og:description', 'og_desc')]:
        m = re.search(f'<meta\\s+property="{meta_key}"\\s+content="([^"]*)"', page)
        if m:
            result[field] = html.unescape(m.group(1))
    
    # Try <title> tag
    m = re.search(r'<title>([^<]+)</title>', page[:2000])
    if m:
        result['html_title'] = html.unescape(m.group(1).strip())
    
    # Try JSON-LD schema
    m = re.search(r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', page, re.DOTALL)
    if m:
        try:
            ld = json.loads(m.group(1))
            if isinstance(ld, dict):
                result['schema_name'] = ld.get('name', '')
                result['schema_desc'] = ld.get('description', '')[:500]
        except:
            pass
    
    # Fill best available
    if not result.get('title'):
        result['title'] = result.get('og_title') or result.get('schema_name') or result.get('html_title') or ''
    if not result.get('channel') and result.get('og_title'):
        # Try to parse channel from og:title "xxx - YouTube"
        t = result['og_title']
        if ' - YouTube' in t:
            result['title'] = t.replace(' - YouTube', '')
    
    result['raw_snippet'] = page[:2000]
    
    path = f"{OUT}/{slug}.json"
    with open(path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {slug}.json — {result.get('response_size',0)} bytes → title='{result.get('title','?')[:120]}'")

except Exception as e:
    result['error'] = str(e)[:300]
    path = f"{OUT}/{slug}.json"
    with open(path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  ❌ {slug}: {e}")

print(f"\nDone → {OUT}/")
