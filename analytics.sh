#!/bin/bash
set -euo pipefail

DAYS="${1:-7}"
if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then
    echo "Usage: ./analytics.sh [days]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOURS=$((DAYS * 24))

python3 "$SCRIPT_DIR/analyze_traffic.py" --hours "$HOURS"
