#!/usr/bin/env python3
"""
MachineMachine Evolving Org — Retrospective Engine
Runs after every benchmark. Commits lessons. Updates protocols.
"""
import json, sys, os, subprocess, datetime, re
from pathlib import Path

# Cerebras client
import httpx

def _load_cerebras_key():
    config = open(os.path.expanduser("~/.config/cerebras/config")).read()
    for line in config.splitlines():
        if line.startswith("CEREBRAS_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("CEREBRAS_API_KEY not found in config")
CEREBRAS_KEY = _load_cerebras_key()
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"

def cerebras_call(prompt, max_tokens=2000):
    resp = httpx.post(CEREBRAS_URL, 
        headers={"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
        json={"model": "zai-glm-4.7", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        timeout=60)
    msg = resp.json()["choices"][0]["message"]
    # zai-glm-4.7 may return 'reasoning' instead of 'content'
    return msg.get("content") or msg.get("reasoning") or ""

def run_retrospective(results_file: str, run_id: str = None):
    results = Path(results_file).read_text()
    run_id = run_id or f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n🔄 Running retrospective for {run_id}...")
    
    # ── 1. RetroAgent analysis ──────────────────────────────────────────
    # Extract scores if this is a JSON results file
    scores_summary = ""
    try:
        data = json.loads(results)
        if "scores" in data:
            sa = data["scores"].get("A", {}).get("total", "?")
            ma = data["scores"].get("B", {}).get("total", "?")
            scores_summary = f"SCORES: Single Agent={sa}/100, Multi-Agent={ma}/100, Delta={ma-sa if isinstance(sa,int) and isinstance(ma,int) else '?'}"
    except:
        # It's markdown, try to extract scores
        sa_m = re.search(r'Single Agent.*?(\d+)/100', results)
        ma_m = re.search(r'Multi.Agent.*?(\d+)/100', results)
        if sa_m and ma_m:
            sa, ma = int(sa_m.group(1)), int(ma_m.group(1))
            scores_summary = f"SCORES: Single Agent={sa}/100, Multi-Agent={ma}/100, Delta={ma-sa}"

    retro_prompt = f"""You are the MachineMachine Retrospective Agent. Analyze this benchmark run.

{scores_summary}

BENCHMARK RESULTS (summary):
{results[:5000]}

Produce a JSON analysis. Keep all string values SHORT (under 100 chars each). Use this exact structure:
{{
  "run_summary": "2-sentence summary",
  "single_agent_score": 0,
  "multi_agent_score": 0,
  "delta": 0,
  "key_finding": "most important insight",
  "memories": [
    {{"agent": "Systems Architect", "memory": "lesson learned", "importance": 0.8}},
    {{"agent": "Coordination Specialist", "memory": "lesson learned", "importance": 0.8}},
    {{"agent": "Governance Designer", "memory": "lesson learned", "importance": 0.8}},
    {{"agent": "Emergence Engineer", "memory": "lesson learned", "importance": 0.8}},
    {{"agent": "Network Analyst", "memory": "lesson learned", "importance": 0.8}},
    {{"agent": "org_level", "memory": "Synthesis lesson: key insight", "importance": 0.9}}
  ],
  "protocol_suggestion": {{
    "title": "Protocol title (5 words max)",
    "description": "What to change",
    "affected_agents": ["Synthesis", "Emergence Engineer"],
    "rationale": "Why this helps",
    "auto_merge": true,
    "confidence": 0.85
  }},
  "next_run_recommendations": ["try X", "improve Y", "fix Z"],
  "improvement_hypothesis": "If we fix X, score improves by Y because Z"
}}

Return ONLY the JSON object, no markdown fences, no explanation."""

    print("  📊 Calling RetroAgent...")
    retro_raw = cerebras_call(retro_prompt, max_tokens=6000)
    
    # Extract JSON — handle ```json code fences and reasoning model output
    # Try stripping code fences first
    clean = re.sub(r'```json\s*', '', retro_raw)
    clean = re.sub(r'```\s*', '', clean)
    # Find the LAST complete JSON object (model may emit partial ones during reasoning)
    json_candidates = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', clean, re.DOTALL))
    # Try from largest to smallest
    retro = None
    for m in sorted(json_candidates, key=lambda x: len(x.group()), reverse=True):
        try:
            retro = json.loads(m.group())
            if "run_summary" in retro or "key_finding" in retro:
                break
        except:
            continue
    
    if retro is None:
        # Last resort: try the raw full match
        json_match = re.search(r'\{.*\}', clean, re.DOTALL)
        if json_match:
            try:
                retro = json.loads(json_match.group())
            except:
                pass
    
    if retro is None:
        print(f"  ⚠️  Could not parse JSON from retro response. Raw:\n{retro_raw[:500]}")
        retro = {"memories": [], "protocol_suggestion": None, "key_finding": "Parse error", "run_summary": retro_raw[:200]}
    
    print(f"  ✅ Retro complete. Key finding: {retro.get('key_finding', 'N/A')}")
    
    # ── 2. Store memories to Qdrant ─────────────────────────────────────
    print("\n  🧠 Storing memories to Qdrant...")
    memory_script = os.path.expanduser("~/.openclaw/skills/m2-memory/memory.sh")
    stored = 0
    for mem in retro.get("memories", []):
        agent = mem.get("agent", "org_level")
        memory_text = f"[{run_id}][{agent}] {mem['memory']}"
        importance = mem.get("importance", 0.7)
        try:
            result = subprocess.run(
                [memory_script, "store", memory_text, "--importance", str(importance)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                stored += 1
            else:
                print(f"    ⚠️  Memory store stderr: {result.stderr[:100]}")
        except Exception as e:
            print(f"    ⚠️  Memory store failed: {e}")
    print(f"  ✅ Stored {stored}/{len(retro.get('memories', []))} memories")
    
    # ── 3. Protocol amendment to fleet-governance ───────────────────────
    protocol = retro.get("protocol_suggestion")
    if protocol:
        print(f"\n  📜 Proposing protocol amendment: {protocol.get('title', 'untitled')}...")
        fleet_dir = Path(os.path.expanduser("~/.openclaw/workspace/platform/fleet-governance"))
        protocols_file = fleet_dir / "PROTOCOLS.md"
        learning_log = fleet_dir / "LEARNING_LOG.md"
        
        # Append to PROTOCOLS.md
        amendment = f"""

## Amendment {run_id}: {protocol['title']}
**Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}
**Trigger:** Benchmark run {run_id} (delta: {retro.get('delta', 'N/A')})
**Confidence:** {protocol.get('confidence', 0):.0%}
**Affected agents:** {', '.join(protocol.get('affected_agents', []))}

### Change
{protocol['description']}

### Rationale
{protocol['rationale']}

### Status
{'AUTO-MERGED' if protocol.get('auto_merge') else 'PROPOSED — requires human review'}
"""
        with open(protocols_file, 'a') as f:
            f.write(amendment)
        
        # Append to LEARNING_LOG.md
        log_entry = f"""
## {run_id} — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

**Scores:** Single={retro.get('single_agent_score','?')}, Multi-Agent={retro.get('multi_agent_score','?')}, Delta={retro.get('delta','?')}
**Key Finding:** {retro.get('key_finding', 'N/A')}
**Summary:** {retro.get('run_summary', 'N/A')}
**Protocol Proposed:** {protocol['title']}
**Improvement Hypothesis:** {retro.get('improvement_hypothesis', 'N/A')}
**Next Run Recommendations:**
{chr(10).join('- ' + r for r in retro.get('next_run_recommendations', []))}

"""
        with open(learning_log, 'a') as f:
            f.write(log_entry)
        
        # Git commit
        try:
            subprocess.run(['git', 'add', 'PROTOCOLS.md', 'LEARNING_LOG.md'], cwd=fleet_dir, check=True)
            commit_msg = f"retro({run_id}): {protocol['title']}\n\nAuto-{'merged' if protocol.get('auto_merge') else 'proposed'} | confidence={protocol.get('confidence',0):.0%}\n{protocol['rationale'][:200]}"
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=fleet_dir, check=True)
            subprocess.run(['git', 'push', 'origin', 'main'], cwd=fleet_dir, check=True)
            print(f"  ✅ Protocol committed to fleet-governance")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Git commit failed: {e}")
    
    # ── 4. Return structured results ────────────────────────────────────
    return {
        "run_id": run_id,
        "retro": retro,
        "memories_stored": stored,
        "protocol_proposed": bool(protocol)
    }

if __name__ == "__main__":
    results_file = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/developer/.openclaw/workspace/projects/agent-org-simulator/BENCHMARK_RESULTS.md"
    run_id = sys.argv[2] if len(sys.argv) > 2 else None
    result = run_retrospective(results_file, run_id)
    print(f"\n✅ Retrospective complete: {result['run_id']}")
    print(json.dumps(result['retro'], indent=2)[:1000])
