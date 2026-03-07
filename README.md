# Delegators Dashboard – The Graph Network
This project generates an interactive HTML dashboard to monitor live **delegation** and **undelegation** activity on [The Graph Network](https://thegraph.com/).  
It highlights recent activity by delegators, indexed by timestamp, indexer, token amount, and event type.

> **v1.0.8** — Arbitrum subgraphs, paginated fetching (up to 5 000 records), ENS caching, avatar integration.

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

| Role | Subgraph | ID |
|---|---|---|
| Delegation events | Graph Analytics Arbitrum | `AgV4u2z1BFZKSj4Go1AdQswUGW2FcAtnPhifd4V7NLVz` |
| Indexer metadata/avatars | Graph Network Arbitrum | `DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp` |
| ENS names | ENS Subgraph | `5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH` |

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
# API key for The Graph gateway — https://thegraph.com/studio/apikeys/
GRAPH_API_KEY=your_graph_api_key

# Full ENS subgraph URL (API key embedded)
ENS_API_KEY=https://gateway.thegraph.com/api/<your-key>/subgraphs/id/5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH

# Records to fetch (gateway caps each page at 1000; pagination is automatic)
TRANSACTION_COUNT=5000

# Filter out delegations below this GRT amount
GRT_SIZE=10000

# ENS cache file path (relative to script dir); delete to force full refresh
ENS_CACHE_FILE=ens_cache.json

# Hours before a cached ENS name is re-fetched (0 = always refresh)
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
- The Graph gateway caps `first` at **1000 per query**; the script automatically paginates using `id_gt` cursor pagination, so `TRANSACTION_COUNT` can safely be set above 1000
- `run_delegators_vps.sh` is a VPS-specific variant that also copies the generated reports into the nginx web root (`/var/www/graphtools.pro/delegators/`)

---

## 📊 Powered By

- 🧠 [The Graph](https://thegraph.com)
- 📛 ENS (Ethereum Name Service)
- 🧩 Python, HTML5, CSS3, DataTables.js
- 🌐 GitHub Pages / any static web host
