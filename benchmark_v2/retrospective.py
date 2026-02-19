"""
BenchmarkSuite v2 — Retrospective Engine
Deterministic retrospective algorithm. Returns structured FixProposal.
Stores lessons in org_memory dict (portable, reproducible, no vector store dependency).
"""
import json
from dataclasses import dataclass
from .llm_clients import cerebras_call
from .evaluator import EvalResult


@dataclass
class FixProposal:
    failure_mode: str        # What went wrong
    root_cause: str          # Why it went wrong
    protocol_fix: str        # Concrete change to apply next run
    domain_grounding_hint: str  # Specialist prompt amendment to prevent domain drift
    memory_keys: dict[str, str]  # {role_memory_query: lesson_text} to store in org_memory


def run_retrospective(
    task_name: str,
    task_prompt: str,
    sa_output: str,
    ma_output: str,
    eval_result: EvalResult,
    topology: str,
    iteration: int,
    org_memory: dict,
    verbose: bool = True,
) -> FixProposal:
    """
    Analyze why MA org under/over-performed and generate a FixProposal.
    """
    delta = eval_result.delta_mean
    winner = eval_result.winner

    context = f"""
BENCHMARK RETROSPECTIVE — Iteration {iteration}
Task: {task_name}
Topology: {topology}
SA score: {eval_result.sa_mean:.1f} ± {eval_result.sa_std:.1f}
MA score: {eval_result.ma_mean:.1f} ± {eval_result.ma_std:.1f}
Delta: {delta:+.1f}
Winner: {winner.upper()}

TASK: {task_prompt[:500]}

SINGLE AGENT OUTPUT (truncated):
{sa_output[:1200]}

MULTI-AGENT OUTPUT (truncated):
{ma_output[:1200]}

EXISTING ORG MEMORY (what was already tried):
{json.dumps(org_memory, indent=2)[:800] if org_memory else "None yet."}
"""

    prompt = f"""{context}

You are the MachineMachine Retrospective Agent. Analyze this benchmark run with precision.

Answer these questions concisely:
1. FAILURE_MODE: What specific weakness caused MA to score {'lower' if delta < 0 else 'only marginally higher'} than SA?
2. ROOT_CAUSE: What is the underlying reason? (e.g., domain drift, synthesis loss, specialist overlap, abstraction instead of specifics)
3. PROTOCOL_FIX: What ONE concrete change to the specialist prompts or synthesis will fix this? Be very specific.
4. DOMAIN_GROUNDING: What phrase should be added to specialist prompts to prevent domain drift or bias?
5. MEMORY_LESSONS: For each of the 5 specialist roles, what is the ONE most important lesson from this run? (format: "role_name: lesson")

Output EXACTLY this format:
FAILURE_MODE: [one sentence]
ROOT_CAUSE: [one sentence]
PROTOCOL_FIX: [one or two sentences, very concrete]
DOMAIN_GROUNDING: [phrase to add to prompts]
MEMORY_LESSONS:
- Systems Architect: [lesson]
- Coordination Specialist: [lesson]
- Governance Designer: [lesson]
- Emergence Engineer: [lesson]
- Network Analyst: [lesson]
- synthesis_protocol: [lesson for synthesizer]"""

    if verbose:
        print(f"  [Retrospective] Analyzing iteration {iteration}...")

    retro_text, elapsed = cerebras_call(prompt, max_tokens=1000)

    if verbose:
        print(f"  [Retrospective] Done ({elapsed:.1f}s)")

    # Parse structured output
    def extract_field(text: str, field: str) -> str:
        import re
        pattern = rf'{re.escape(field)}:\s*(.+?)(?=\n[A-Z_]+:|$)'
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def extract_lessons(text: str) -> dict:
        lessons = {}
        import re
        # Look for "- Role Name: lesson" pattern
        matches = re.findall(r'-\s*(.+?):\s*(.+?)(?=\n-|\Z)', text, re.DOTALL)
        for role, lesson in matches:
            key = role.strip().lower().replace(" ", "_")
            lessons[key] = lesson.strip()
        return lessons

    failure_mode = extract_field(retro_text, "FAILURE_MODE")
    root_cause = extract_field(retro_text, "ROOT_CAUSE")
    protocol_fix = extract_field(retro_text, "PROTOCOL_FIX")
    domain_grounding = extract_field(retro_text, "DOMAIN_GROUNDING")

    # Extract lessons section
    lessons_section = ""
    if "MEMORY_LESSONS:" in retro_text:
        lessons_section = retro_text.split("MEMORY_LESSONS:")[1]
    memory_lessons = extract_lessons(lessons_section)

    # Update org_memory with new lessons
    for key, lesson in memory_lessons.items():
        existing = org_memory.get(key, "")
        if existing:
            org_memory[key] = f"{existing}\n[Iter {iteration}] {lesson}"
        else:
            org_memory[key] = f"[Iter {iteration}] {lesson}"

    if verbose and failure_mode:
        print(f"  Failure mode: {failure_mode}")
        print(f"  Fix: {protocol_fix}")

    return FixProposal(
        failure_mode=failure_mode or "Unknown",
        root_cause=root_cause or "Unknown",
        protocol_fix=protocol_fix or "Unknown",
        domain_grounding_hint=domain_grounding or "",
        memory_keys=memory_lessons,
    )
