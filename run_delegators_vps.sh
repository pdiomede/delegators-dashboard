#!/bin/bash

NGINX_DIR="/var/www/graphtools.pro/delegators"

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

    # Copy reports to nginx folder
    echo "Copying reports to ${NGINX_DIR} ..."
    cp reports/index.html "${NGINX_DIR}/index.html" && \
    cp reports/delegators.csv "${NGINX_DIR}/delegators.csv" && \
    cp reports/social-card.jpeg "${NGINX_DIR}/social-card.jpeg"

    if [ $? -eq 0 ]; then
        # Ensure nginx can read the files regardless of who ran the script
        chmod 644 "${NGINX_DIR}/index.html" "${NGINX_DIR}/delegators.csv" "${NGINX_DIR}/social-card.jpeg"
        echo "Reports deployed to ${NGINX_DIR}"
    else
        echo "Error: failed to copy reports to ${NGINX_DIR}"
        exit 1
    fi
else
    echo "Error: fetch_delegators_metrics.py failed."
    exit 1
fi
