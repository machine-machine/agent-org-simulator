#!/usr/bin/env python3
"""
MachineMachine Evolving Org — Retrospective Engine
Runs after every benchmark. Commits lessons. Updates protocols.

Feedback loops (added 2026-02-19):
- Task 2: Extracts top technical discoveries → content_queue.json (content-org)
- Task 3: Updates strategy_context.md (content-org) after each run
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

# ── Shared file paths (content-org feedback loops) ───────────────────────────
# From: projects/agent-org-simulator/evolving_org/ → up 3 → projects/content-org/
_THIS_DIR = Path(__file__).parent
CONTENT_ORG_DIR = _THIS_DIR.parent.parent / "content-org"
CONTENT_QUEUE_FILE = CONTENT_ORG_DIR / "content_queue.json"
STRATEGY_CONTEXT_FILE = CONTENT_ORG_DIR / "strategy_context.md"

def cerebras_call(prompt, max_tokens=2000):
    resp = httpx.post(CEREBRAS_URL, 
        headers={"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
        json={"model": "zai-glm-4.7", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        timeout=60)
    msg = resp.json()["choices"][0]["message"]
    # zai-glm-4.7 may return 'reasoning' instead of 'content'
    return msg.get("content") or msg.get("reasoning") or ""


# ── Task 2: Extract technical discoveries → content_queue.json ───────────────

def extract_content_queue_items(retro: dict, run_id: str, results_text: str) -> list[dict]:
    """
    Ask Cerebras to extract top 2-3 technical discoveries from the benchmark run
    and format them as content queue items for the content-org flywheel.
    """
    key_finding = retro.get("key_finding", "")
    run_summary = retro.get("run_summary", "")
    memories = retro.get("memories", [])
    memories_text = "\n".join(
        f"  [{m.get('agent', '?')}] {m.get('memory', '')}" for m in memories
    )

    prompt = f"""You are extracting publishable technical discoveries from a MachineMachine benchmark run.

RUN ID: {run_id}
KEY FINDING: {key_finding}
SUMMARY: {run_summary}
AGENT MEMORIES:
{memories_text}

BENCHMARK RESULTS EXCERPT:
{results_text[:3000]}

Extract the 2-3 most concrete, publishable technical discoveries. Focus on:
- Specific algorithms or protocols discovered (e.g., "Phi Accrual failure detection outperformed simple timeout")
- Architectural patterns proven by the benchmark (e.g., "star topology outperforms mesh for coordination tasks")
- Counter-intuitive findings (e.g., "more agents doesn't mean better — 3 outperformed 5 on focused tasks")
- Mechanisms that have clear arXiv research backing

For each discovery, provide an arXiv search hint (keywords to find related papers).

Output ONLY valid JSON array, no markdown fences:
[
  {{
    "source": "{run_id}",
    "topic": "Specific technical discovery in one concrete sentence",
    "arxiv_hint": "2-4 keywords to search arXiv for related papers",
    "priority": "high",
    "added": "{datetime.date.today().isoformat()}",
    "used": false
  }}
]

