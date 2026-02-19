#!/usr/bin/env bash
# run_enterprise.sh — Run enterprise cost-center benchmarks
# Usage: bash run_enterprise.sh  (from project root)
# Topology: star only (hrm may still be building; add it later)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Starting enterprise benchmark suite..."

# ---------------------------------------------------------------------------
# 1. Wait for benchmark_v2/__init__.py to be importable (retry 5x, 10s sleep)
# ---------------------------------------------------------------------------

MAX_RETRIES=5
RETRY_DELAY=10
ATTEMPT=0

until python3 -c "import benchmark_v2" 2>/dev/null; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ "$ATTEMPT" -ge "$MAX_RETRIES" ]; then
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ERROR: benchmark_v2 not importable after ${MAX_RETRIES} attempts. Aborting."
        exit 1
    fi
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] benchmark_v2 not importable yet (attempt ${ATTEMPT}/${MAX_RETRIES}). Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
done

echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] benchmark_v2 is importable. Proceeding..."

# ---------------------------------------------------------------------------
# 2. Create output directory
# ---------------------------------------------------------------------------

OUTPUT_DIR="benchmark_v2/results/enterprise"
mkdir -p "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# 3. Run the enterprise benchmark suite
#    run_suite.py lives inside benchmark_v2/ and adds parent to sys.path,
#    so invoke it as a module from the project root.
# ---------------------------------------------------------------------------

python3 benchmark_v2/run_suite.py \
    --tasks contract_review code_review_protocol support_triage_system \
    --topologies star \
    --iterations 3 \
    --output "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# 4. Echo completion with timestamp
# ---------------------------------------------------------------------------

echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] Enterprise benchmark suite complete. Results in: $OUTPUT_DIR"
