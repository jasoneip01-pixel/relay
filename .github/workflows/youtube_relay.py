#!/usr/bin/env python3
"""YouTube Relay — fetches page metadata from GH US runner.
Triggered by workflow_dispatch with URL input."""

import json, os, re, html, sys
from datetime import datetime, timezone
try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], check=True)
    import requests

OUT = f"data/youtube/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (X11; Linux x86_64) YouTubeRelay/1.0'

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--url', help='Specific YouTube URL to fetch', required=True)
args = parser.parse_args()

def extract_all(html_text):
    """Try multiple extraction strategies."""
    result = {}
    raw_snippet = html_text[:3000]
    
    # Strategy 1: og:title + og:description (most reliable)
    for pattern, key in [('og:title', 'og_title'), ('og:description', 'og_description'),
                         ('og:video:tag', 'tags')]:
        m = re.search(f'<meta\\s+property="{pattern}"\\s+content="([^"]*)"', html_text)
        if m:
            val = html.unescape(m.group(1))
            if key == 'tags':
                result.setdefault('tags', []).append(val)
            else:
                result[key] = val
    
    # Strategy 2: schema.org data
    m = re.search(r'"name":\s*"([^"]+)"', html_text)
    if m and 'og_title' not in result:
        result['schema_title'] = html.unescape(m.group(1))
    
    # Strategy 3: ytInitialData
    m = re.search(r'var ytInitialData\s*=\s*(\{.+?\});\s*\n\s*</script>', html_text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            contents = data.get('contents', {}).get('twoColumnWatchNextResults', {})
            for section in contents.get('results', {}).get('results', {}).get('contents', []):
                p = section.get('videoPrimaryInfoRenderer', {})
                if p.get('title'):
                    result['yt_title'] = p['title'].get('runs', [{}])[0].get('text', '')
                    result['yt_views'] = p.get('viewCount', {}).get('videoViewCountRenderer', {}).get('viewCount', {}).get('simpleText', '')
                s = section.get('videoSecondaryInfoRenderer', {})
                if s.get('owner'):
                    result['yt_channel'] = s['owner'].get('videoOwnerRenderer', {}).get('title', {}).get('runs', [{}])[0].get('text', '')
                    result['yt_subs'] = s['owner'].get('videoOwnerRenderer', {}).get('subscriberCountText', {}).get('simpleText', '')
        except:
            pass
    
    # Strategy 4: oembed API fallback
    # (call separately since it's a different endpoint)
    
    # Strategy 5: Bot wall detection
    bot_markers = ['captcha', 'recaptcha', 'verify you are human', 'Before you continue',
                   'unusual traffic', 'Sign in to confirm']
    result['bot_wall'] = any(m.lower() in html_text[:5000].lower() for m in bot_markers)
    
    result['raw_snippet'] = raw_snippet
    return result


url = args.url
vid_id = None
if 'watch?v=' in url:
    vid_id = url.split('watch?v=')[1].split('&')[0]
elif 'youtu.be/' in url:
    vid_id = url.split('youtu.be/')[1].split('?')[0]

slug = vid_id or url.split('/')[-1][:20]

result = {
    'url': url,
    'video_id': vid_id,
    'fetched_at': datetime.now(timezone.utc).isoformat(),
}

try:
    print(f"Fetching: {url}")
    r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}, timeout=20)
    result['status_code'] = r.status_code
    result['response_size'] = len(r.text)
    
    page = r.text
    
    # Extract metadata from HTML
    meta = extract_all(page)
    result.update(meta)
    
    # Try oembed for title if OG failed
    if not meta.get('og_title') and vid_id:
        try:
            oe = requests.get(
                f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid_id}&format=json',
                headers={'User-Agent': UA}, timeout=10
            )
            if oe.status_code == 200:
                od = oe.json()
                result['oembed_title'] = od.get('title', '')
                result['oembed_author'] = od.get('author_name', '')
        except:
            pass
    
    # Best title
    result['title'] = meta.get('og_title') or meta.get('yt_title') or meta.get('oembed_title') or meta.get('schema_title') or ''
    result['channel'] = meta.get('oembed_author') or meta.get('yt_channel') or ''
    result['description'] = meta.get('og_description') or ''
    result['views'] = meta.get('yt_views') or ''
    result['tags'] = meta.get('tags', [])
    
    path = f"{OUT}/{slug}.json"
    with open(path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {slug}.json — {len(page)} bytes → title='{result['title']}'")
    
    if result.get('bot_wall'):
        print(f"  ⚠️ Bot wall detected in response!")

except Exception as e:
    result['error'] = str(e)[:300]
    path = f"{OUT}/{slug}.json"
    with open(path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  ❌ {slug}: {e}")

print(f"\nDone. Saved to {OUT}/")
