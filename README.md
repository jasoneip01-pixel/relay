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

## 📡 每日新闻简报 / Daily News Brief

> 中英双语 · 每天 08:30/20:30 BJT 更新（00:30/12:30 UTC）
> 格式：`news/YYYY/MM/YYYY-MM-DD.md` — 可直接在 GitHub 上阅读

### 📋 内容说明

| 板块 | 来源 | 中文说明 |
|------|------|---------|
| 💰 财经 | WSJ Business RSS | 华尔街日报商业版头条，附英文原文标题和中译摘要 |
| 🌍 国际 | AP News | 美联社全球要闻精选，标题+链接 |
| 🏛️ 美联储 | Federal Reserve | 最新货币政策声明/发布会/监管公告 |
| 📊 宏观 | FRED (St. Louis Fed) | 8 项关键指标：GDP / 失业率 / CPI / 联邦基金利率 / S&P500 / 10年国债 / 盈亏平衡通胀 / M2 货币供应 |
| 📈 市场 | Alpha Vantage | 10 只主要标的实时快照：AAPL/MSFT/GOOGL/AMZN/TSLA/META/NVDA/SPY/QQQ/DIA |

### 👉 浏览新闻

→ [news/ 目录](news/) — 按日期查看所有简报
