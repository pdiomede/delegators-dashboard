# Changelog

All notable changes to this project are documented here.  
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.0.1] — 2026-03-08

### Bug fixes — round 2 (general)

- **CSV datetime format** — `block_datetime` was serialised via `str(datetime)`, producing `2026-03-07 12:34:56+00:00` (non-standard); now explicitly calls `.isoformat()` for consistent ISO 8601 output
- **File encoding** — added `encoding='utf-8'` to both the HTML and CSV `open()` calls; emoji characters in the HTML (`🏠 📊 ✅ ❌ 🔓 🧹 💰`) could produce garbled output on non-UTF-8 platforms (common on Windows)
- **Unescaped `&` in HTML** — `& Analytics` in `<title>`, `og:title`, and `twitter:title` was invalid HTML; replaced with `&amp;` to pass validation and avoid issues with strict parsers
- **`grt_threshold` recomputed on every row** — the table loop was re-evaluating `GRT_SIZE * 10**18` for every event; now uses the variable already computed once in the stats block
- **Unnecessary `global` declarations** — `fetch_events()` and `fetch_metrics()` declared `global` for variables they only *read*, never assigned; removed (misleading and contrary to Python convention)
- **Noisy ENS cache-hit logs** — `"🧠 Using cached ENS for …"` was emitted for every indexer and delegator address lookup, generating ~2 000 log lines per 1 000-event run; removed
- **Stale ENS fallback on network failure** — when a cached ENS record was expired and the live re-fetch threw a network exception, `""` (raw hex) was returned; the last-known ENS name is now returned as a fallback with a log warning
- **Mid-pagination crash loses partial results** — if page N of a paginated fetch failed, all results from pages 1…N-1 were discarded and the script crashed; now catches `RuntimeError`/`RequestException`, logs a warning, and returns whatever was collected
- **Missing HTML success log** — `generate_delegators_to_html()` logged nothing on success while `generate_delegators_to_csv()` logged `✅ Saved CSV …`; added matching `✅ Saved HTML dashboard: …`
- **Invalid env-var values crash silently** — `int(os.getenv("TRANSACTION_COUNT", …))` and `int(os.getenv("GRT_SIZE", …))` raised a bare `ValueError` when set to an invalid value (e.g. `10k`); now raises `EnvironmentError` with a clear, actionable message before any log is written

---

## [2.0.0] — 2026-03-08

### Breaking change — new data source

- **Switched from `delegatedStakes` (state-based) to the custom `graph-delegation-events` subgraph (event-based)**; requires `GRAPH_DELEGATION_EVENTS` in `.env`

### New features

