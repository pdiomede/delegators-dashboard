# Delegators Dashboard – The Graph Network
This project generates an interactive HTML dashboard to monitor live **delegation** and **undelegation** activity on [The Graph Network](https://thegraph.com/).  
It highlights recent activity by delegators, indexed by timestamp, indexer, token amount, and event type.

**Live Dashboard:**  
🔗 [graphtools.pro/delegators](https://graphtools.pro/delegators/)

🧪 This dashboard is part of [**Graph Tools Pro**](https://graphtools.pro), a community-driven initiative to provide useful, independent analytics tools for The Graph ecosystem.

---

## 📌 Features

- Live dashboard for the most recent delegation and undelegation events on **Arbitrum** (withdrawals excluded)
- **Exact GRT amounts** per transaction — powered by the custom [`graph-delegation-events`](./subgraph/README.md) subgraph
- **Tx column** — transaction hash per row, linked to [Arbiscan](https://arbiscan.io)
- ENS name resolution for delegator and indexer addresses
- Avatar integration for indexers (via subgraph metadata)
- Light/dark mode with theme toggle
- **Time-range filter** — LAST 30 DAYS (default) / LAST 90 DAYS
- Filtering by event type (Delegations / Undelegations) and GRT thresholds
- **Paginated table** — 50 rows per page, integrated with all filters and search
- CSV download — respects current filters (time range, event type, GRT, search)
- Clean, responsive layout with semantic HTML5
- Fully client-side (static file based, no backend needed)
- Social sharing card (og:image / twitter:card) for X, LinkedIn and other platforms

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
├── 📂 reports/
│   ├── 📜 delegators.csv            # Generated CSV export
│   ├── 📜 index.html                # Generated HTML dashboard
│   └── 📜 social-card.jpeg          # Social sharing card (og:image) — deployed once
└── 📂 subgraph/                     # Custom subgraph (graph-delegation-events) — deployed on The Graph Network
    ├── 📜 README.md                 # Subgraph docs: schema, events, deploy instructions
    ├── 📜 schema.graphql            # DelegationEvent entity schema
    ├── 📜 subgraph.yaml             # Manifest: L2 staking contract on Arbitrum
    ├── 📜 package.json              # Graph CLI scripts
    ├── 📂 abis/
    │   └── 📜 L2Staking.json        # ABI for the Graph L2 staking contract
    └── 📂 src/
        └── 📜 mapping.ts            # AssemblyScript event handlers
```

---

## 🔗 Subgraphs Used

| Role | Subgraph | ID | Auth |
|---|---|---|---|
| Delegation events ✅ | graph-delegation-events *(custom)* | `GRAPH_DELEGATION_EVENTS` env var | `GRAPH_API_KEY` |
| Indexer metadata/avatars | Graph Network Arbitrum | `DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp` | `GRAPH_API_KEY` |
| ENS names | ENS Subgraph | `5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH` | `ENS_API_KEY` |
| Delegation events *(retired)* | Graph Analytics Arbitrum | `AgV4u2z1BFZKSj4Go1AdQswUGW2FcAtnPhifd4V7NLVz` | — |

---

## 🧩 Custom Subgraph — `graph-delegation-events`

> **Status:** Deployed on The Graph Network. Source code in [`./subgraph/`](./subgraph/).  
> Full documentation → **[subgraph/README.md](./subgraph/README.md)**

**`graph-delegation-events`** is a purpose-built subgraph for indexing delegation-side staking activity from The Graph Network's staking contract on Arbitrum One. It is the primary data source for this dashboard since **v2.0.0**.

Its objective is to provide an **event-level record** of delegation and undelegation flows, capturing the **exact GRT delta** for each on-chain transaction rather than the latest aggregate stake state. Unlike state-based entities such as `delegatedStakes` — which only expose the current balance of a delegator-indexer position — this subgraph models the underlying staking events directly. That makes it possible to show precise GRT amounts for every delegation, top-up, undelegation, and withdrawal.

It supports both **legacy** (pre-Horizon) and **Horizon** (post-Dec 2025) event formats.

### What it indexes

| Era | Contract Event | `eventType` |
|---|---|---|
| Legacy | `StakeDelegated` | `delegation` |
| Legacy | `StakeDelegatedLocked` | `undelegation` |
| Legacy | `StakeDelegatedWithdrawn` | `withdrawal` |
| Horizon | `TokensDelegated` | `delegation` |
| Horizon | `TokensUndelegated` | `undelegation` |
| Horizon | `DelegatedTokensWithdrawn` | `withdrawal` |

### Contract

- **Network:** Arbitrum One
- **Address:** [`0x00669A4CF01450B64E8A2A20E9b1FCB71E61eF03`](https://arbiscan.io/address/0x00669A4CF01450B64E8A2A20E9b1FCB71E61eF03)
- **Start block:** `42,440,000`

For the full schema, example queries, and deploy instructions, see **[subgraph/README.md](./subgraph/README.md)**.

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
# API key for The Graph gateway (used for all subgraph queries)
# Get yours at: https://thegraph.com/studio/apikeys/
GRAPH_API_KEY=[api-key]

# Subgraph ID for the custom graph-delegation-events subgraph (required)
# Find it in Subgraph Studio or The Graph Explorer
GRAPH_DELEGATION_EVENTS=[subgraph-id]

# Optional: separate API key for ENS subgraph queries (falls back to GRAPH_API_KEY)
# ENS_API_KEY=[api-key]

# Filter out delegations below this GRT amount
GRT_SIZE=10000

# Update cadence shown in the dashboard header (e.g. "updated every 8 hours")
UPDATE_CADENCE_HOURS=8

# ENS cache file path (relative to script dir unless absolute); delete to force a full refresh
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
- `GRAPH_DELEGATION_EVENTS` must be set in `.env` — the script raises a clear error on startup if missing or still set to the placeholder value
- Since v2.0.0, delegation data comes from the **custom `graph-delegation-events` subgraph** (see [`subgraph/README.md`](./subgraph/README.md)), which exposes exact per-transaction GRT amounts and transaction hashes
- ENS names are cached locally (default: `ens_cache.json` in script dir) for performance (configurable TTL via `ENS_CACHE_EXPIRY_HOURS`); a corrupt cache file is handled gracefully (auto-reset to empty)
- The script fetches all delegation events from the **last 90 days** (up to 100,000 records); the Graph gateway caps `first` at 1000 per query, so pagination is automatic
- `run_delegators_vps.sh` is a VPS-specific variant that also copies the generated reports into the nginx web root (`/var/www/graphtools.pro/delegators/`)
- If `ENS_API_KEY` is not set in `.env`, it silently falls back to `GRAPH_API_KEY`

---

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

## 📊 Powered By

- 🧠 [The Graph](https://thegraph.com)
- 📛 ENS (Ethereum Name Service)
- 🧩 Python, HTML5, CSS3, DataTables.js
- 🌐 GitHub Pages / any static web host
