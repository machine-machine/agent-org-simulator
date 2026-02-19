#!/bin/bash
# MachineMachine Weekly Org Evolution Run
# Runs benchmark → retrospective → updates learning log → commits curve

set -e
cd /home/developer/.openclaw/workspace/projects/agent-org-simulator

# Determine run number
RUN_NUM=$(ls evolving_org/run_*_results.json 2>/dev/null | wc -l)
RUN_NUM=$((RUN_NUM + 1))

echo "Starting weekly evolution run #$RUN_NUM..."

# Run benchmark
python3 evolving_org/benchmark_runner.py $RUN_NUM

# Run retrospective
python3 evolving_org/retrospective.py "evolving_org/run_$(printf '%03d' $RUN_NUM)_results.json" "run_$(printf '%03d' $RUN_NUM)"

# Regenerate improvement curve
python3 evolving_org/plot_curve.py

# Update BENCHMARK_RESULTS.md with latest
python3 evolving_org/update_summary.py

# Commit everything
git add evolving_org/ BENCHMARK_RESULTS.md 2>/dev/null || true
git commit -m "weekly-run: evolution run #$RUN_NUM complete" || true
git push origin main || true

echo "✅ Run #$RUN_NUM complete."
