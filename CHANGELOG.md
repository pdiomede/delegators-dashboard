# Changelog

All notable changes to this project are documented here.  
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.1.1] — 2026-03-08 (latest)

### Changed

- **Summary cards fixed** — Total Delegated, Total Undelegated, and Net now show the full 90-day totals and no longer change when filters are applied. The table and CSV download still respect filters.
- **Path resolution** — `report_dir`, `log_dir`, and `ENS_CACHE_FILE` are now resolved relative to the script directory. The script works correctly when run from any working directory (e.g. cron, different folders). Absolute paths in `ENS_CACHE_FILE` are preserved.
- **Breadcrumb** — Simplified to `[excluding under X GRT]` only.

### Fixed

- **`fetch_indexer_avatar` when account is null** — `indexers[0].get("account", {})` returned `None` when the subgraph had `account: null`; now uses `or {}` to avoid `AttributeError`.
- **`int(raw_tokens)` / `int(raw_ts)` ValueError** — Subgraph may return floats or invalid strings; now caught with `try/except` and events are skipped with a warning instead of crashing.
- **`fetch_ens_name` return None** — When cache had `"ens": null`, `record.get("ens", "")` returned `None`; now uses `record.get("ens") or ""` to always return a string.
- **`toggleTheme` null check** — Added guard for missing `toggle-icon` element to prevent crash.
- **Filter robustness** — Rows use `data-event-type` and `data-grt` attributes for reliable filtering; filter functions validate input; search input is trimmed.

---

## [2.1.0] — 2026-03-08

### Added

- **Time-range filter** — New filter bar: LAST 30 DAYS (default) | LAST 90 DAYS. Backend always fetches last 90 days; client-side filter controls which events are shown.
- **Filtered CSV download** — Download CSV now exports only the currently filtered rows instead of the full dataset.

### Changed

- **Removed `TRANSACTION_COUNT` and `DAYS_BACK`** — Backend always fetches last 90 days (up to 100,000 events). Time range is controlled solely by the client-side filter.
- **`UPDATE_CADENCE_HOURS=0`** — Header now shows "updated on every run" instead of "0 hours".

### Fixed