Return 2-3 items maximum. Only include discoveries that would make interesting blog posts about AI org design."""

    print("  📋 Extracting content queue items...")
    raw = cerebras_call(prompt, max_tokens=1000)

    # Parse JSON array — handle reasoning model output (may emit thinking chain before JSON)
    clean = re.sub(r"```json\s*", "", raw)
    clean = re.sub(r"```\s*", "", clean)
    # Try all JSON arrays found, use the last complete one (model may emit partial then full)
    arr_candidates = list(re.finditer(r'\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]', clean, re.DOTALL))
    items = None
    for m in sorted(arr_candidates, key=lambda x: len(x.group()), reverse=True):
        try:
            parsed = json.loads(m.group())
            if isinstance(parsed, list) and parsed and "topic" in parsed[0]:
                items = parsed
                break
        except json.JSONDecodeError:
            continue

    if items:
        valid = []
        for item in items:
            if isinstance(item, dict) and "topic" in item:
                item["source"] = run_id
                item["added"] = datetime.date.today().isoformat()
                item["used"] = False
                item.setdefault("priority", "high")
                item.setdefault("arxiv_hint", "multi-agent AI systems")
                valid.append(item)
        if valid:
            return valid

    # ── Fallback: construct items from retro data directly ───────────────
    print(f"  ⚠️  Cerebras JSON parse failed — using retro data directly")
    fallback_items = []

    # Use key_finding as primary topic
    if key_finding and len(key_finding) > 20:
        # Derive arxiv_hint from key finding words
        hint_words = [w for w in key_finding.lower().split() if len(w) > 4][:4]
        fallback_items.append({
            "source": run_id,
            "topic": key_finding[:200],
            "arxiv_hint": " ".join(hint_words) if hint_words else "multi-agent AI organization",
            "priority": "high",
            "added": datetime.date.today().isoformat(),
            "used": False,
        })

    # Use highest-importance memory as second item
    sorted_mems = sorted(memories, key=lambda m: m.get("importance", 0), reverse=True)
    for mem in sorted_mems[:1]:
        mem_text = mem.get("memory", "")
        if mem_text and len(mem_text) > 20 and mem_text != key_finding[:len(mem_text)]:
            hint_words = [w for w in mem_text.lower().split() if len(w) > 4][:4]
            fallback_items.append({
                "source": run_id,
                "topic": mem_text[:200],
                "arxiv_hint": " ".join(hint_words) if hint_words else "LLM agent coordination",
                "priority": "high",
                "added": datetime.date.today().isoformat(),
                "used": False,
            })

    if fallback_items:
        print(f"  ✅ Fallback: created {len(fallback_items)} queue items from retro data")
    return fallback_items


def append_to_content_queue(items: list[dict]):
    """Append new items to content_queue.json in content-org."""
    if not items:
        return

    CONTENT_ORG_DIR.mkdir(parents=True, exist_ok=True)

    existing = []
    if CONTENT_QUEUE_FILE.exists():
        try:
            existing = json.loads(CONTENT_QUEUE_FILE.read_text())
        except Exception:
            existing = []

    # Avoid duplicate topics (simple dedup by topic prefix)
    existing_topics = {e.get("topic", "")[:50].lower() for e in existing}
    new_items = [
        item for item in items
        if item.get("topic", "")[:50].lower() not in existing_topics
    ]

    if new_items:
        existing.extend(new_items)
        CONTENT_QUEUE_FILE.write_text(json.dumps(existing, indent=2))
        print(f"  ✅ Added {len(new_items)} items to content_queue.json → {CONTENT_QUEUE_FILE}")
        for item in new_items:
            print(f"     - {item['topic'][:70]}")
    else:
        print(f"  ℹ️  No new content queue items (already queued or empty)")


# ── Task 3: Update strategy_context.md ───────────────────────────────────────

def update_strategy_context(retro: dict, run_id: str, run_number: int = None):
    """
    Write/update the shared strategy context file that the content-org Brand Voice
    and Scout agents read before generating content.
    """
    key_finding = retro.get("key_finding", "N/A")
    run_summary = retro.get("run_summary", "N/A")
    next_recs = retro.get("next_run_recommendations", [])
    hypothesis = retro.get("improvement_hypothesis", "")
    protocol = retro.get("protocol_suggestion", {}) or {}
    single = retro.get("single_agent_score", "?")
    multi = retro.get("multi_agent_score", "?")
    delta = retro.get("delta", "?")

    # Build arxiv keyword clusters from what improved performance
    arxiv_keywords = []
    if protocol:
        title = protocol.get("title", "")
        if title:
            # Convert protocol title to keyword clusters
            words = [w for w in title.lower().split() if len(w) > 3]
            if words:
                arxiv_keywords.append(" ".join(words[:3]) + " multi-agent")
    # Add from recommendations
    for rec in next_recs[:2]:
        rec_words = [w for w in rec.lower().split() if len(w) > 4][:3]
        if rec_words:
            arxiv_keywords.append(" ".join(rec_words))

    # Fallback keywords
    if not arxiv_keywords:
        arxiv_keywords = ["multi-agent coordination AI", "LLM organization learning"]

    # Load KPI data for tone guidance (if available)
    kpi_tone_guidance = "Data-backed, technical specificity drives engagement"
    org_memory_file = CONTENT_ORG_DIR / "results" / "org_memory.json"
    if org_memory_file.exists():
        try:
            mem = json.loads(org_memory_file.read_text())
            patterns = mem.get("content_patterns", [])
            if patterns:
                kpi_tone_guidance = "; ".join(patterns[:2])
        except Exception:
            pass

    run_num_str = f"#{run_number}" if run_number else run_id
    today = datetime.date.today().isoformat()

    content = f"""# Content Strategy Context (auto-updated by weekly org evolution)
