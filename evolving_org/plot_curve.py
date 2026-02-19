#!/usr/bin/env python3
"""
MachineMachine Improvement Curve Generator
Reads all run_NNN_results.json files and generates an HTML chart.
"""
import json, re, os
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_HTML = BASE_DIR / "improvement_curve.html"

def load_runs():
    runs = []
    for f in sorted(BASE_DIR.glob("run_*_results.json")):
        try:
            data = json.loads(f.read_text())
            run_num = data.get("run_number") or int(re.search(r'run_(\d+)', f.name).group(1))
            sa = data.get("scores", {}).get("A", {}).get("total", 0) or 0
            ma = data.get("scores", {}).get("B", {}).get("total", 0) or 0
            amendments = data.get("protocol_amendments", [])
            key_finding = data.get("key_finding", "")
            runs.append({
                "run": run_num,
                "sa": sa,
                "ma": ma,
                "delta": ma - sa,
                "amendments": amendments,
                "key_finding": key_finding,
                "run_id": data.get("run_id", f"run_{str(run_num).zfill(3)}")
            })
        except Exception as e:
            print(f"  ⚠️  Could not load {f}: {e}")
    return sorted(runs, key=lambda x: x["run"])

def load_learning_log():
    """Extract protocol amendments from LEARNING_LOG.md"""
    log_path = Path(os.path.expanduser("~/.openclaw/workspace/platform/fleet-governance/LEARNING_LOG.md"))
    amendments = []
    if log_path.exists():
        content = log_path.read_text()
        for section in re.split(r'\n## ', content):
            run_match = re.match(r'(run_\d+)', section)
            protocol_match = re.search(r'\*\*Protocol Proposed:\*\* (.+)', section)
            if run_match and protocol_match:
                amendments.append({
                    "run_id": run_match.group(1),
                    "protocol": protocol_match.group(1).strip()
                })
    return amendments

