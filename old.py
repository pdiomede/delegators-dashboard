import os
import json
import csv
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List

# v1.0.8 / 20-May-2025
# Author: Paolo Diomede
DASHBOARD_VERSION = "1.0.8"


# Function that writes in the log file
def log_message(message):
    timestamped = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] {message}"
    print(timestamped)
    with open(log_file, "a") as log:
        log.write(timestamped + "\n")
# End Function 'log_message'


# Load environment variables from the .env file
load_dotenv()
API_KEY = os.getenv("GRAPH_API_KEY")
ENS_API_KEY = os.getenv("ENS_API_KEY")
TRANSACTION_COUNT = int(os.getenv("TRANSACTION_COUNT", 100)) # Default number of transaction to return
GRT_SIZE = int(os.getenv("GRT_SIZE", 10000)) # Excluding GRT under 10000


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
SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/9wzatP4KXm4WinEhB31MdKST949wCH8ZnkGe8o3DLTwp"
ENS_SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/5XqPmWe6gjyrJtFn9cLy237i4cWw2j9HcUJEXsP5qGtH"
AVATAR_SUBGRAPH_URL = f"https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/DZz4kDTdmzWLWsV373w2bSmoar3umKKH9y82SUKr5qmp"


# Create REPORTS directory if it doesn't exist
report_dir = "reports"
os.makedirs(report_dir, exist_ok=True)


# Create LOGS directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"metrics_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.txt")


# Get data to be used in the log and report files
timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# GraphQL query to retrieve ENS
queryENS = """
    query GetEnsName($address: String!) {
      domains(where: { resolvedAddress: $address, name_ends_with: ".eth" }, first: 1) {
        name
      }
    }
"""