Last updated: {today} | Run: {run_num_str}

## What the org proved this week
- {key_finding}
- Multi-agent score: {multi}/100, Single-agent score: {single}/100, Delta: {delta}
- {run_summary}

## Benchmark improvement hypothesis
{hypothesis if hypothesis else "Continue refining specialist coordination patterns"}

## Concepts to explore on arXiv
{chr(10).join(f'- {kw}' for kw in arxiv_keywords[:3])}

## Tone guidance from KPIs
- {kpi_tone_guidance}
- Show concrete mechanisms, not just conclusions
- Include failure modes and open questions — builds credibility

## Protocol proposed this run
{f"- {protocol.get('title', 'N/A')}: {protocol.get('description', '')[:120]}" if protocol else "- No protocol proposed this run"}

## Next run focus areas
{chr(10).join(f'- {r}' for r in next_recs[:3]) if next_recs else '- Continue current approach'}
"""

    CONTENT_ORG_DIR.mkdir(parents=True, exist_ok=True)
    STRATEGY_CONTEXT_FILE.write_text(content)
    print(f"  ✅ strategy_context.md updated → {STRATEGY_CONTEXT_FILE}")


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
    
    # ── 4. Feedback Loop: Extract discoveries → content_queue.json ─────
    print(f"\n  🔗 Feedback Loop: Extracting content queue items...")
    try:
        queue_items = extract_content_queue_items(retro, run_id, results)
        append_to_content_queue(queue_items)
    except Exception as e:
        print(f"  ⚠️  Content queue extraction failed: {e}")

    # ── 5. Feedback Loop: Update strategy_context.md ───────────────────
    print(f"\n  🗺️  Feedback Loop: Updating content strategy context...")
    try:
        # Infer run number from run_id if possible
        run_num = None
        m = re.search(r'(\d+)', run_id)
        if m:
            run_num = int(m.group(1))
        update_strategy_context(retro, run_id, run_number=run_num)
    except Exception as e:
        print(f"  ⚠️  Strategy context update failed: {e}")

    # ── 6. Return structured results ────────────────────────────────────
    return {
        "run_id": run_id,
        "retro": retro,
        "memories_stored": stored,
        "protocol_proposed": bool(protocol),
        "content_queue_items": len(queue_items) if 'queue_items' in dir() else 0,
        "strategy_context_updated": STRATEGY_CONTEXT_FILE.exists(),
    }

if __name__ == "__main__":
    results_file = sys.argv[1] if len(sys.argv) > 1 else \
        "/home/developer/.openclaw/workspace/projects/agent-org-simulator/BENCHMARK_RESULTS.md"
    run_id = sys.argv[2] if len(sys.argv) > 2 else None
    result = run_retrospective(results_file, run_id)
    print(f"\n✅ Retrospective complete: {result['run_id']}")
    print(json.dumps(result['retro'], indent=2)[:1000])
