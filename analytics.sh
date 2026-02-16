#!/bin/bash
# analytics.sh — Detailed page-level analytics from nginx access log
# Usage: ./analytics.sh [days]  (default: 7)

ACCESS_LOG="/var/log/nginx/web-ceo.access.log"
DAYS=${1:-7}

if [ ! -f "$ACCESS_LOG" ]; then
    echo "No access log found at $ACCESS_LOG"
    exit 1
fi

echo "============================================"
echo "  DevToolbox Analytics Report"
echo "  Period: Last $DAYS day(s)"
echo "  Generated: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "============================================"
echo ""

# Calculate cutoff
CUTOFF_EPOCH=$(date -u -d "$DAYS days ago" +%s 2>/dev/null)

# Filter to recent entries and exclude static assets
FILTERED=$(mktemp)
while IFS= read -r line; do
    LOG_DATE=$(echo "$line" | grep -oP '\[\K[^\]]+' | head -1)
    if [ -n "$LOG_DATE" ]; then
        LOG_EPOCH=$(date -u -d "$(echo "$LOG_DATE" | sed 's|/| |g; s|:| |1')" +%s 2>/dev/null)
        if [ -n "$LOG_EPOCH" ] && [ "$LOG_EPOCH" -ge "$CUTOFF_EPOCH" ] 2>/dev/null; then
            echo "$line" >> "$FILTERED"
        fi
    fi
done < "$ACCESS_LOG"

TOTAL=$(wc -l < "$FILTERED")
UNIQUE_IPS=$(awk '{print $1}' "$FILTERED" | sort -u | wc -l)

echo "SUMMARY"
echo "-------"
echo "Total requests: $TOTAL"
echo "Unique visitors (IPs): $UNIQUE_IPS"
echo ""

echo "TOP PAGES (by hits)"
echo "--------------------"
awk '{print $7}' "$FILTERED" | grep -v '\.\(css\|js\|ico\|png\|jpg\|svg\|woff\|woff2\|ttf\)$' | sort | uniq -c | sort -rn | head -20
echo ""

echo "TOP REFERRERS"
echo "-------------"
awk -F'"' '{print $4}' "$FILTERED" | grep -v '^-$' | grep -v '46.225.49.219' | sort | uniq -c | sort -rn | head -10
echo ""

echo "HTTP STATUS CODES"
echo "-----------------"
awk '{print $9}' "$FILTERED" | sort | uniq -c | sort -rn
echo ""

echo "USER AGENTS (top 10)"
echo "--------------------"
awk -F'"' '{print $6}' "$FILTERED" | sort | uniq -c | sort -rn | head -10
echo ""

echo "HOURLY DISTRIBUTION"
echo "-------------------"
awk '{
    match($0, /\[([0-9]+\/[A-Za-z]+\/[0-9]+):([0-9]+)/, arr)
    if (arr[2] != "") print arr[2]
}' "$FILTERED" | sort | uniq -c | sort -k2n
echo ""

rm -f "$FILTERED"
