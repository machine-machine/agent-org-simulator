#!/usr/bin/env python3
"""
MachineMachine Benchmark Runner — with org memory injection
Compares single agent vs multi-agent org WITH accumulated lessons
"""
import httpx, json, os, time, datetime, subprocess, re
from pathlib import Path

def _load_cerebras_key():
    config = open(os.path.expanduser("~/.config/cerebras/config")).read()
    for line in config.splitlines():
        if line.startswith("CEREBRAS_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("CEREBRAS_API_KEY not found in config")

CEREBRAS_KEY = _load_cerebras_key()
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
MEMORY_SH = os.path.expanduser("~/.openclaw/skills/m2-memory/memory.sh")

TASK = """Design a complete incident response protocol for a 5-agent AI organization. 
Cover all of: (1) failure detection mechanisms, (2) inter-agent communication during incidents, 
(3) work redistribution when an agent goes offline, (4) agent recovery and reintegration, 
(5) post-incident knowledge capture. Be as comprehensive and technically specific as possible."""

def cerebras_call(prompt, max_tokens=2000):
    t0 = time.time()
    resp = httpx.post(CEREBRAS_URL,
        headers={"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
        json={"model": "zai-glm-4.7", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        timeout=90)
    data = resp.json()
    msg = data["choices"][0]["message"]
    # zai-glm-4.7 may return 'reasoning' instead of 'content'
    content = msg.get("content") or msg.get("reasoning") or ""
    return content, time.time() - t0

def get_lessons(query):
    try:
        result = subprocess.run([MEMORY_SH, "search", query, "--limit", "3"],
            capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else ""
    except:
        return ""

def run_benchmark(run_number: int):
    run_id = f"run_{str(run_number).zfill(3)}"
    results = {"run_id": run_id, "run_number": run_number, "timestamp": datetime.datetime.now().isoformat()}
    
    print(f"\n{'='*60}")
    print(f"BENCHMARK {run_id} — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print('='*60)
    
    # ── Single Agent ──────────────────────────────────────────────────
    print("\n[1/7] Single Agent baseline...")
    sa_prompt = f"You are an AI system architect. {TASK}"
    sa_output, sa_time = cerebras_call(sa_prompt, max_tokens=2500)
    results["single_agent"] = {"output": sa_output, "time": sa_time, "words": len(sa_output.split())}
    print(f"  ✅ {len(sa_output.split())} words in {sa_time:.1f}s")
    
    # ── Fetch lessons for each agent ──────────────────────────────────
    if run_number > 1:
        print("\n[2/7] Fetching org memory for agents...")
    
    AGENTS = [
        ("Systems Architect",      "failure detection heartbeat protocols", "technical detection mechanisms for agent failure: heartbeat protocols, timeout thresholds, health check APIs, circuit breaker patterns. Include timing values, protocol specs."),
        ("Coordination Specialist","inter-agent communication incident",    "inter-agent communication during incidents: message formats, escalation paths, consensus mechanisms. Include message schemas."),
        ("Governance Designer",    "governance decision incident response", "decision framework for incident response: authority levels, escalation thresholds, audit requirements, rollback procedures. Include decision trees."),
        ("Emergence Engineer",     "work redistribution load balancing",    "work redistribution when capacity drops: algorithms for load balancing, quality preservation under degraded conditions. Use concrete algorithms, not metaphors."),
        ("Network Analyst",        "post-incident learning knowledge graph","post-incident learning: metrics to capture, org memory updates, pattern detection, knowledge graph updates, preventing recurrence."),
    ]
    
    specialist_outputs = []
    agent_results = []
    total_specialist_time = 0
    
    for i, (name, memory_query, domain) in enumerate(AGENTS):
        print(f"\n[{i+3}/7] {name}...")
        
        lessons = ""
        if run_number > 1:
            lessons = get_lessons(memory_query)
            if lessons:
                lessons = f"\n\nLESSONS FROM PREVIOUS RUNS:\n{lessons}\nApply these lessons in your response.\n"
        
        prompt = f"You are the {name} for a 5-agent AI organization. Design the {domain}{lessons}\nBe extremely specific with technical details. Use concrete engineering specs, not abstract metaphors."
        output, elapsed = cerebras_call(prompt, max_tokens=3000)
        specialist_outputs.append(f"=== {name} ===\n{output}")
        agent_results.append({"agent": name, "words": len(output.split()), "time": elapsed})
        total_specialist_time += elapsed
        print(f"  ✅ {len(output.split())} words in {elapsed:.1f}s")
    
    # ── Synthesis ─────────────────────────────────────────────────────
    print("\n[7/7] Synthesis agent...")
    synthesis_lessons = get_lessons("synthesis structured json handoff protocol concrete") if run_number > 1 else ""
    
    synth_prompt = f"""You are the MachineMachine Synthesis Agent. Integrate these 5 specialist outputs into ONE unified incident response protocol.

CRITICAL INSTRUCTION: Preserve ALL technical specifics (numbers, schemas, code snippets, protocol names, timing values). Do NOT replace concrete specs with abstract metaphors or generic descriptions. Do NOT use terms like "Adaptive Organism", "Hydro-Organic Mesh", or "Voltage signals" unless they map to a real engineering concept. If two agents conflict, note both options with their tradeoffs.

{synthesis_lessons if synthesis_lessons else ""}

SPECIALIST INPUTS:
{'='*40}
{chr(10).join(specialist_outputs)}
{'='*40}

Produce a single coherent, technically detailed incident response protocol. Include ALL concrete specs (numbers, schemas, algorithms) from the specialists. Structure with clear sections for each of the 5 areas."""

    synth_output, synth_time = cerebras_call(synth_prompt, max_tokens=4000)
    results["multi_agent"] = {
        "specialists": agent_results,
        "synthesis": synth_output,
        "specialist_words": sum(a["words"] for a in agent_results),
        "synthesis_words": len(synth_output.split()),
        "total_time": total_specialist_time + synth_time,
        "parallel_time": max(a["time"] for a in agent_results) + synth_time
    }
    print(f"  ✅ {len(synth_output.split())} synthesis words in {synth_time:.1f}s")
    
    # ── Score both ────────────────────────────────────────────────────
    print("\n📊 Scoring...")
    score_prompt = f"""You are a technical evaluator. Rate these two AI outputs for incident response protocol quality.

RUBRIC (0-20 points each, 100 total):
1. Coverage: addresses ALL 5 areas (detection, communication, redistribution, recovery, post-incident learning)
2. Technical Depth: specific mechanisms, numbers, schemas, named protocols
3. Coherence: logically consistent, well-structured
4. Implementability: a dev team could actually build this
5. Edge Cases: handles cascading failures, partial outages, race conditions

OUTPUT A (Single Agent):
{results['single_agent']['output'][:1500]}

OUTPUT B (Multi-Agent Synthesis):
{results['multi_agent']['synthesis'][:1500]}

Score each output. Give integer values only. Use exactly this format at the end of your response:
A_coverage: [0-20]
A_depth: [0-20]
A_coherence: [0-20]
A_implementability: [0-20]
A_edge_cases: [0-20]
A_total: [0-100]
A_notes: [one sentence]
B_coverage: [0-20]
B_depth: [0-20]
B_coherence: [0-20]
B_implementability: [0-20]
B_edge_cases: [0-20]
B_total: [0-100]
B_notes: [one sentence]"""
    
    score_raw, _ = cerebras_call(score_prompt, max_tokens=4000)
    
    # Parse key:value format from the reasoning output (search from END for final values)
    def parse_scores(text, prefix):
        s = {}
        for key in ["coverage", "depth", "coherence", "implementability", "edge_cases", "total", "notes"]:
            pattern = rf'{prefix}_{key}:\s*(\d+)'
            # Find all matches, use the LAST one (end of reasoning = final answer)
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                val = matches[-1].group(1).strip()
                try:
                    s[key] = int(val)
                except:
                    s[key] = val
        # If total missing but others present, sum them
        if "total" not in s or not isinstance(s.get("total"), int):
            nums = [s.get(k, 0) for k in ["coverage","depth","coherence","implementability","edge_cases"] if isinstance(s.get(k), int)]
            if nums:
                s["total"] = sum(nums)
        return s
    
    scores = {
        "A": parse_scores(score_raw, "A"),
        "B": parse_scores(score_raw, "B")
    }
    results["scores"] = scores
    
    sa_score = scores.get("A", {}).get("total", 0) or 0
    ma_score = scores.get("B", {}).get("total", 0) or 0
    delta = ma_score - sa_score
    
    print(f"\n  Single Agent: {sa_score}/100")
    print(f"  Multi-Agent:  {ma_score}/100")
    print(f"  Delta:        {delta:+d}")
    
    return results, sa_score, ma_score, delta

# Run if called directly
if __name__ == "__main__":
    import sys
    run_num = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    results, sa, ma, delta = run_benchmark(run_num)
    
    # Save raw results
    out_path = Path(f"/home/developer/.openclaw/workspace/projects/agent-org-simulator/evolving_org/run_{str(run_num).zfill(3)}_results.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
