#!/bin/bash

# Navigate to the GitHub dashboard project directory
cd /home/paolo/factory/delegators

# Activate the virtual environment
source venv/bin/activate

# Run the first script
echo "Running fetch_delegators_metrics.py ..."
python3 fetch_delegators_metrics.py

if [ $? -eq 0 ]; then
    echo "fetch_delegators_metrics.py completed"
    echo "Dashboards successfully generated."
else
    echo "Error: fetch_delegators_metrics.py failed."
fi
