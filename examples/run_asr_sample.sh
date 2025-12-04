#!/usr/bin/env bash
# Sample ASR run (safe) - scans localhost only
# Ensure .venv is active and you have permission to scan targets

set -euo pipefail

TARGETS_FILE="targets.txt"
cat > "$TARGETS_FILE" <<EOF
127.0.0.1
localhost
EOF

# Run ASR (safe mode, TLS check enabled, banner grabbing enabled)
python3 cli/main.py asr --targets "$TARGETS_FILE" --max-workers 10 --safe-mode --tls-check --format json --output results/asr_sample_summary.json

echo "ASR sample run complete. Results: results/asr_sample_summary.json"
