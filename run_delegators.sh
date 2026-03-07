#!/bin/bash

# Navigate to the script's own directory
cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install / upgrade dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run the script
echo "Running fetch_delegators_metrics.py ..."
python3 fetch_delegators_metrics.py

if [ $? -eq 0 ]; then
    echo "fetch_delegators_metrics.py completed"
    echo "Dashboards successfully generated."
else
    echo "Error: fetch_delegators_metrics.py failed."
fi
