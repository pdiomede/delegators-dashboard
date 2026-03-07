# Delegators Dashboard – The Graph Network
This project generates an interactive HTML dashboard to monitor live **delegation** and **undelegation** activity on [The Graph Network](https://thegraph.com/).  
It highlights recent activity by delegators, indexed by timestamp, indexer, token amount, and event type.

> **v1.1.0** — Table pagination (50 rows/page), fixed data freshness (most recent records first), GitHub link in footer, author credit.

**Live Dashboard:**  
🔗 [graphtools.pro/delegators](https://graphtools.pro/delegators/)

🧪 This dashboard is part of [**Graph Tools Pro**](https://graphtools.pro), a community-driven initiative to provide useful, independent analytics tools for The Graph ecosystem.

---

## 📌 Features

- Live dashboards for the most recent delegation/undelegation events on **Arbitrum**
- ENS name resolution for delegator and indexer addresses
- Avatar integration for indexers (via subgraph metadata)
- Light/dark mode with theme toggle
- Filtering by event type and GRT thresholds
- **Paginated table** — 50 rows per page, integrated with all filters and search
- CSV download of all listed events
- Clean, responsive layout with semantic HTML5
- Fully client-side (static file based, no backend needed)

---

## 📂 Project Structure

```
📁 delegators/
├── 📜 fetch_delegators_metrics.py   # Main script: fetches data and renders dashboard
├── 📜 run_delegators.sh             # Shell script: sets up venv and runs the pipeline (local)
├── 📜 run_delegators_vps.sh         # Shell script: runs the pipeline + deploys to nginx (VPS)
├── 📜 requirements.txt              # Python dependencies
├── 📜 .env                          # API keys and config (excluded via .gitignore)
├── 📂 logs/                         # Auto-generated log files
└── 📂 reports/
    ├── 📜 delegators.csv            # Generated CSV export
    └── 📜 index.html                # Generated HTML dashboard
```

---

## 🔗 Subgraphs Used

| Role | Subgraph | ID | Auth |
|---|---|---|---|
| Delegation events | Graph Analytics Arbitrum | `AgV4u2z1BFZKSj4Go1AdQswUGW2FcAtnPhifd4V7NLVz` | `GRAPH_API_KEY` |
| Indexer metadata/avatars | Graph Network Arbitrum | `DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp` | `GRAPH_API_KEY` |
| ENS names | ENS Subgraph | `5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH` | `ENS_API_KEY` (full URL) |

---

## 🚀 How to Use

### Option A — One-command run (recommended)

```bash
git clone https://github.com/pdiomede/delegators-dashboard.git
cd delegators-dashboard
cp .env.example .env   # then fill in your API keys
./run_delegators.sh
```

`run_delegators.sh` automatically creates the virtual environment, installs all dependencies, and runs the script.

### Option B — Manual setup

1. Clone the repo:
```bash
git clone https://github.com/pdiomede/delegators-dashboard.git
cd delegators-dashboard
```

2. Create a `.env` file:
```bash
# API key for The Graph gateway (used for delegation + avatar subgraphs)
# Get yours at: https://thegraph.com/studio/apikeys/
GRAPH_API_KEY=[api-key]

# Full ENS subgraph URL with its own dedicated API key embedded
ENS_API_KEY=https://gateway.thegraph.com/api/[api-key]/subgraphs/id/5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH

# Records to fetch (gateway caps each page at 1000; pagination is automatic)
TRANSACTION_COUNT=5000

# Filter out delegations below this GRT amount
GRT_SIZE=10000

# ENS cache file path (relative to script dir); delete to force a full refresh
ENS_CACHE_FILE=ens_cache.json

# Hours before a cached ENS name is re-fetched (0 = always refresh; 168 = weekly)
ENS_CACHE_EXPIRY_HOURS=48
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the script:
```bash
python3 fetch_delegators_metrics.py
```

5. Open `reports/index.html` in your browser.

---

## 🛡️ Notes

- `.env` and `.DS_Store` are excluded via `.gitignore`
- ENS names are cached locally in `ens_cache.json` for performance (configurable TTL via `ENS_CACHE_EXPIRY_HOURS`). Delete the file to force a full refresh.
- The dashboard uses the **Graph Analytics Arbitrum** subgraph for delegation data — individual transaction hashes are not available in this subgraph; the tx column shows "N/A"
- The Graph gateway caps `first` at **1000 per query**; the script automatically paginates using a timestamp cursor, always fetching the most recently active records first
- `run_delegators_vps.sh` is a VPS-specific variant that also copies the generated reports into the nginx web root (`/var/www/graphtools.pro/delegators/`)
- If `ENS_API_KEY` is missing from `.env`, ENS lookups are silently skipped (addresses shown as-is) rather than crashing

---

## 📋 Changelog

### v1.1.0
- Added table pagination: 50 rows per page with first/prev/page-numbers/next/last controls
- Pagination is fully integrated with event type filter, GRT filter, and search box
- Fixed data freshness: records now fetched ordered by `lastDelegatedAt`/`lastUndelegatedAt` DESC so the most recent activity always appears first (previously oldest records were shown)
- Updated footer: author credit for Paolo Diomede with link, GitHub repo link with icon
- Bumped version to 1.1.0

### v1.0.9
- Fixed `log_message` being called before `log_file` was defined (latent `NameError`)
- Fixed typo `TRANSCATION_COUNT` → `TRANSACTION_COUNT` in `fetch_metrics()`
- Fixed missing `<tr>` opening tag in HTML table header (malformed HTML)
- Fixed `ENS_SUBGRAPH_URL` being `None` when `ENS_API_KEY` is missing — now skips gracefully
- Fixed `generate_delegators_to_csv` crashing with `IndexError` on empty event list
- Fixed JS filter: `"Delegation"` was incorrectly matching rows labelled `"Undelegation"`
- Removed dead code: `fetch_ens_name2` (duplicate of `fetch_ens_name`, never called)
- Fixed ENS cache timestamp comparison using `.astimezone()` instead of `.replace(tzinfo=)`
- Added empty-event guard in `generate_delegators_to_html`
- Removed unused `order_by` parameter from `_paginate()`

### v1.0.8
- Migrated to Arbitrum subgraphs (Graph Analytics + Graph Network)
- Added `id_gt` cursor pagination — `TRANSACTION_COUNT` can safely exceed 1000
- Added explicit `RuntimeError` when subgraph returns errors instead of data
- Added `EnvironmentError` guard if `GRAPH_API_KEY` is missing
- Added `run_delegators_vps.sh` for VPS deployment to nginx
- ENS lookup now uses dedicated `ENS_API_KEY` URL from `.env`
- Thousands separator on transaction count in dashboard header

---

## 📊 Powered By

- 🧠 [The Graph](https://thegraph.com)
- 📛 ENS (Ethereum Name Service)
- 🧩 Python, HTML5, CSS3, DataTables.js
- 🌐 GitHub Pages / any static web host
