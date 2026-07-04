# Relay — IP-block bypass via GitHub Actions

GitHub Actions US runner relay for fetching blocked websites from behind GFW.

## How it works

```
China VPC (IP-blocked) ──×── target.com
                              │
GitHub US Runner ─────────────✅── target.com
       │
       └── writes to this repo
              │
China VPC ─────✅ git pull (readable)
```

## Workflows

| Workflow | Trigger | What it does |
|:---|:---|:---|
| `news-relay.yml` | schedule + dispatch | Fetch WSJ/AP/Fed/FRED/market data |
| `youtube-relay.yml` | dispatch only | Fetch YouTube video metadata |

## Usage

```bash
# Trigger a relay
curl -X POST \
  https://api.github.com/repos/jasoneip01-pixel/relay/actions/workflows/<name>.yml/dispatches \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"ref":"main","inputs":{"url":"<url>"}}'

# Read results
cd relay-repo && git pull && cat data/<YYYY-MM-DD>/<slug>.json
```

## Sources accessible via this relay

| Source | Method | Tier |
|:---|:---|:---|
| YouTube (metadata) | dispatch | — |
| WSJ (US Business RSS) | scheduled | 🟢 T1 |
| AP News (headlines) | scheduled | 🟢 T1 |
| Federal Reserve (releases) | scheduled | 🟢 T1 |
| FRED (economic data) | scheduled | 🟢 T1 |
| Alpha Vantage (market) | scheduled | 🟡 T2 |

For direct-access sources (no relay needed), see `skills/arist-self/foreign-channel/references/channel-registry.md`
