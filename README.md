# Delegators Dashboard – The Graph Network
This project generates an interactive HTML dashboard to monitor live **delegation** and **undelegation** activity on [The Graph Network](https://thegraph.com/).  
It highlights recent activity by delegators, indexed by timestamp, indexer, token amount, and event type.

> **v2.0.1** — Switched to custom `graph-delegation-events` subgraph: exact per-transaction GRT amounts, Tx hash column with Arbiscan links, withdrawal event type.

**Live Dashboard:**  
🔗 [graphtools.pro/delegators](https://graphtools.pro/delegators/)

🧪 This dashboard is part of [**Graph Tools Pro**](https://graphtools.pro), a community-driven initiative to provide useful, independent analytics tools for The Graph ecosystem.

---

## 📌 Features

- Live dashboard for the most recent delegation, undelegation, and withdrawal events on **Arbitrum**
- **Exact GRT amounts** per transaction — powered by the custom [`graph-delegation-events`](./subgraph/README.md) subgraph
- **Tx column** — transaction hash per row, linked to [Arbiscan](https://arbiscan.io)
- ENS name resolution for delegator and indexer addresses
- Avatar integration for indexers (via subgraph metadata)
- Light/dark mode with theme toggle
- Filtering by event type (Delegations / Undelegations / Withdrawals) and GRT thresholds
- **Paginated table** — 50 rows per page, integrated with all filters and search
- CSV download of all listed events
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

# Records to fetch (gateway caps each page at 1000; pagination is automatic)
TRANSACTION_COUNT=1000

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
- `GRAPH_DELEGATION_EVENTS` must be set in `.env` — the script raises a clear error on startup if missing or still set to the placeholder value
- Since v2.0.0, delegation data comes from the **custom `graph-delegation-events` subgraph** (see [`subgraph/README.md`](./subgraph/README.md)), which exposes exact per-transaction GRT amounts and transaction hashes
- ENS names are cached locally in `ens_cache.json` for performance (configurable TTL via `ENS_CACHE_EXPIRY_HOURS`); a corrupt cache file is handled gracefully (auto-reset to empty)
- The Graph gateway caps `first` at **1000 per query**; the script automatically paginates using a timestamp cursor, always fetching the most recently active records first
- `run_delegators_vps.sh` is a VPS-specific variant that also copies the generated reports into the nginx web root (`/var/www/graphtools.pro/delegators/`)
- If `ENS_API_KEY` is not set in `.env`, it silently falls back to `GRAPH_API_KEY`

---

## 📋 Changelog

### v2.0.0 ⭐ Major release
- **Switched data source** from `delegatedStakes` (state-based) to the custom `graph-delegation-events` subgraph (event-based)
- **Exact GRT amounts** for every event — delegations, top-ups, and undelegations all show the precise delta per transaction, not the total stake
- **New "Tx" column** — each row now shows the transaction hash (truncated) as a clickable link to Arbiscan
- **New "Withdrawal" event type** (`🔓 Withdrawal`) — tokens withdrawn after the unbonding period, previously not tracked
- **Removed top-up distinction** — no longer needed since every row is a true on-chain transaction with an exact amount
- **Stats panel** — "Top-up Events" card replaced with "Withdrawals" count; "Total Delegated" now reflects all delegation transactions accurately
- **Filter bar** — "New Delegations" and "Top-ups" replaced with single "✅ Delegations" filter; "🔓 Withdrawals" filter added
- Breadcrumb now shows correct transaction count (no longer doubled)
- Requires `GRAPH_DELEGATION_EVENTS` in `.env` (custom subgraph ID)

### v1.4.3
- Replaced invisible `➕` emoji on top-up rows with a styled amber `[+]` badge (visible on both dark and light mode)
- Same badge applied to the Top-ups filter button
- Updated JS filter match from `"➕ Top-up"` to `"Top-up"` to align with new label

### v1.4.2
- Added tooltips on event type labels in the table (hover to see definition of New Delegation / Top-up / Undelegation)
- Added tooltips on filter buttons with the same explanations
- Added `cursor: help` style on event type cells to hint that hovering shows info

### v1.4.1
- Fixed ENS lookups broken by `[api-key]` placeholder in `.env`
- `ENS_API_KEY` now holds just the key (not a full URL), falling back to `GRAPH_API_KEY` when not set
- `ENS_SUBGRAPH_URL` is now constructed consistently with other subgraph URLs
- Removed stale `global ENS_SUBGRAPH_URL` and `None` guard in `fetch_ens_name`

### v1.4.0
- Distinguished **New Delegation** (first-time stake) from **Top-up** (increase to existing position) using `createdAt` vs `lastDelegatedAt`
- Top-up rows show a tooltip explaining the amount is total stake, not delta
- Stats panel: renamed to "New Delegations", added "Top-up Events" count card, clarified Net label
- Added "➕ Top-ups" filter button
- Bumped version to 1.4.0

### v1.3.0
- Regenerated `social-card.jpeg` at correct 1200×630px with CTA button
- Updated `og:title` and `twitter:title` to optimal length (52 chars)
- Updated `og:description` and `twitter:description` to optimal length (140 chars)
- Changed "Generated on" line: removed version suffix, updated cadence to "every 24 hours"

### v1.2.1
- Added `social-card.jpeg` (1200×630) for rich social sharing previews on X, LinkedIn, etc.
- Updated `og:image` and `twitter:image` meta tags to point to the new card
- Fixed footer version not rendering (`{DASHBOARD_VERSION}` was inside a non-f-string)
- Fixed `run_delegators_vps.sh`: `social-card.jpeg` now only copied on first deploy (skipped if already present)
- Fixed `run_delegators_vps.sh`: `chown paolo:www-data` applied consistently to all deployed files

### v1.2.0
- Removed Tx column (transaction hashes unavailable from the Analytics subgraph)
- Refactored footer: `©Year Graph Tools Pro  |  Delegators Dashboard vX.X.X  |  Author: Paolo Diomede  |  View on GitHub`; version pulled dynamically from `DASHBOARD_VERSION`
- Fixed `tokens: float` → `int` in `DelegationEvent` (float loses precision on large wei values)
- Fixed favicon MIME type: `image/png` → `image/x-icon` for `.ico` file
- Fixed filter link `href="#"` causing page-top scroll on click → `javascript:void(0)`
- Fixed `run_query` not guarding against `payload["data"]` being `None`
- Replaced per-call cache file I/O in `fetch_ens_name` with a module-level in-memory dict (loaded once, saved on update)
- Protected ENS cache JSON load against corrupt/empty file (`JSONDecodeError` → graceful reset)
- Narrowed `fetch_indexer_avatar` exception catch from bare `Exception` to `requests.RequestException`
- Removed unnecessary `global` declarations in `generate_delegators_to_csv` and `generate_delegators_to_html`
- Fixed `window.scrollTo` firing on initial page load (added `_initialLoad` flag)
- Fixed `_paginate` timestamp boundary — switched from `_lt` to composite `_lte + id_lt` cursor to avoid skipping records that share a boundary timestamp
- Bumped version to 1.2.0

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