- **Exact GRT amounts** — every delegation, undelegation, and withdrawal row shows the precise GRT delta for that transaction, not an aggregate balance
- **Tx column** — each table row now shows the transaction hash (truncated `0x1234…abcd`) as a clickable link to [Arbiscan](https://arbiscan.io)
- **Withdrawal event type** (`🔓 Withdrawal`) — tokens withdrawn after the ~28-day unbonding period are now tracked as a distinct event type, previously invisible
- **Withdrawals filter** — new "🔓 Withdrawals" filter button; replaced "New Delegations / Top-ups" with a single "✅ Delegations" button
- **Stats panel** — "Top-up Events" card replaced with "Withdrawals" count; "Total Delegated" now correctly sums per-transaction amounts

### Bug fixes — round 1 (new subgraph)

- **No HTTP timeout** — all `requests.post()` calls lacked a timeout and could hang indefinitely; added `timeout=30` to `run_query`, `fetch_ens_name`, and `fetch_indexer_avatar`
- **No avatar cache** — `fetch_indexer_avatar()` made a fresh API call for every table row; with event-level data the same indexer appears hundreds of times, causing duplicate calls and rate-limit risk; added `_avatar_cache` dict
- **`JSONDecodeError` uncaught in `run_query`** — a gateway HTML error page caused an unhandled crash with no useful message; now caught and re-raised as `RuntimeError` with the response preview
- **GRT filter silently dropped all withdrawal events** — Horizon withdrawals may carry `tokens = 0`; the old `tokens < GRT_SIZE * 10**18` filter hid them from the table; withdrawals are now exempt from the threshold filter
- **Stats totals didn't match table** — stats summed all events including sub-threshold ones not shown in the table; both now apply the same `grt_threshold`
- **Redundant `sorted()` in `fetch_events()`** — `_paginate()` already returns records in DESC timestamp order; the final re-sort was wasted O(n log n) work; removed
- **`id_lt` cursor unreliable for `txHash-logIndex` IDs** — lexicographic string comparison places `"tx-10"` before `"tx-9"`, potentially causing duplicates at page boundaries in high-activity blocks; added a `seen_ids` set to deduplicate any records that slip through
- **Subgraph errors not logged** — `run_query` raised `RuntimeError` without a prior `log_message`, so failures were invisible in log files; now logs before raising
- **`TRANSACTION_COUNT` default was 5 000, not 1 000** — silently fetched 5× more data than documented when the `.env` key was absent; corrected to 1 000
- **`fetch_ens_name` / avatar crashed on `None` address** — `data.get(key)` returns `None` if a key is absent from the subgraph response; `address.lower()` then raised `AttributeError`; added early-return guard for falsy addresses

### Other

- Breadcrumb no longer shows `TRANSACTION_COUNT × 2` (previous logic fetched delegations and undelegations separately)
- Removed top-up heuristic (`createdAt < lastDelegatedAt`) — no longer needed with event-level data
- Removed "Top-up Events" stat card; removed "➕ Top-ups" filter button
- `subgraph/` folder added: source code for the custom `graph-delegation-events` subgraph (AssemblyScript mappings, schema, manifest, ABI)
- `README.md` updated with v2.0.0 changelog, subgraph cross-references, updated `.env` example, and corrected subgraphs table

---

## [1.4.3] — 2026-03-07

- Replaced invisible `➕` emoji on top-up rows with a styled amber `[+]` badge (visible on both dark and light mode)
- Same badge applied to the Top-ups filter button
- Updated JS filter to match `"Top-up"` instead of `"➕ Top-up"`

## [1.4.2] — 2026-03-07

- Added hover tooltips on event-type labels in the table (New Delegation / Top-up / Undelegation definitions)
- Added tooltips on filter buttons with the same explanations
- Added `cursor: help` on event-type cells to signal that hovering shows info

## [1.4.1] — 2026-03-07

- Fixed ENS lookups broken by `[api-key]` placeholder left in `.env`
- `ENS_API_KEY` now holds just the key (not the full URL), falling back to `GRAPH_API_KEY` when not set
- `ENS_SUBGRAPH_URL` constructed consistently with other subgraph URLs

## [1.4.0] — 2026-03-07

- Detected top-ups vs. first-time delegations using `createdAt` vs. `lastDelegatedAt`
- Top-up rows carry a tooltip noting that the amount shown is the total, not the delta
- Stats panel split: "New Delegations" (GRT), "Top-up Events" (count), "Net (new only)"
- Added "➕ Top-ups" filter button

## [1.3.0] — 2026-03-07

- Regenerated `social-card.jpeg` at 1 200 × 630 px with CTA
- Optimised `og:title`, `twitter:title`, `og:description`, `twitter:description` lengths
- "Generated on" line: removed version suffix, cadence changed to "every 24 hours"

## [1.2.1] — 2026-03-07

- Added `social-card.jpeg` for rich social sharing previews (X, LinkedIn)
- Fixed footer version string not rendering (was inside a non-f-string)
- Fixed `run_delegators_vps.sh`: social card only copied on first deploy; consistent `chown paolo:www-data`

## [1.2.0] — 2026-03-07

- Removed Tx column (hashes unavailable in previous data source)
- Refactored footer with dynamic version, author credit, GitHub link
- Fixed `tokens` field: `float` → `int` (float loses precision on large wei values)
- Fixed favicon MIME type, filter `href="#"` scroll bug, `payload["data"] is None` guard
- ENS cache: in-memory dict (loaded once, saved on update); corrupt-file protection
- Fixed `_paginate` cursor: `_lt` → composite `_lte + id_lt` to avoid skipping boundary records

## [1.1.0] — 2026-03-07

- Added paginated table: 50 rows/page with full pagination controls
- Pagination integrated with event-type filter, GRT filter, and search
- Fixed data freshness: records now fetched `DESC` by timestamp (most recent first)
- Updated footer with author credit and GitHub link

## [1.0.9] — 2026-03-07

- Fixed 9 bugs: `NameError` on log, typo in `TRANSACTION_COUNT`, malformed `<tr>`, `ENS_SUBGRAPH_URL` None guard, CSV `IndexError`, JS filter false-positive, dead-code removal, ENS cache timestamp fix, empty-event guard

## [1.0.8] — 2026-03-07

- Migrated to Arbitrum subgraphs (Graph Analytics + Graph Network)
- Added cursor-based pagination, `RuntimeError` on subgraph errors, `EnvironmentError` for missing API key
- Added `run_delegators_vps.sh` for nginx deployment
