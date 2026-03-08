import html as html_module
import os
import json
import csv
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List

# v2.1.0 / 08-Mar-2026
# Author: Paolo Diomede
DASHBOARD_VERSION = "2.1.0"


# Function that writes in the log file
def log_message(message):
    timestamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    print(timestamped)
    with open(log_file, "a", encoding='utf-8') as log:
        log.write(timestamped + "\n")
# End Function 'log_message'


# Create REPORTS directory if it doesn't exist
report_dir = "reports"
os.makedirs(report_dir, exist_ok=True)

# Create LOGS directory if it doesn't exist (must be before any log_message calls)
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"metrics_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.txt")

# Load environment variables from the .env file
load_dotenv()
API_KEY = os.getenv("GRAPH_API_KEY")
if not API_KEY:
    raise EnvironmentError("GRAPH_API_KEY is not set. Add it to your .env file.")
ENS_API_KEY = os.getenv("ENS_API_KEY", API_KEY)  # falls back to GRAPH_API_KEY if not set
try:
    GRT_SIZE = int(os.getenv("GRT_SIZE", 10000))
except ValueError:
    raise EnvironmentError("GRT_SIZE in .env must be a plain integer (e.g. 10000).")
if GRT_SIZE < 0:
    raise EnvironmentError(f"GRT_SIZE must be 0 or greater (got {GRT_SIZE}).")
try:
    UPDATE_CADENCE_HOURS = int(os.getenv("UPDATE_CADENCE_HOURS", 8))
except ValueError:
    UPDATE_CADENCE_HOURS = 8

# Load ENS cache file path
ENS_CACHE_FILE = os.getenv("ENS_CACHE_FILE", "ens_cache.json")
if not os.getenv("ENS_CACHE_FILE"):
    log_message("⚠️ ENS_CACHE_FILE not set in .env — using default: 'ens_cache.json'")

# Load ENS cache expiry duration
try:
    ENS_CACHE_EXPIRY_HOURS = int(os.getenv("ENS_CACHE_EXPIRY_HOURS", 24))
    if not os.getenv("ENS_CACHE_EXPIRY_HOURS"):
        log_message("⚠️ ENS_CACHE_EXPIRY_HOURS not set in .env — using default: 24h")
except ValueError:
    ENS_CACHE_EXPIRY_HOURS = 24
    log_message("⚠️ ENS_CACHE_EXPIRY_HOURS is not a valid integer — using default: 24h")

# List of all used subgraphs
DELEGATION_EVENTS_SUBGRAPH_ID = os.getenv("GRAPH_DELEGATION_EVENTS")
if not DELEGATION_EVENTS_SUBGRAPH_ID or DELEGATION_EVENTS_SUBGRAPH_ID == "<subgraph_id>":
    raise EnvironmentError("GRAPH_DELEGATION_EVENTS is not set. Add the subgraph ID to your .env file.")
DELEGATION_EVENTS_URL = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/{DELEGATION_EVENTS_SUBGRAPH_ID}"  # graph-delegation-events (Arbitrum)
ENS_SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{ENS_API_KEY}/subgraphs/id/5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH"  # ENS Mainnet
AVATAR_SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp"   # Graph Network Arbitrum


# GraphQL query to retrieve ENS
queryENS = """
    query GetEnsName($address: String!) {
      domains(where: { resolvedAddress: $address, name_ends_with: ".eth" }, first: 1) {
        name
      }
    }
"""


_ens_cache: dict = {}  # in-memory cache — loaded once, saved after each new lookup

def _load_ens_cache() -> dict:
    """Load ENS cache from disk once into the module-level dict."""
    global _ens_cache
    if _ens_cache:
        return _ens_cache
    if os.path.exists(ENS_CACHE_FILE):
        try:
            with open(ENS_CACHE_FILE, "r", encoding='utf-8') as f:
                _ens_cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            log_message("⚠️ ENS cache file is corrupt or unreadable — starting with empty cache.")
            _ens_cache = {}
    return _ens_cache

def _save_ens_cache() -> None:
    try:
        with open(ENS_CACHE_FILE, "w", encoding='utf-8') as f:
            json.dump(_ens_cache, f, indent=2)
    except IOError as e:
        log_message(f"⚠️ Failed to save ENS cache: {e}")