def generate_html(runs, amendments):
    if not runs:
        print("  No runs found, generating placeholder chart.")
        runs = [{"run": 1, "sa": 90, "ma": 73, "delta": -17, "run_id": "run_001"}]

    labels = [f"Run {r['run']}" for r in runs]
    sa_data = [r["sa"] for r in runs]
    ma_data = [r["ma"] for r in runs]
    delta_data = [r["delta"] for r in runs]

    # Amendment annotations
    annotation_lines = []
    for r in runs:
        if r.get("amendments"):
            for amend in r["amendments"]:
                annotation_lines.append(f'  {{run: {r["run"]}, label: "{amend[:40]}..."}}')
    
    # Build amendment JS objects for vertical lines
    amend_js = ",\n".join(annotation_lines) if annotation_lines else ""

    # Summary stats
    first_delta = runs[0]["delta"] if runs else 0
    last_delta = runs[-1]["delta"] if runs else 0
    improved = last_delta > first_delta

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MachineMachine — Org Improvement Curve</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0a0a0f;
    color: #e0e0e0;
    font-family: 'SF Mono', 'Fira Code', monospace;
    min-height: 100vh;
    padding: 40px 20px;
  }}
  .container {{
    max-width: 900px;
    margin: 0 auto;
  }}
  .header {{
    text-align: center;
    margin-bottom: 40px;
  }}
  .header h1 {{
    font-size: 2rem;
    background: linear-gradient(135deg, #00d4ff, #7b2ff7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}
  .header p {{
    color: #888;
    font-size: 0.9rem;
  }}
  .chart-container {{
    background: #111120;
    border: 1px solid #1e1e3a;
    border-radius: 12px;
    padding: 30px;
    margin-bottom: 30px;
  }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
  }}
  .stat-card {{
    background: #111120;
    border: 1px solid #1e1e3a;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
  }}
  .stat-value {{
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 6px;
  }}
  .stat-label {{
    font-size: 0.8rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .positive {{ color: #00d4ff; }}
  .negative {{ color: #ff4757; }}
  .neutral {{ color: #7b2ff7; }}
  .amendments {{
    background: #111120;
    border: 1px solid #1e1e3a;
    border-radius: 12px;
    padding: 24px;
  }}
  .amendments h3 {{
    color: #00d4ff;
    margin-bottom: 16px;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 2px;
  }}
  .amendment-item {{
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 10px 0;
    border-bottom: 1px solid #1e1e3a;
  }}
  .amendment-item:last-child {{ border-bottom: none; }}
  .amend-run {{
    color: #7b2ff7;
    font-size: 0.85rem;
    min-width: 60px;
  }}
  .amend-text {{
    color: #ccc;
    font-size: 0.85rem;
    line-height: 1.4;
  }}
  .verdict {{
    text-align: center;
    padding: 20px;
    background: {'rgba(0, 212, 255, 0.1)' if improved else 'rgba(255, 71, 87, 0.1)'};
    border: 1px solid {'#00d4ff' if improved else '#ff4757'};
    border-radius: 8px;
    margin-bottom: 30px;
    font-size: 1.1rem;
  }}
  .footer {{
    text-align: center;
    color: #444;
    font-size: 0.8rem;
    margin-top: 30px;
  }}
  .footer a {{ color: #7b2ff7; text-decoration: none; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>MachineMachine Org Improvement Curve</h1>
    <p>Self-evolving AI organization — benchmark scores across runs</p>
  </div>

  <div class="verdict">
    {'✅ Multi-agent org IMPROVED from run 1 to run ' + str(runs[-1]["run"]) + ' — self-evolving architecture confirmed' if improved else '🔄 Org learning in progress — delta: ' + str(first_delta) + ' → ' + str(last_delta)}
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value neutral">{len(runs)}</div>
      <div class="stat-label">Total Runs</div>
    </div>
    <div class="stat-card">
      <div class="stat-value {'positive' if runs[-1]['sa'] >= 70 else 'neutral'}">{runs[-1]["sa"]}<span style="font-size:1rem">/100</span></div>
      <div class="stat-label">Single Agent (latest)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value {'positive' if runs[-1]['ma'] >= 70 else 'neutral'}">{runs[-1]["ma"]}<span style="font-size:1rem">/100</span></div>
      <div class="stat-label">Multi-Agent (latest)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value {'positive' if last_delta > 0 else 'negative'}">{last_delta:+d}</div>
      <div class="stat-label">Delta (multi − single)</div>
    </div>
  </div>

  <div class="chart-container">
    <canvas id="improvementChart" height="300"></canvas>
  </div>

  <div class="amendments">
    <h3>Protocol Amendments</h3>
    {chr(10).join(f'<div class="amendment-item"><span class="amend-run">{a["run_id"]}</span><span class="amend-text">{a["protocol"]}</span></div>' for a in amendments) if amendments else '<p style="color:#888">No amendments yet.</p>'}
  </div>

  <div class="footer">
    <p>Generated by MachineMachine Evolving Org Engine · <a href="https://github.com/machine-machine/agent-org-simulator">github.com/machine-machine/agent-org-simulator</a></p>
  </div>
</div>

<script>
const ctx = document.getElementById('improvementChart').getContext('2d');

const labels = {json.dumps(labels)};
const singleAgentData = {json.dumps(sa_data)};
const multiAgentData = {json.dumps(ma_data)};
const deltaData = {json.dumps(delta_data)};

const chart = new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [
      {{
        label: 'Single Agent',
        data: singleAgentData,
        borderColor: '#888888',
        backgroundColor: 'rgba(136, 136, 136, 0.1)',
        borderWidth: 2,
        pointRadius: 6,
        pointBackgroundColor: '#888888',
        tension: 0.3,
      }},
      {{
        label: 'Multi-Agent Org',
        data: multiAgentData,
        borderColor: '#00d4ff',
        backgroundColor: 'rgba(0, 212, 255, 0.1)',
        borderWidth: 3,
        pointRadius: 7,
        pointBackgroundColor: '#00d4ff',
        tension: 0.3,
        fill: true,
      }},
      {{
        label: 'Delta (MA - SA)',
        data: deltaData,
        borderColor: '#7b2ff7',
        backgroundColor: 'rgba(123, 47, 247, 0.05)',
        borderWidth: 2,
        borderDash: [5, 5],
        pointRadius: 5,
        pointBackgroundColor: '#7b2ff7',
        tension: 0.3,
        yAxisID: 'deltaAxis',
      }}
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{
      intersect: false,
      mode: 'index',
    }},
    plugins: {{
      legend: {{
        labels: {{
          color: '#aaa',
          font: {{ family: 'SF Mono, monospace', size: 12 }}
        }}
      }},
      tooltip: {{
        backgroundColor: '#111120',
        borderColor: '#1e1e3a',
        borderWidth: 1,
        titleColor: '#00d4ff',
        bodyColor: '#ccc',
      }}
    }},
    scales: {{
      x: {{
        grid: {{ color: '#1e1e3a' }},
        ticks: {{ color: '#888', font: {{ family: 'monospace' }} }}
      }},
      y: {{
        min: 0,
        max: 100,
        grid: {{ color: '#1e1e3a' }},
        ticks: {{
          color: '#888',
          font: {{ family: 'monospace' }},
          callback: v => v + '/100'
        }},
        title: {{ display: true, text: 'Score', color: '#888' }}
      }},
      deltaAxis: {{
        position: 'right',
        min: -40,
        max: 40,
        grid: {{ drawOnChartArea: false }},
        ticks: {{
          color: '#7b2ff7',
          font: {{ family: 'monospace' }},
          callback: v => (v > 0 ? '+' : '') + v
        }},
        title: {{ display: true, text: 'Delta', color: '#7b2ff7' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

    OUTPUT_HTML.write_text(html)
    print(f"  ✅ Improvement curve written to {OUTPUT_HTML}")
    return OUTPUT_HTML

if __name__ == "__main__":
    print("📈 Generating improvement curve...")
    runs = load_runs()
    amendments = load_learning_log()
    print(f"  Found {len(runs)} runs, {len(amendments)} protocol amendments")
    for r in runs:
        print(f"  Run {r['run']}: SA={r['sa']}, MA={r['ma']}, delta={r['delta']:+d}")
    generate_html(runs, amendments)
    print("✅ Done")
