# Delegators Dashboard – The Graph Network

This project generates an interactive HTML dashboard to monitor live **delegation** and **undelegation** activity on [The Graph Network](https://thegraph.com/). 
It highlights transactions by delegators, indexed by timestamp, indexer, token amount, and transaction hash.

---

## 📌 Features

- Live dashboards for the most recent delegation/undelegation events
- ENS name resolution for delegator and indexer addresses
- Avatar integration for indexers (via subgraph metadata)
- Light/dark mode with theme toggle
- Filtering by event type and GRT thresholds
- CSV download of all listed transactions
- Clean, responsive layout with semantic HTML5
- Fully client-side (static file based, no backend needed)

---

## 📂 Project Structure
📁 delegators/
- 📜 fetch_delegators_metrics.py        # Main script to fetch and render dashboard
- 📜 .env                               # API keys and config (excluded via .gitignore)
- 📂 logs/                              # Auto-generated log files
- 📂 reports/
  - 📜 delegators.csv                  # Generated CSV
  - 📜 index.html                      # Generated dashboard
- 📂 archive/                          # Archived dashboard versions
---

## 🚀 How to Use

1. Clone the repo:

git clone https://github.com/pdiomede/delegators-dashboard.git
cd delegators-dashboard

2.	Create a .env file with the following variables:
```
GRAPH_API_KEY=your_graph_key
ENS_API_KEY=your_ens_key
TRANSACTION_COUNT=100
GRT_SIZE=10000
ENS_CACHE_FILE=ens_cache.json
ENS_CACHE_EXPIRY_HOURS=24
```

3.	Install dependencies:
pip install python-dotenv requests

4.	Run the script:
python fetch_delegators_metrics.py

5.	Open reports/index.html in your browser to view the dashboard.

## 🛡️ Notes
- .env and .DS_Store are excluded via .gitignore.
- API calls use The Graph Network
- ENS names are cached locally for performance.

## 📊 Powered By
- 🧠 The Graph
- 📛 ENS (Ethereum Name Service)
- 🧩 Python, HTML5, CSS3, DataTables.js
- 🌐 GitHub Pages / any static web host
