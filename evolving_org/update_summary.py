#!/usr/bin/env python3
"""
Update BENCHMARK_RESULTS.md with a summary of all runs.
"""
import json, re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
RESULTS_MD = BASE_DIR.parent / "BENCHMARK_RESULTS.md"

def load_runs():
    runs = []
    for f in sorted(BASE_DIR.glob("run_*_results.json")):
        try:
            data = json.loads(f.read_text())
            run_num = data.get("run_number") or int(re.search(r'run_(\d+)', f.name).group(1))
            sa = data.get("scores", {}).get("A", {}).get("total", 0) or 0
            ma = data.get("scores", {}).get("B", {}).get("total", 0) or 0
            runs.append({
                "run": run_num,
                "run_id": data.get("run_id", f"run_{str(run_num).zfill(3)}"),
                "sa": sa,
                "ma": ma,
                "delta": ma - sa,
                "timestamp": data.get("timestamp", ""),
                "key_finding": data.get("key_finding", "")
            })
        except Exception as e:
            print(f"  ⚠️  Could not load {f}: {e}")
    return sorted(runs, key=lambda x: x["run"])

def update_summary():
    runs = load_runs()
    if not runs:
        print("No runs found.")
        return

    existing = RESULTS_MD.read_text() if RESULTS_MD.exists() else ""
    
    # Build evolution summary section
    table_rows = []
    for r in runs:
        sign = "+" if r["delta"] >= 0 else ""
        won = "🏆 MA" if r["delta"] > 0 else ("🏆 SA" if r["delta"] < 0 else "TIE")
        table_rows.append(f"| {r['run_id']} | {r['sa']}/100 | {r['ma']}/100 | {sign}{r['delta']} | {won} |")

    first = runs[0]
    latest = runs[-1]
    improved = latest["delta"] > first["delta"]

    summary = f"""

---

## Evolution Summary (Auto-Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')})

| Run | Single Agent | Multi-Agent | Delta | Winner |
|-----|-------------|-------------|-------|--------|
{chr(10).join(table_rows)}

**Runs completed:** {len(runs)}  
**Multi-agent improvement:** Delta went from {first['delta']:+d} (run 1) → {latest['delta']:+d} (latest)  
**Self-evolution status:** {'✅ CONFIRMED — org improved across runs' if improved else '🔄 In progress'}

📊 [View Improvement Curve](evolving_org/improvement_curve.html)  
🔗 [Fleet Governance Protocols](https://github.com/machine-machine/fleet-governance)
"""

    # Replace or append the evolution summary
    if "## Evolution Summary" in existing:
        # Replace from the evolution summary section to end
        new_content = re.sub(r'\n---\n\n## Evolution Summary.*$', summary, existing, flags=re.DOTALL)
    else:
        new_content = existing.rstrip() + summary

    RESULTS_MD.write_text(new_content)
    print(f"✅ Updated {RESULTS_MD}")
    print(f"   Runs: {len(runs)}, Latest delta: {latest['delta']:+d}")

if __name__ == "__main__":
    update_summary()