def fetch_ens_name(address: str) -> str:
    if not address:
        return ""
    headers = {"Content-Type": "application/json"}
    address = address.lower()

    ens_cache = _load_ens_cache()

    # Check cache and freshness
    record = ens_cache.get(address)
    if record:
        ts_raw = record.get("timestamp")
        if ts_raw:
            ts_str = ts_raw.replace("Z", "+00:00") if isinstance(ts_raw, str) else ts_raw
            try:
                last_updated = datetime.fromisoformat(ts_str).astimezone(timezone.utc)
                if datetime.now(timezone.utc) - last_updated < timedelta(hours=ENS_CACHE_EXPIRY_HOURS):
                    return record.get("ens", "")
            except (ValueError, TypeError):
                pass  # invalid timestamp — treat as stale, re-fetch

    payload = {
        "query": queryENS,
        "variables": { "address": address }
    }

    try:
        response = requests.post(ENS_SUBGRAPH_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        try:
            result = response.json()
        except json.JSONDecodeError:
            log_message(f"⚠️ ENS subgraph returned non-JSON (status {response.status_code}) for {address}")
            if record and record.get("ens"):
                log_message(f"↩️ Using stale cached ENS for {address}: {record['ens']}")
                return record["ens"]
            return ""
        domains = result.get("data", {}).get("domains", [])

        ens_name = domains[0]["name"] if domains and "name" in domains[0] else ""
        ens_cache[address] = {
            "ens": ens_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        _save_ens_cache()

        log_message(f"🔍 Fetched ENS for {address}: {ens_name or 'no ENS'}")
        return ens_name

    except requests.RequestException as e:
        log_message(f"⚠️ ENS lookup failed for {address}: {e}")
        # Return the stale cached value rather than an empty string if available
        if record and record.get("ens"):
            log_message(f"↩️ Using stale cached ENS for {address}: {record['ens']}")
            return record["ens"]
        return ""


@dataclass
class DelegationEvent:
    indexer: str
    tokens: int
    delegator: str
    block_timestamp: int
    event_type: str   # 'delegation', 'undelegation', or 'withdrawal'
    tx_hash: str = ""

    def to_dict(self):
        return {
            "indexer": self.indexer,
            "tokens": self.tokens,
            "delegator": self.delegator,
            "block_timestamp": self.block_timestamp,
            "block_datetime": datetime.fromtimestamp(self.block_timestamp, tz=timezone.utc),
            "event_type": self.event_type,
            "tx_hash": self.tx_hash,
        }


class DelegationFetcher:
    def __init__(self, SUBGRAPH_URL: str):
        self.subgraph_url = SUBGRAPH_URL

    def run_query(self, query: str) -> dict:
        try:
            response = requests.post(self.subgraph_url, json={"query": query}, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            log_message(f"⚠️ HTTP request to subgraph failed: {e}")
            raise
        try:
            payload = response.json()
        except json.JSONDecodeError as e:
            log_message(f"⚠️ Subgraph returned non-JSON response (status {response.status_code}): {response.text[:200]}")
            raise RuntimeError(f"Subgraph returned non-JSON response: {e}") from e
        if "data" not in payload or payload["data"] is None:
            errors = payload.get("errors", payload)
            log_message(f"⚠️ Subgraph query error: {errors}")
            raise RuntimeError(f"Subgraph query failed: {errors}")
        return payload["data"]

    def _paginate(self, entity: str, order_field: str, extra_where: str, fields: str, limit: int) -> list:
        """Fetch up to `limit` records ordered by `order_field` DESC (most recent first).
        Uses a composite cursor (timestamp_lte + id_lt) to avoid skipping records that
        share the same timestamp at a page boundary.

        Note: the new subgraph uses string IDs of the form `txHash-logIndex`. Lexicographic
        id_lt comparison can be ambiguous for log indices ≥ 10 (e.g. "-10" sorts before "-9").
        A seen-ID set is maintained to deduplicate any records that slip through the cursor."""
        PAGE_SIZE = 1000
        results = []
        seen_ids: set = set()
        last_ts = None
        last_id = None

        while len(results) < limit:
            batch = min(PAGE_SIZE, limit - len(results))
            where_parts = [extra_where] if extra_where else []
            if last_ts is not None:
                where_parts.append(f"{order_field}_lte: {last_ts}")
                where_parts.append(f'id_lt: "{last_id}"')
            where_clause = ", ".join(where_parts)
            where_block = f"where: {{ {where_clause} }}" if where_clause else ""

            query = f'''
            {{
              items: {entity}(
                orderBy: {order_field},
                orderDirection: desc,
                first: {batch},
                {where_block}
              ) {{
                id
                {fields}
              }}
            }}
            '''
            try:
                data = self.run_query(query)
            except (RuntimeError, requests.RequestException) as e:
                log_message(f"⚠️ Pagination interrupted after {len(results)} records: {e}. Using partial results.")
                break
            page = data.get("items") or []
            if not page:
                break
            for record in page:
                if record["id"] not in seen_ids:
                    seen_ids.add(record["id"])
                    results.append(record)
            log_message(f"📄 Page fetched: {len(page)} records (unique total so far: {len(results)})")
            last_ts = page[-1][order_field]
            last_id = page[-1]["id"]
            if len(page) < batch:
                break

        return results

    def fetch_events(self) -> List[DelegationEvent]:

        FETCH_DAYS = 90
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=FETCH_DAYS)).timestamp())
        extra_where = f'eventType_in: ["delegation", "undelegation"], timestamp_gte: {cutoff}'
        limit = 100_000

        log_message(f"⏳ Fetching all delegation events from last {FETCH_DAYS} days (GRT ≥ {GRT_SIZE:,})...")

        fields = "eventType indexer delegator tokens txHash timestamp"

        raw_events = self._paginate(
            entity="delegationEvents",
            order_field="timestamp",
            extra_where=extra_where,
            fields=fields,
            limit=limit,
        )

        if not raw_events:
            log_message("⚠️ Subgraph returned 0 events — the subgraph may be empty, still syncing, or the query failed silently.")

        events = []
        for e in raw_events:
            raw_tokens = e.get("tokens")
            raw_ts     = e.get("timestamp")
            if raw_tokens is None:
                log_message(f"⚠️ Skipping event with null tokens (id={e.get('id', '?')})")
                continue
            if raw_ts is None:
                log_message(f"⚠️ Skipping event with null timestamp (id={e.get('id', '?')})")
                continue
            events.append(DelegationEvent(
                indexer=e.get("indexer", ""),
                tokens=int(raw_tokens),
                delegator=e.get("delegator", ""),
                block_timestamp=int(raw_ts),
                event_type=e.get("eventType", ""),
                tx_hash=e.get("txHash", ""),
            ))

        log_message(f"✅ Loaded {len(events):,} delegation events.")
        # _paginate already returns records DESC by timestamp — no re-sort needed
        return events