def fetch_ens_name(address: str) -> str:
    global ENS_SUBGRAPH_URL
    headers = {"Content-Type": "application/json"}
    address = address.lower()

    # Load cache from file
    if os.path.exists(ENS_CACHE_FILE):
        with open(ENS_CACHE_FILE, "r") as f:
            ens_cache = json.load(f)
    else:
        ens_cache = {}

    # Check cache and freshness (24h)
    record = ens_cache.get(address)
    if record:
        last_updated = datetime.fromisoformat(record["timestamp"]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last_updated < timedelta(hours=ENS_CACHE_EXPIRY_HOURS):
            log_message(f"🧠 Using cached ENS for {address}: {record['ens'] or 'no ENS'}")
            return record["ens"]

    # Build GraphQL query
    payload = {
        "query": queryENS,
        "variables": { "address": address }
    }

    try:
        response = requests.post(ENS_SUBGRAPH_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        domains = result.get("data", {}).get("domains", [])

        # Get ENS if available, else store empty string
        ens_name = domains[0]["name"] if domains and "name" in domains[0] else ""
        ens_cache[address] = {
            "ens": ens_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save updated cache
        with open(ENS_CACHE_FILE, "w") as f:
            json.dump(ens_cache, f, indent=2)

        log_message(f"🔍 Fetched ENS for {address}: {ens_name or 'no ENS'}")
        return ens_name

    except requests.RequestException as e:
        log_message(f"⚠️ ENS lookup failed for {address}: {e}")
        return ""


@dataclass
class DelegationEvent:
    indexer: str
    tokens: float
    delegator: str
    block_timestamp: int
    transaction_hash: str
    event_type: str  # 'delegation' or 'undelegation'

    def to_dict(self):
        return {
            "indexer": self.indexer,
            "tokens": self.tokens,
            "delegator": self.delegator,
            "block_timestamp": self.block_timestamp,
            "block_datetime": datetime.fromtimestamp(self.block_timestamp, tz=timezone.utc),
            "transaction_hash": self.transaction_hash,
            "event_type": self.event_type,
        }


class DelegationFetcher:
    def __init__(self, SUBGRAPH_URL: str):
        self.subgraph_url = SUBGRAPH_URL

    def run_query(self, query: str) -> dict:
        response = requests.post(self.subgraph_url, json={"query": query})
        response.raise_for_status()
        return response.json()["data"]

    def fetch_events(self) -> List[DelegationEvent]:
        
        global TRANSACTION_COUNT

        query = f'''
        {{
          stakeDelegateds(orderBy: blockTimestamp, orderDirection: desc, first: {TRANSACTION_COUNT}) {{
            indexer
            tokens
            delegator
            blockTimestamp
            transactionHash
          }}
          stakeDelegatedLockeds(orderBy: blockTimestamp, orderDirection: desc, first: {TRANSACTION_COUNT}) {{
            indexer
            tokens
            delegator
            blockTimestamp
            transactionHash
          }}
        }}
        '''

        data = self.run_query(query)

        events = []

        for d in data["stakeDelegateds"]:
            events.append(DelegationEvent(
                indexer=d["indexer"],
                tokens=int(d["tokens"]),
                delegator=d["delegator"],
                block_timestamp=int(d["blockTimestamp"]),
                transaction_hash=d["transactionHash"],
                event_type="delegation"
            ))

        for u in data["stakeDelegatedLockeds"]:
            events.append(DelegationEvent(
                indexer=u["indexer"],
                tokens=int(u["tokens"]),
                delegator=u["delegator"],
                block_timestamp=int(u["blockTimestamp"]),
                transaction_hash=u["transactionHash"],
                event_type="undelegation"
            ))

        return sorted(events, key=lambda e: e.block_timestamp, reverse=True)


# FUNCTION SECTION


def fetch_indexer_avatar(address):
    queryAvatar = f'''
    {{
        indexers(where: {{ id: "{address.lower()}" }}) {{
            account {{
                metadata {{
                    image
                }}
            }}
        }}
    }}
    '''

    try:
        response = requests.post(AVATAR_SUBGRAPH_URL, json={"query": queryAvatar})
        response.raise_for_status()
        result = response.json()

        if not result or "data" not in result or result["data"] is None:
            log_message(f"⚠️ Unexpected avatar response structure:\n{json.dumps(result, indent=2)}")
            return ""

        indexers = result["data"].get("indexers", [])
        if not indexers:
            return ""

        account = indexers[0].get("account", {})
        metadata = account.get("metadata")

        if metadata is None:
            log_message(f"ℹ️ No metadata found for address {address}")
            return ""

        image = metadata.get("image", "")
        return image if image else ""

    except Exception as e:
        log_message(f"⚠️ Failed to fetch indexer avatar for address {address}: {e}")
        return ""
    
    
# Returns all the data about last delegations and undelegations
def fetch_metrics():
    global SUBGRAPH_URL, TRANSCATION_COUNT
    fetcher = DelegationFetcher(SUBGRAPH_URL)
    events = fetcher.fetch_events()
    return events
# End Function 'fetch_metrics'


# Returns all the data in a CSV file
def generate_delegators_to_csv(events: List[DelegationEvent]):
    global report_dir, log_file
    filename = "delegators.csv"
    csv_path = os.path.join(report_dir, filename)

    with open(csv_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=events[0].to_dict().keys())
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_dict())

    log_message(f"✅ Saved CSV file: {csv_path}")
# End Function 'generate_delegators_to_csv'


# Function that fetches ENS names
def fetch_ens_name2(address: str) -> str:

    global ENS_SUBGRAPH_URL

    headers = {
        "Content-Type": "application/json"
    }

    # Ensure address is lowercase and prefixed correctly
    address = address.lower()

    payload = {
        "query": queryENS,
        "variables": {
            "address": address
        }
    }

    try:
        response = requests.post(ENS_SUBGRAPH_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        domains = result.get("data", {}).get("domains", [])
        if domains and isinstance(domains, list) and "name" in domains[0]:
            return domains[0]["name"]
    except requests.RequestException as e:
        log_message(f"⚠️ ENS lookup failed for {address}: {e}")

    return ""
# End Function 'fetch_ens_name'


def generate_delegators_to_html(events: List[DelegationEvent]):
    global report_dir, log_file, TRANSACTION_COUNT, GRT_SIZE
    
    filename = "index.html"
    html_path = os.path.join(report_dir, filename)

    with open(html_path, mode='w') as f:
        f.write("""
            <!DOCTYPE html>
            <html lang="en">
            <head>

                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta name="description" content="Track real-time delegation and undelegation activity on The Graph Network with Graph Tools Pro's Delegators Activity Log, featuring detailed transaction data.">
                <meta name="robots" content="index, follow">

                <meta property="og:title" content="Graph Tools Pro :: Delegators Activity Log">
                <meta property="og:description" content="Monitor real-time delegation activity on The Graph Network, including indexer and delegator transactions.">
                <meta property="og:url" content="https://graphtools.pro/delegators/">
                <meta property="og:type" content="website">
                <meta property="og:image" content="https://graphtools.pro/graphtoolsprologo.jpg">
                
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="Graph Tools Pro :: Delegators Activity Log">
                <meta name="twitter:description" content="Monitor real-time delegation activity on The Graph Network, including indexer and delegator transactions.">
                <meta name="twitter:image" content="https://graphtools.pro/graphtoolsprologo.jpg">
                
                <title>Graph Tools Pro: Delegators Activity Log & Analytics</title>
                <link rel="canonical" href="https://graphtools.pro/delegators/">
                <link rel="icon" type="image/png" href="https://graphtools.pro/favicon.ico">
              
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
                </style>

                <script defer data-domain="graphtools.pro/delegators" src="https://plausible.io/js/script.file-downloads.hash.outbound-links.pageview-props.tagged-events.js"></script>
                <script>window.plausible = window.plausible || function() { (window.plausible.q = window.plausible.q || []).push(arguments) }</script>


            </head>
            <body class="dark-mode">
        """)
        
               
        # Header with breadcrumb and toggle
        f.write(f"""
            <div class="header-container">
                <div class="breadcrumb" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 500; font-size: 0.85em; letter-spacing: 0.3px; text-shadow: 0 1px 2px rgba(0,0,0,0.15);">
                    <a href="https://graphtools.pro" class="home-link" style="text-decoration: none;">🏠 Home</a>&nbsp;&nbsp;&raquo;&nbsp;&nbsp;
                    <span class="current-page-title">📊 Delegators Activity Log <span style="font-size: 0.85em; color: var(--text-color);">&nbsp;&nbsp;[last {TRANSACTION_COUNT * 2} transactions, excluding under {GRT_SIZE:,} GRT]</span></span>    
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
                    Generated on: {timestamp} - (updated every hour) - v{DASHBOARD_VERSION}
                </div>
            </div>
        """)

        
        total_delegated = sum(e.tokens for e in events if e.event_type == "delegation") // 10**18
        total_undelegated = sum(e.tokens for e in events if e.event_type == "undelegation") // 10**18
        net = total_delegated - total_undelegated
        
        net_color = "limegreen" if net >= 0 else "crimson"

        f.write(f"""
            <div style="display: flex; gap: 20px; margin-bottom: 30px;">
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Total Delegated</div>
                    <div style="font-size: 2em; font-weight: bold; color: limegreen;">{total_delegated:,} GRT</div>
                </div>
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Total Undelegated</div>
                    <div style="font-size: 2em; font-weight: bold; color: crimson;">{total_undelegated:,} GRT</div>
                </div>
                <div style="flex: 1; background: var(--table-bg); padding: 20px; border-radius: 10px; text-align: center;">
                    <div style="font-size: 1.2em; color: var(--text-color);">Net</div>
                    <div style="font-size: 2em; font-weight: bold; color: {net_color};">{net:,} GRT</div>
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
                    <div class="filter-bar">
                        <strong style="margin-left: 16px;">Filter for:</strong>
                        <a class="filter-button" href="#" data-filter="Delegations" onclick="filterByFlag('Delegations')">✅ Delegations</a>
                        | <a class="filter-button" href="#" data-filter="Undelegations" onclick="filterByFlag('Undelegations')">❌ Undelegation</a>
                        | <a class="filter-button" href="#" data-filter="All" onclick="filterByFlag('All')">🧹 Clear Filter</a>
                    </div>
                    <div class="filter-bar">
                        <strong style="margin-left: 16px;">Filter for:</strong>
                        <a class="filter-button" href="#" data-filter="50000" onclick="filterByGRT('50000')">💰 > 50,000 GRT</a>
                        | <a class="filter-button" href="#" data-filter="100000" onclick="filterByGRT('100000')">💰💰 > 100,000 GRT</a>
                        | <a class="filter-button" href="#" data-filter="1000000" onclick="filterByGRT('1000000')">💰💰💰 > 1M GRT</a>
                        | <a class="filter-button" href="#" data-filter="All" onclick="filterByGRT('All')">🧹 Clear Filter</a>
                    </div>
                </div>
            </div>
        """)

        f.write("""
            <table>
        """)
        
        headers = ["Event", "GRT", "Date", "Indexer", "Delegator", "Tx"]
        for header in headers:
            f.write(f"<th>{header}</th>")
        f.write("</tr>\n")

        key_order = ["event_type", "tokens", "block_datetime", "indexer", "delegator", "transaction_hash"]
        for event in events:
            if event.tokens < GRT_SIZE * 10**18:
                continue
            f.write("<tr>")
            data = event.to_dict()
            for key in key_order:
                value = data.get(key)

                if key == "block_datetime" and isinstance(value, datetime):
                    value = f'<span style="font-size: 0.85em;">{value.strftime("%Y-%m-%d %H:%M")}</span>'
                
                if key == "tokens":
                    value = f"{int(value) // 10**18:,}"

                if key == "event_type":
                    label = "✅ Delegation" if value == "delegation" else "❌ Undelegation"
                    value = f'<span style="font-size: 0.85em;">{label}</span>'

                if key in ("indexer", "delegator"):
                    ens_name = fetch_ens_name(value)
                    display_name = ens_name if ens_name else value

                    if key == "indexer":
                        avatar_url = fetch_indexer_avatar(value)
                        if avatar_url:
                            display_name = f'<img src="{avatar_url}" alt="avatar" style="height:20px;vertical-align:middle;margin-right:5px;">{display_name}'

                    link = f'<a href="https://thegraph.com/explorer/profile/{value}" target="_blank">{display_name}</a>'
                    value = f'<span style="font-size: 0.85em;">{link}</span>'
                
                if key == "transaction_hash":
                    value = f'<a href="https://arbiscan.io/tx/{value}" target="_blank"><span style="font-size: 0.85em;">view</span></a>'
                
                f.write(f"<td>{value}</td>")

            f.write("</tr>\n")
        
        f.write("""</table>
                    
                <hr class="footer-divider">
                <div class="footer">
                    ©<script>document.write(new Date().getFullYear())</script> 
                    <a href="https://graphtools.pro">Graph Tools Pro</a> :: Made with ❤️ by 
                    <a href="https://x.com/graphtronauts_c" target="_blank">Graphtronauts</a>
                    for <a href="https://x.com/graphprotocol" target="_blank">The Graph</a> ecosystem 👨‍🚀
                    <div style="margin-top: 8px;">
                        <span style="font-size: 0.8rem;">For Info: <a href="https://x.com/pdiomede" target="_blank">@pdiomede</a> & <a href="https://x.com/PaulBarba12" target="_blank">@PaulBarba12</a></span>
                    </div>
                </div>
                
                <script>
                    function toggleTheme() {
                        document.body.classList.toggle('light-mode');
                        const icon = document.getElementById('toggle-icon');
                        icon.textContent = document.body.classList.contains('light-mode') ? '☀️' : '🌙';
                    }
                
                    function downloadCSV() {
                        const link = document.createElement('a');
                        link.href = 'delegators.csv';
                        link.download = 'delegators.csv';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    }
                
                    function filterByFlag(flag) {
                        const rows = document.querySelectorAll("table tr");
                        rows.forEach((row, index) => {
                            if (index === 0) return; // skip header
                            const eventCell = row.cells[0];
                            if (!eventCell) return;
                            const isDelegation = eventCell.textContent.includes("Delegation");
                            const isUndelegation = eventCell.textContent.includes("Undelegation");
                            
                            if (flag === "Delegations" && !isDelegation) {
                                row.style.display = "none";
                            } else if (flag === "Undelegations" && !isUndelegation) {
                                row.style.display = "none";
                            } else {
                                row.style.display = "";
                            }
                        });
                        // Update active class on buttons
                        document.querySelectorAll('.filter-button').forEach(btn => {
                            btn.classList.remove('active-filter');
                        });
                        if (flag !== 'All') {
                            document.querySelectorAll('.filter-button').forEach(btn => {
                                if (btn.dataset.filter === flag) {
                                    btn.classList.add('active-filter');
                                }
                            });
                        }
                    }
                                        
                    function filterByGRT(flag) {
                        const rows = document.querySelectorAll("table tr");
                        rows.forEach((row, index) => {
                            if (index === 0) return; // skip header
                            const grtCell = row.cells[1];
                            if (!grtCell) return;
                        
                            const grtAmount = parseInt(grtCell.textContent.replace(/,/g, ""));
                        
                            if (flag === "All") {
                                row.style.display = "";
                            } else {
                                const threshold = parseInt(flag);
                                row.style.display = grtAmount > threshold ? "" : "none";
                            }
                        });
                        // Update active class on buttons
                        document.querySelectorAll('.filter-button').forEach(btn => {
                            btn.classList.remove('active-filter');
                        });
                        if (flag !== 'All') {
                            document.querySelectorAll('.filter-button').forEach(btn => {
                                if (btn.dataset.filter === flag) {
                                    btn.classList.add('active-filter');
                                }
                            });
                        }
                    }
                
                    document.getElementById("searchBox").addEventListener("input", function () {
                        const query = this.value.toLowerCase();
                        const rows = document.querySelectorAll("table tr");
                        
                        rows.forEach((row, index) => {
                            if (index === 0) return; // Skip header
                            const indexerCell = row.cells[3];
                            if (!indexerCell) return;
                        
                            const text = indexerCell.textContent.toLowerCase();
                            row.style.display = text.includes(query) ? "" : "none";
                        });
                    });
                
                </script>
            </body>
            </html>
        """)


if __name__ == "__main__":
    delegators = fetch_metrics()
    generate_delegators_to_csv(delegators)
    generate_delegators_to_html(delegators)