- **ENS cache KeyError** — `record["timestamp"]` could raise when cache record lacked a timestamp; now uses `record.get("timestamp")` with fallback.
- **`fromisoformat` on `Z` suffix** — Older Python versions fail on ISO strings ending in `Z`; now normalizes to `+00:00` before parsing.
- **HTML injection** — Escaped `display_name`, `avatar_url`, `tx_hash`, and unknown event types before inserting into HTML.
- **CSV column order** — Replaced `dict.keys()` with explicit `CSV_FIELDNAMES` for consistent column order across Python versions.
- **`filterByDays` invalid input** — Invalid values (e.g. `"invalid"`) no longer produce NaN cutoff; only `"30"` and `"90"` are accepted.
- **`tx_hash` truncation** — Short strings no longer produce overlapping/weird output; truncation only when `len > 20`.
- **`queryAvatar` injection** — Rejects addresses containing `"`, `\`, or newlines before building GraphQL query.
- **Download CSV** — Now respects all active filters (time range, event type, GRT, search) and extracts full tx hash from link href.

---

## [2.0.2] — 2026-03-08

### Changed

- **Track only delegations and undelegations** — Withdrawals are no longer fetched or displayed; subgraph query now uses `eventType_in: ["delegation", "undelegation"]` so withdrawals never consume the `TRANSACTION_COUNT` quota. Stats panel reduced to 3 cards (Total Delegated, Total Undelegated, Net); Withdrawals card and filter button removed. Table loop and JS filter simplified accordingly.
- **Configurable update cadence in header** — The "Generated on" line now shows "updated every N hours" where N is read from `UPDATE_CADENCE_HOURS` in `.env` (default: 8). Add `UPDATE_CADENCE_HOURS=8` (or 24, etc.) to match your cron schedule.

---

## [2.0.1] — 2026-03-08

### Bug fixes — round 3 (reliability & observability)

- **`log_message` missing `encoding='utf-8'`** — the log file was opened without an explicit encoding; emoji characters in log lines (`⚠️ ✅ 🔍 ↩️`) could raise `UnicodeEncodeError` on non-UTF-8 systems (common on Windows)
- **ENS cache file encoding** — both `open(ENS_CACHE_FILE, "r")` and `open(ENS_CACHE_FILE, "w")` lacked `encoding='utf-8'`; internationalized ENS names could corrupt the cache on non-UTF-8 platforms
- **Avatar cache poisoned by transient network errors** — `fetch_indexer_avatar()` stored `""` in `_avatar_cache` on `requests.RequestException`; a one-off network hiccup at startup permanently suppressed every avatar for the entire run; the `except` branch no longer writes to the cache
- **`fetch_indexer_avatar` crashed on non-JSON avatar response** — only `requests.RequestException` was caught; a gateway HTML error page would raise an unhandled `json.JSONDecodeError`; added inner `try/except json.JSONDecodeError` with a clear log message; non-JSON responses are not cached
- **`fetch_ens_name` crashed on non-JSON ENS response** — same gap: a non-JSON body from the ENS gateway raised an unhandled `JSONDecodeError`; added inner `try/except json.JSONDecodeError` with stale-cache fallback, matching the existing `RequestException` handler
- **`fetch_events()` was completely silent** — the main subgraph fetch can take 10–30 s and produced no log output; added `⏳ Fetching up to N events…` at start and `✅ Loaded N events.` on completion
- **`_paginate` progress log pre-dated deduplication** — the `📄 Page fetched` message reported `len(results) + len(page)` *before* the `seen_ids` deduplication loop, so duplicate records inflated the reported total; log now fires after deduplication with the true unique count
- **HTML `<table>` missing `<thead>` / `<tbody>`** — the header `<tr>` was written directly into `<table>` without a `<thead>` wrapper; CSS `position:sticky` on header rows cannot work without `<thead>`; screen readers misbehave; the JS `getAllRows()` relied on a fragile `.slice(1)` to skip the header; added `<thead>` / `<tbody>`, updated `getAllRows()` to `querySelectorAll("table tbody tr")`
- **`TRANSACTION_COUNT = 0` produced a silent empty dashboard** — `while len(results) < limit` exits immediately when `limit = 0`; the only feedback was a confusing "No events to write" message far downstream; added `if TRANSACTION_COUNT <= 0: raise EnvironmentError(…)` at startup
- **`fetch_events()` gave no warning when subgraph returned 0 events** — there was no way to distinguish "subgraph is genuinely empty" from "pagination failed silently"; added `⚠️ Subgraph returned 0 events — subgraph may be empty, still syncing, or the query failed silently.`

### Bug fixes — round 4 (data safety & correctness)

- **`GRT_SIZE` not validated `>= 0`** — a negative value (e.g. `GRT_SIZE=-1`) made `grt_threshold` negative, causing every event to pass the size filter and flood the table regardless of delegation amount; added `if GRT_SIZE < 0: raise EnvironmentError(…)` at startup
- **`data["items"]` hard key access in `_paginate`** — if the subgraph ever returns a response without an `"items"` key (unexpected schema change, partial error), the script crashed with `KeyError`; changed to `data.get("items") or []`, which falls through to the existing `if not page: break` guard
- **`int(e["tokens"])` crashed on `null` subgraph field** — if the subgraph returned `null` for `tokens`, `int(None)` raised `TypeError` and aborted the entire fetch; events with null tokens are now skipped individually with a `⚠️` log
- **`int(e["timestamp"])` crashed on `null` subgraph field** — same gap: a null `timestamp` field raised `TypeError` during `DelegationEvent` construction; null-timestamp events are now skipped individually with a `⚠️` log
- **Bare `else` silently misclassified unknown event types as withdrawals** — the HTML event-type renderer used `else` to catch `"withdrawal"`, so any new `eventType` value from a subgraph schema update would silently render as `🔓 Withdrawal`; replaced with explicit `elif value == "withdrawal"` and a new `else` branch that renders `❓ {value}` with a tooltip warning
- **JavaScript GRT filter hid 0-token withdrawal rows** — the client-side `grtMatch` applied the GRT threshold to every row; withdrawal events may legitimately have `tokens = 0` (Horizon protocol), causing them to disappear when a GRT amount filter was active; this was inconsistent with the Python server-side logic that always includes withdrawals; added `|| isWithdrawal` to the `grtMatch` expression
- **`fetch_indexer_avatar` had no `None`/empty address guard** — unlike `fetch_ens_name`, which had `if not address: return ""` at the top, `fetch_indexer_avatar` called `address.lower()` unconditionally; a null `indexer` field from the subgraph would cause `AttributeError: 'NoneType' object has no attribute 'lower'`; guard added
- **`_paginate` progress log reported inflated count before deduplication** — (companion fix to round-3 item above); the log was also emitting *before* the dedup loop during this round's refactor; log now appears after the loop with the accurate unique total
- **`timestamp` ("Generated on") computed at module load, not at HTML write time** — the module-level `timestamp = datetime.now(…)` was evaluated once when the script started; after a long run (hundreds of ENS/avatar lookups), the printed timestamp could be many minutes stale by the time the HTML was actually written; `timestamp` is now computed inside `generate_delegators_to_html()` immediately before writing
- **`<body class="dark-mode">` referenced a non-existent CSS class** — dark styling comes from `:root` CSS variable defaults, not a `.dark-mode` rule (which was never defined); the class was vestigial, semantically wrong, and would confuse future CSS changes; changed to `<body>` with no class; dark mode remains the default via `:root`, and `.light-mode` overrides it on toggle

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