# FUNCTION SECTION

_avatar_cache: dict = {}  # in-memory cache keyed by lowercase address

def fetch_indexer_avatar(address):
    if not address:
        return ""
    addr = address.lower()
    if addr in _avatar_cache:
        return _avatar_cache[addr]

    # Use variable to avoid GraphQL injection if address ever contained quotes
    if '"' in addr or '\\' in addr or '\n' in addr:
        return ""
    queryAvatar = f'''
    {{
        indexers(where: {{ id: "{addr}" }}) {{
            account {{
                metadata {{
                    image
                }}
            }}
        }}
    }}
    '''

    try:
        response = requests.post(AVATAR_SUBGRAPH_URL, json={"query": queryAvatar}, timeout=30)
        response.raise_for_status()
        try:
            result = response.json()
        except json.JSONDecodeError:
            log_message(f"⚠️ Avatar subgraph returned non-JSON (status {response.status_code}) for {addr}")
            # Do NOT cache — transient gateway error; will retry on next run
            return ""

        if not result or "data" not in result or result["data"] is None:
            log_message(f"⚠️ Unexpected avatar response structure:\n{json.dumps(result, indent=2)}")
            _avatar_cache[addr] = ""
            return ""

        indexers = result["data"].get("indexers", [])
        if not indexers:
            _avatar_cache[addr] = ""
            return ""

        account = indexers[0].get("account", {})
        metadata = account.get("metadata")

        if metadata is None:
            log_message(f"ℹ️ No metadata found for address {address}")
            _avatar_cache[addr] = ""
            return ""

        image = metadata.get("image", "") or ""
        _avatar_cache[addr] = image
        return image

    except requests.RequestException as e:
        log_message(f"⚠️ Failed to fetch indexer avatar for address {address}: {e}")
        # Do NOT cache — transient failure; the next run should retry
        return ""
    
    
# Returns all the data about last delegations and undelegations
def fetch_metrics():
    fetcher = DelegationFetcher(DELEGATION_EVENTS_URL)
    events = fetcher.fetch_events()
    return events
# End Function 'fetch_metrics'


# Explicit column order for CSV (dict.keys() order can vary across Python versions)
CSV_FIELDNAMES = ["event_type", "tokens", "block_datetime", "block_timestamp", "indexer", "delegator", "tx_hash"]


# Returns all the data in a CSV file
def generate_delegators_to_csv(events: List[DelegationEvent]):
    filename = "delegators.csv"
    csv_path = os.path.join(report_dir, filename)

    if not events:
        log_message("⚠️ No events to write to CSV.")
        return

    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for event in events:
            row = event.to_dict()
            # datetime objects aren't CSV-serialisable; convert to ISO 8601 string
            if isinstance(row.get("block_datetime"), datetime):
                row["block_datetime"] = row["block_datetime"].isoformat()
            writer.writerow(row)

    log_message(f"✅ Saved CSV file: {csv_path}")
# End Function 'generate_delegators_to_csv'




def generate_delegators_to_html(events: List[DelegationEvent]):

    if not events:
        log_message("⚠️ No events to render in HTML dashboard.")
        return

    # Capture the timestamp right before writing so it reflects actual generation time
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cadence_display = "on every run" if UPDATE_CADENCE_HOURS == 0 else f"every {UPDATE_CADENCE_HOURS} hours"

    filename = "index.html"
    html_path = os.path.join(report_dir, filename)

    with open(html_path, mode='w', encoding='utf-8') as f:
        f.write("""
            <!DOCTYPE html>
            <html lang="en">
            <head>

                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="description" content="Track real-time delegation and undelegation activity on The Graph Network with Graph Tools Pro's Delegators Activity Log, featuring detailed transaction data.">
                <meta name="robots" content="index, follow">

                <meta property="og:title" content="Graph Tools Pro: Delegators Activity Log &amp; Analytics">
                <meta property="og:description" content="Track live delegation and undelegation activity on The Graph Network (Arbitrum). ENS names, indexer avatars, filters, CSV export and more.">
                <meta property="og:url" content="https://graphtools.pro/delegators/">
                <meta property="og:type" content="website">
                <meta property="og:image" content="https://graphtools.pro/delegators/social-card.jpeg">
                
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="Graph Tools Pro: Delegators Activity Log &amp; Analytics">
                <meta name="twitter:description" content="Track live delegation and undelegation activity on The Graph Network (Arbitrum). ENS names, indexer avatars, filters, CSV export and more.">
                <meta name="twitter:image" content="https://graphtools.pro/delegators/social-card.jpeg">
                
                <title>Graph Tools Pro: Delegators Activity Log &amp; Analytics</title>
                <link rel="canonical" href="https://graphtools.pro/delegators/">
                <link rel="icon" type="image/x-icon" href="https://graphtools.pro/favicon.ico">
              
                <style>
                    .filter-button.active-filter {
                        background-color: #ffeb3b;
                        padding: 2px 6px;
                        border-radius: 4px;
                        color: black;
                        font-weight: bold;
                    }
                    :root {
                        --bg-color: #111;
                        --text-color: #fff;
                        --table-bg: #1e1e1e;
                        --header-bg: #333;
                        --link-color: #fff;
                    }
                    .light-mode {
                        --bg-color: #f0f2f5;
                        --text-color: #000;
                        --table-bg: #ffffff;
                        --header-bg: #ddd;
                        --link-color: #0000EE;
                    }
                    .light-mode .home-link {
                        color: var(--text-color);
                    }
                    body {
                        background-color: var(--bg-color);
                        color: var(--text-color);
                        font-family: Arial, sans-serif;
                        padding: 10px 20px 20px 20px;
                        margin-top: 0;
                        transition: all 0.3s ease;
                    }
                    .header-container {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 15px;
                        line-height: 1;
                    }
                    .breadcrumb {
                        font-size: 0.9em;
                        margin: 0;
                        padding: 0;
                        display: flex;
                        align-items: center;
                    }
                    .toggle-container {
                        display: flex;
                        align-items: center;
                        margin: 0;
                        padding: 0;
                    }
                    .toggle-switch {
                        position: relative;
                        width: 50px;
                        height: 24px;
                        margin-right: 10px;
                    }
                    .toggle-switch input {
                        opacity: 0;
                        width: 0;
                        height: 0;
                    }
                    .toggle-switch .slider {
                        position: absolute;
                        top: 0; left: 0;
                        right: 0; bottom: 0;
                        background: #ccc;
                        transition: 0.4s;
                        border-radius: 34px;
                    }
                    .toggle-switch .slider:before {
                        position: absolute;
                        content: "";
                        height: 18px;
                        width: 18px;
                        left: 4px;
                        bottom: 3px;
                        background: white;
                        transition: 0.4s;
                        border-radius: 50%;
                    }
                    .toggle-switch input:checked + .slider {
                        background: #2196F3;
                    }
                    .toggle-switch input:checked + .slider:before {
                        transform: translateX(24px);
                    }
                    #toggle-icon {
                        font-size: 1.5rem;
                        line-height: 1;
                    }
                    .divider {
                        border: 0;
                        height: 2px;
                        background: linear-gradient(to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0));
                        margin: 15px 0;
                    }
                    .light-mode .divider {
                        background: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0));
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        background: var(--table-bg);
                    }
                    th, td {
                        padding: 8px 12px;
                        border: 1px solid #444;
                        text-align: left;
                    }
                    th {
                        background-color: var(--header-bg);
                        color: var(--text-color);
                    }
                    .filter-bar {
                        display: flex;
                        align-items: center;
                        gap: 8px;
                        font-size: 0.8em;
                    }
                    .filter-bar a {
                        text-decoration: none;
                    }
                    .download-button {
                        padding: 5px 10px;
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        cursor: pointer;
                    }
                    .download-button:hover {
                        background-color: #45a049;
                    }
                    .filter-container {
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }
                    .controls-container {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 12px;
                        margin-bottom: 20px;
                    }
                    .search-and-button {
                        display: flex;
                        align-items: flex-end;
                        gap: 12px;
                    }
                    .tooltip-header {
                        position: relative;
                        cursor: help;
                    }
                    .tooltip-header .tooltip-text {
                        visibility: hidden;
                        background-color: #333;
                        color: #fff;
                        text-align: left;
                        padding: 6px 10px;
                        border-radius: 4px;
                        position: absolute;
                        z-index: 1;
                        bottom: 125%;
                        left: 50%;
                        transform: translateX(-50%);
                        opacity: 0;
                        transition: opacity 0.3s;
                        width: max-content;
                        max-width: 220px;
                        font-size: 13px;
                        pointer-events: none;
                    }
                    .tooltip-header:hover .tooltip-text {
                        visibility: visible;
                        opacity: 1;
                    }
                    a {
                        color: var(--link-color);
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    .footer {
                        text-align: center;
                        margin: 10px 0 40px;
                        font-size: 0.9rem;
                        opacity: 0.9;
                    }
                    .footer a {
                        color: #80bfff;
                        text-decoration: none;
                        transition: color 0.3s ease;
                    }
                    .footer a:hover {
                        color: #4d94ff;
                    }
                    .light-mode .footer a {
                        color: #0066cc;
                    }
                    .light-mode .footer a:hover {
                        color: #0033ff;
                    }
                    .footer-divider {
                        border: none;
                        border-bottom: 1px solid rgba(200, 200, 200, 0.2);
                        margin: 40px 0 10px;
                        opacity: 0.8;
                    }
                    .current-page-title {
                        color: #00bcd4;
                        font-weight: bold;
                    }
                    .light-mode .current-page-title {
                        color: #1a73e8;
                    }
                    .pagination-bar {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        flex-wrap: wrap;
                        gap: 10px;
                        margin: 16px 0 8px;
                        font-size: 0.85em;
                    }
                    .page-info {
                        color: var(--text-color);
                        opacity: 0.75;
                    }
                    .page-buttons {
                        display: flex;
                        align-items: center;
                        gap: 4px;
                    }
                    .page-buttons button {
                        background: var(--table-bg);
                        color: var(--text-color);
                        border: 1px solid #555;
                        border-radius: 4px;
                        padding: 4px 10px;
                        cursor: pointer;
                        font-size: 0.9em;
                        transition: background 0.2s;
                    }
                    .page-buttons button:hover:not(:disabled) {
                        background: #00bcd4;
                        color: #000;
                        border-color: #00bcd4;
                    }
                    .page-buttons button.active-page {
                        background: #00bcd4;
                        color: #000;
                        border-color: #00bcd4;
                        font-weight: bold;
                    }
                    .page-buttons button:disabled {
                        opacity: 0.3;
                        cursor: default;
                    }
                    .page-buttons .ellipsis {
                        padding: 0 4px;
                        opacity: 0.5;
                    }
                    .light-mode .page-buttons button {
                        border-color: #aaa;
                    }
                </style>

                <script defer data-domain="graphtools.pro/delegators" src="https://plausible.io/js/script.file-downloads.hash.outbound-links.pageview-props.tagged-events.js"></script>
                <script>window.plausible = window.plausible || function() { (window.plausible.q = window.plausible.q || []).push(arguments) }</script>


            </head>
            <body>
        """)
        
               
        # Header with breadcrumb and toggle
        breadcrumb_sub = f"last 90 days fetched, GRT ≥ {GRT_SIZE:,}"
        f.write(f"""
            <div class="header-container">
                <div class="breadcrumb" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 500; font-size: 0.85em; letter-spacing: 0.3px; text-shadow: 0 1px 2px rgba(0,0,0,0.15);">
                    <a href="https://graphtools.pro" class="home-link" style="text-decoration: none;">🏠 Home</a>&nbsp;&nbsp;&raquo;&nbsp;&nbsp;
                    <span class="current-page-title">📊 Delegators Activity Log <span style="font-size: 0.85em; color: var(--text-color);">&nbsp;&nbsp;[{breadcrumb_sub}]</span></span>    
                </div>
                <div class="toggle-container">
                    <label class="toggle-switch">
                        <input type="checkbox" onclick="toggleTheme()">
                        <span class="slider"></span>
                    </label>
                    <span id="toggle-icon">🌙</span>
                </div>
            </div>
            
            <hr class="divider">
                <div style="text-align: center;">    
                <h1 style="margin-bottom: 4px;">Delegators Activity Log</h1>
                <div style="text-align: center; font-size: 0.8em; color: var(--text-color); margin-top: 0; margin-bottom: 30px;">
                    Generated on: {timestamp} - (updated {cadence_display})
                </div>
            </div>
        """)

        
        grt_threshold = GRT_SIZE * 10**18
        total_delegated   = sum(e.tokens for e in events if e.event_type == "delegation"   and e.tokens >= grt_threshold) // 10**18
        total_undelegated = sum(e.tokens for e in events if e.event_type == "undelegation" and e.tokens >= grt_threshold) // 10**18
        net = total_delegated - total_undelegated

        net_color = "limegreen" if net >= 0 else "crimson"

        f.write(f"""
            <div id="summary-cards" style="display: flex; gap: 20px; margin-bottom: 30px;">
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Total Delegated</div>
                    <div id="total-delegated" style="font-size: 2em; font-weight: bold; color: limegreen;">{total_delegated:,} GRT</div>
                </div>
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Total Undelegated</div>
                    <div id="total-undelegated" style="font-size: 2em; font-weight: bold; color: crimson;">{total_undelegated:,} GRT</div>
                </div>
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Net</div>
                    <div id="net-amount" style="font-size: 2em; font-weight: bold; color: {net_color};">{net:,} GRT</div>
                </div>
            </div>
        """)

        f.write("""
            <div class="controls-container">
                <div class="search-and-button">
                    <input type="text" id="searchBox" placeholder="Search Indexers ..." style="padding: 5px; width: 300px;" />
                    <button class="download-button" onclick="downloadCSV()">Download CSV</button>
                </div>
                <div class="filter-container">
                    <div class="filter-bar" data-filter-type="days">
                        <strong style="margin-left: 16px;">Time range:</strong>
                        <a class="filter-button" href="javascript:void(0)" data-filter="30" onclick="filterByDays('30')">LAST 30 DAYS</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="90" onclick="filterByDays('90')">LAST 90 DAYS</a>
                    </div>
                    <div class="filter-bar" data-filter-type="event">
                        <strong style="margin-left: 16px;">Filter for:</strong>
                        <a class="filter-button" href="javascript:void(0)" data-filter="Delegations" onclick="filterByFlag('Delegations')" title="GRT delegated to an indexer. Amount shown is the exact delta per transaction.">✅ Delegations</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="Undelegations" onclick="filterByFlag('Undelegations')" title="Tokens locked for undelegation from an indexer. Subject to a ~28-day unbonding period before withdrawal.">❌ Undelegations</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="All" onclick="filterByFlag('All')">🧹 Clear Filter</a>
                    </div>
                    <div class="filter-bar" data-filter-type="grt">
                        <strong style="margin-left: 16px;">Filter for:</strong>
                        <a class="filter-button" href="javascript:void(0)" data-filter="50000" onclick="filterByGRT('50000')">💰 > 50,000 GRT</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="100000" onclick="filterByGRT('100000')">💰💰 > 100,000 GRT</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="1000000" onclick="filterByGRT('1000000')">💰💰💰 > 1M GRT</a>
                        | <a class="filter-button" href="javascript:void(0)" data-filter="All" onclick="filterByGRT('All')">🧹 Clear Filter</a>
                    </div>
                </div>
            </div>
        """)

        f.write("""
            <table>
        """)
        
        headers = ["Event", "GRT", "Date", "Indexer", "Delegator", "Tx"]
        f.write("<thead><tr>")
        for header in headers:
            f.write(f"<th>{header}</th>")
        f.write("</tr></thead>\n<tbody>\n")

        key_order = ["event_type", "tokens", "block_datetime", "indexer", "delegator", "tx_hash"]
        for event in events:
            if event.tokens < grt_threshold:
                continue
            f.write(f'<tr data-ts="{event.block_timestamp}">')
            data = event.to_dict()
            for key in key_order:
                value = data.get(key)

                if key == "block_datetime" and isinstance(value, datetime):
                    value = f'<span style="font-size: 0.85em;">{value.strftime("%Y-%m-%d %H:%M")}</span>'
                
                if key == "tokens":
                    value = f"{int(value) // 10**18:,}"

                if key == "event_type":
                    if value == "delegation":
                        label = '✅ Delegation'
                        tooltip = ' title="GRT delegated to an indexer. Amount shown is the exact delta for this transaction."'
                    elif value == "undelegation":
                        label = '❌ Undelegation'
                        tooltip = ' title="Tokens locked for undelegation from an indexer. Subject to a ~28-day unbonding period before withdrawal."'
                    elif value == "withdrawal":
                        label = '🔓 Withdrawal'
                        tooltip = ' title="Tokens withdrawn after the unbonding period has elapsed."'
                    else:
                        safe_val = html_module.escape(str(value or "unknown"), quote=True)
                        label = f'❓ {safe_val}'
                        tooltip = f' title="Unrecognised event type: {safe_val}. The subgraph schema may have changed."'
                    value = f'<span style="font-size: 0.85em; cursor: help;"{tooltip}>{label}</span>'

                if key in ("indexer", "delegator"):
                    if not value:
                        f.write("<td><span style='opacity:0.4;font-size:0.8em;'>—</span></td>")
                        continue
                    ens_name = fetch_ens_name(value)
                    display_name = ens_name if ens_name else value
                    safe_display = html_module.escape(display_name)
                    safe_value = html_module.escape(value, quote=True)

                    if key == "indexer":
                        avatar_url = fetch_indexer_avatar(value)
                        if avatar_url:
                            safe_avatar = html_module.escape(avatar_url, quote=True)
                            display_name = f'<img src="{safe_avatar}" alt="avatar" style="height:20px;vertical-align:middle;margin-right:5px;">{safe_display}'
                        else:
                            display_name = safe_display

                    link = f'<a href="https://thegraph.com/explorer/profile/{safe_value}" target="_blank">{display_name}</a>'
                    value = f'<span style="font-size: 0.85em;">{link}</span>'

                if key == "tx_hash":
                    if value:
                        safe_tx = html_module.escape(value, quote=True)
                        short = value if len(value) <= 20 else value[:8] + "…" + value[-6:]
                        safe_short = html_module.escape(short)
                        value = f'<a href="https://arbiscan.io/tx/{safe_tx}" target="_blank" style="font-size:0.8em;font-family:monospace;" title="{safe_tx}">{safe_short}</a>'
                    else:
                        value = '<span style="opacity:0.4;font-size:0.8em;">—</span>'

                f.write(f"<td>{value}</td>")

            f.write("</tr>\n")
        
        f.write("""</tbody></table>

                <div id="pagination" class="pagination-bar"></div>

                <hr class="footer-divider">
                <div class="footer" style="display:flex;align-items:center;justify-content:center;gap:0;flex-wrap:wrap;">
                    <span>©<script>document.write(new Date().getFullYear())</script>&nbsp;<a href="https://graphtools.pro">Graph Tools Pro</a></span>
                    <span style="opacity:0.4;">&nbsp;&nbsp;|&nbsp;&nbsp;</span>
                    <span>Delegators Dashboard v""" + DASHBOARD_VERSION + """</span>
                    <span style="opacity:0.4;">&nbsp;&nbsp;|&nbsp;&nbsp;</span>
                    <span>Author: <a href="https://x.com/pdiomede" target="_blank">Paolo Diomede</a></span>
                    <span style="opacity:0.4;">&nbsp;&nbsp;|&nbsp;&nbsp;</span>
                    <a href="https://github.com/pdiomede/delegators-dashboard" target="_blank" style="display:inline-flex;align-items:center;gap:4px;">
                        <svg height="14" width="14" viewBox="0 0 16 16" fill="currentColor" style="vertical-align:middle;" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
                        View on GitHub
                    </a>
                </div>
                
                <script>
                    const ROWS_PER_PAGE = 50;
                    let currentPage = 1;
                    let currentDaysFilter = "30";
                    let currentFlagFilter = "All";
                    let currentGRTFilter = "All";
                    let currentSearch = "";

                    function toggleTheme() {
                        document.body.classList.toggle('light-mode');
                        document.getElementById('toggle-icon').textContent =
                            document.body.classList.contains('light-mode') ? '☀️' : '🌙';
                    }

                    function downloadCSV() {
                        const rows = getFilteredRows();
                        const headers = ["Event", "GRT", "Date", "Indexer", "Delegator", "Tx"];
                        let csv = headers.join(",") + "\\n";
                        rows.forEach(row => {
                            const cells = Array.from(row.cells).slice(0, 6);
                            const vals = cells.map((c, i) => {
                                let t = (c && c.textContent) ? c.textContent.trim() : "";
                                if (i === 5 && c) {
                                    const a = c.querySelector('a[href*="arbiscan.io/tx/"]');
                                    if (a) t = (a.getAttribute("href") || "").split("/tx/").pop() || t;
                                }
                                return '"' + t.replace(/"/g, '""') + '"';
                            });
                            csv += vals.join(",") + "\\n";
                        });
                        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = 'delegators.csv';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                    }

                    function getAllRows() {
                        return Array.from(document.querySelectorAll("table tbody tr"));
                    }

                    function getFilteredRows() {
                        const days = parseInt(currentDaysFilter, 10);
                        if (isNaN(days) || (days !== 30 && days !== 90)) return getAllRows();
                        const cutoffTs = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);
                        return getAllRows().filter(row => {
                            const eventCell = row.cells[0];
                            const grtCell   = row.cells[1];
                            const idxCell   = row.cells[3];
                            if (!eventCell || !grtCell) return false;

                            const rowTs = parseInt(row.dataset.ts, 10);
                            const daysMatch = !isNaN(rowTs) && rowTs >= cutoffTs;

                            const isDelegation   = eventCell.textContent.includes("✅ Delegation");
                            const isUndelegation = eventCell.textContent.includes("❌ Undelegation");
                            const grtAmount      = parseInt(grtCell.textContent.replace(/,/g, ""), 10);
                            const idxText        = idxCell ? idxCell.textContent.toLowerCase() : "";

                            const flagMatch   = currentFlagFilter === "All" ||
                                                (currentFlagFilter === "Delegations"   && isDelegation) ||
                                                (currentFlagFilter === "Undelegations" && isUndelegation);
                            const grtMatch    = currentGRTFilter === "All" || (!isNaN(grtAmount) && grtAmount > parseInt(currentGRTFilter, 10));
                            const searchMatch = currentSearch === "" || idxText.includes(currentSearch);

                            return daysMatch && flagMatch && grtMatch && searchMatch;
                        });
                    }

                    let _initialLoad = true;

                    function renderPage(page) {
                        const filtered   = getFilteredRows();
                        const total      = filtered.length;
                        const totalPages = Math.max(1, Math.ceil(total / ROWS_PER_PAGE));
                        currentPage      = Math.min(Math.max(1, page), totalPages);
                        const start      = (currentPage - 1) * ROWS_PER_PAGE;
                        const end        = start + ROWS_PER_PAGE;

                        getAllRows().forEach(r => r.style.display = "none");
                        filtered.forEach((r, i) => { r.style.display = (i >= start && i < end) ? "" : "none"; });

                        updatePaginationControls(currentPage, totalPages, total);
                        if (!_initialLoad) window.scrollTo({ top: 0, behavior: 'smooth' });
                        _initialLoad = false;
                    }

                    function updatePaginationControls(page, totalPages, total) {
                        const container = document.getElementById("pagination");
                        if (!container) return;

                        const start = total === 0 ? 0 : (page - 1) * ROWS_PER_PAGE + 1;
                        const end   = Math.min(page * ROWS_PER_PAGE, total);

                        let html = `<span class="page-info">Showing ${start}–${end} of ${total} results</span>`;
                        html += `<div class="page-buttons">`;
                        html += `<button onclick="renderPage(1)" ${page===1?"disabled":""}>«</button>`;
                        html += `<button onclick="renderPage(${page-1})" ${page===1?"disabled":""}>‹</button>`;

                        const delta = 2;
                        const range = [];
                        for (let i = Math.max(1, page-delta); i <= Math.min(totalPages, page+delta); i++) range.push(i);

                        if (range[0] > 1) {
                            html += `<button onclick="renderPage(1)">1</button>`;
                            if (range[0] > 2) html += `<span class="ellipsis">…</span>`;
                        }
                        range.forEach(p => {
                            html += `<button onclick="renderPage(${p})" class="${p===page?'active-page':''}">${p}</button>`;
                        });
                        if (range[range.length-1] < totalPages) {
                            if (range[range.length-1] < totalPages-1) html += `<span class="ellipsis">…</span>`;
                            html += `<button onclick="renderPage(${totalPages})">${totalPages}</button>`;
                        }

                        html += `<button onclick="renderPage(${page+1})" ${page===totalPages?"disabled":""}>›</button>`;
                        html += `<button onclick="renderPage(${totalPages})" ${page===totalPages?"disabled":""}>»</button>`;
                        html += `</div>`;

                        container.innerHTML = html;
                    }

                    function updateSummaryFromFilteredRows() {
                        const rows = getFilteredRows();
                        let delegated = 0, undelegated = 0;
                        rows.forEach(row => {
                            const eventCell = row.cells[0];
                            const grtCell = row.cells[1];
                            if (!eventCell || !grtCell) return;
                            const grt = parseInt(grtCell.textContent.replace(/,/g, ""), 10) || 0;
                            if (eventCell.textContent.includes("✅ Delegation")) delegated += grt;
                            else if (eventCell.textContent.includes("❌ Undelegation")) undelegated += grt;
                        });
                        const net = delegated - undelegated;
                        const netEl = document.getElementById("net-amount");
                        if (document.getElementById("total-delegated")) document.getElementById("total-delegated").textContent = delegated.toLocaleString() + " GRT";
                        if (document.getElementById("total-undelegated")) document.getElementById("total-undelegated").textContent = undelegated.toLocaleString() + " GRT";
                        if (netEl) {
                            netEl.textContent = net.toLocaleString() + " GRT";
                            netEl.style.color = net >= 0 ? "limegreen" : "crimson";
                        }
                    }

                    function applyFiltersAndRender() {
                        renderPage(1);
                        updateSummaryFromFilteredRows();
                        document.querySelectorAll('.filter-bar[data-filter-type="days"] .filter-button').forEach(btn => {
                            btn.classList.toggle('active-filter', btn.dataset.filter === currentDaysFilter);
                        });
                        document.querySelectorAll('.filter-bar[data-filter-type="event"] .filter-button').forEach(btn => {
                            btn.classList.toggle('active-filter', btn.dataset.filter !== "All" && btn.dataset.filter === currentFlagFilter);
                        });
                        document.querySelectorAll('.filter-bar[data-filter-type="grt"] .filter-button').forEach(btn => {
                            btn.classList.toggle('active-filter', btn.dataset.filter !== "All" && btn.dataset.filter === currentGRTFilter);
                        });
                    }

                    function filterByDays(days) {
                        if (days === "30" || days === "90") { currentDaysFilter = days; applyFiltersAndRender(); }
                    }
                    function filterByFlag(flag) { currentFlagFilter = flag; applyFiltersAndRender(); }
                    function filterByGRT(flag)  { currentGRTFilter  = flag; applyFiltersAndRender(); }

                    document.getElementById("searchBox").addEventListener("input", function () {
                        currentSearch = this.value.toLowerCase();
                        applyFiltersAndRender();
                    });

                    // Initial render
                    applyFiltersAndRender();
                </script>
            </body>
            </html>
        """)


    log_message(f"✅ Saved HTML dashboard: {html_path}")


if __name__ == "__main__":
    delegators = fetch_metrics()
    generate_delegators_to_csv(delegators)
    generate_delegators_to_html(delegators)
