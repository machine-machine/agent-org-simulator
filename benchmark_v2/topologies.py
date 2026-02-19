"""
BenchmarkSuite v2 — Org Topologies
Three multi-agent organizational structures to compare.
"""
import time
from dataclasses import dataclass
from .tasks import Task
from .llm_clients import cerebras_call, load_cerebras_key

@dataclass
class TopologyResult:
    topology: str
    final_output: str
    specialist_outputs: list[dict]
    total_time: float
    parallel_time: float  # min possible if specialists ran in parallel


def _specialist_prompt(role, task: Task, org_memory: dict = None, prior_output: str = None) -> str:
    lessons = ""
    if org_memory:
        key = role.memory_query
        lessons_text = org_memory.get(key, "")
        if lessons_text:
            lessons = f"\n\nLESSONS FROM PREVIOUS RUNS:\n{lessons_text}\nApply these lessons.\n"

    prior = ""
    if prior_output:
        prior = f"\n\nPREVIOUS SPECIALIST OUTPUT TO REFINE:\n{prior_output[:2000]}\n\nBuild on this, correct errors, and add your specialized perspective.\n"

    return (
        f"You are the {role.name} for a 5-agent AI organization. "
        f"Design the {role.domain_instruction}{lessons}{prior}\n"
        "Be extremely specific with technical details. Use concrete engineering specs, not abstract metaphors."
    )


def _synthesis_prompt(task: Task, specialist_outputs: list[tuple[str, str]], org_memory: dict = None) -> str:
    lessons = ""
    if org_memory:
        synth_lessons = org_memory.get("synthesis_protocol", "")
        if synth_lessons:
            lessons = f"\n\nLESSONS ON SYNTHESIS FROM PREVIOUS RUNS:\n{synth_lessons}\n"

    specialists_text = "\n\n".join(f"=== {name} ===\n{output}" for name, output in specialist_outputs)

    return (
        f"You are the MachineMachine Synthesis Agent. Integrate these {len(specialist_outputs)} specialist outputs "
        f"into ONE unified response for this task:\n\n{task.prompt}\n\n"
        "CRITICAL: Preserve ALL technical specifics (numbers, schemas, code snippets, protocol names, timing values). "
        "Do NOT replace concrete specs with abstract metaphors. "
        "If specialists conflict, note both options with tradeoffs.\n"
        f"{lessons}\n"
        f"SPECIALIST INPUTS:\n{'='*40}\n{specialists_text}\n{'='*40}\n\n"
        "Produce a single coherent, technically detailed response. "
        "Include ALL concrete specs from the specialists. Structure with clear sections for each required area."
    )


def run_star(task: Task, org_memory: dict = None) -> TopologyResult:
    """5 specialists in parallel → 1 synthesizer."""
    specialist_outputs = []
    specialist_times = []

    for role in task.specialist_roles:
        prompt = _specialist_prompt(role, task, org_memory)
        output, elapsed = cerebras_call(prompt, max_tokens=2500)
        specialist_outputs.append({"role": role.name, "output": output, "time": elapsed})
        specialist_times.append(elapsed)

    synth_prompt = _synthesis_prompt(
        task,
        [(s["role"], s["output"]) for s in specialist_outputs],
        org_memory
    )
    final_output, synth_time = cerebras_call(synth_prompt, max_tokens=4000)

    return TopologyResult(
        topology="star",
        final_output=final_output,
        specialist_outputs=specialist_outputs,
        total_time=sum(specialist_times) + synth_time,
        parallel_time=max(specialist_times) + synth_time,
    )


def run_pipeline(task: Task, org_memory: dict = None) -> TopologyResult:
    """Specialists in series — each sees and refines previous output."""
    specialist_outputs = []
    current_output = ""

    for role in task.specialist_roles:
        prompt = _specialist_prompt(role, task, org_memory, prior_output=current_output if current_output else None)
        output, elapsed = cerebras_call(prompt, max_tokens=3000)
        specialist_outputs.append({"role": role.name, "output": output, "time": elapsed})
        # Each specialist's output becomes input to the next (append their contribution)
        current_output = output

    total_time = sum(s["time"] for s in specialist_outputs)

    return TopologyResult(
        topology="pipeline",
        final_output=current_output,  # last specialist's output is the final product
        specialist_outputs=specialist_outputs,
        total_time=total_time,
        parallel_time=total_time,  # inherently serial
    )


def run_peer_review(task: Task, org_memory: dict = None) -> TopologyResult:
    """Phase 1: draft independently. Phase 2: cross-critique. Phase 3: synthesize with critiques."""
    # Phase 1: independent drafts
    drafts = []
    for role in task.specialist_roles:
        prompt = _specialist_prompt(role, task, org_memory)
        output, elapsed = cerebras_call(prompt, max_tokens=2000)
        drafts.append({"role": role.name, "output": output, "time": elapsed})

    # Phase 2: each specialist reviews 2 others (round-robin)
    critiques = []
    n = len(drafts)
    for i, reviewer in enumerate(drafts):
        review_targets = [(i + 1) % n, (i + 2) % n]
        targets_text = "\n\n".join(
            f"=== {drafts[j]['role']} draft ===\n{drafts[j]['output'][:800]}"
            for j in review_targets
        )
        critique_prompt = (
            f"You are the {reviewer['role']}. Critically review these 2 specialist drafts "
            f"for the task: {task.name}.\n\n{targets_text}\n\n"
            "Identify: (1) technical errors or gaps, (2) missing edge cases, "
            "(3) conflicts with your own domain expertise. Be specific and constructive. "
            "Keep your critique under 300 words."
        )
        critique, elapsed = cerebras_call(critique_prompt, max_tokens=500)
        critiques.append({"reviewer": reviewer["role"], "critique": critique, "time": elapsed})

    # Phase 3: synthesis with critique awareness
    all_drafts_text = "\n\n".join(f"=== {d['role']} ===\n{d['output']}" for d in drafts)
    all_critiques_text = "\n\n".join(f"[{c['reviewer']} critique]: {c['critique']}" for c in critiques)
    synth_prompt = (
        f"You are the MachineMachine Synthesis Agent. Integrate these specialist drafts "
        f"into ONE unified response, informed by the peer critiques.\n\n"
        f"TASK: {task.prompt}\n\n"
        f"DRAFTS:\n{all_drafts_text[:4000]}\n\n"
        f"PEER CRITIQUES:\n{all_critiques_text[:2000]}\n\n"
        "Address the critiques, resolve conflicts, and produce a technically precise unified response."
    )
    final_output, synth_time = cerebras_call(synth_prompt, max_tokens=4000)

    all_outputs = drafts + critiques
    total_time = sum(d["time"] for d in drafts) + sum(c["time"] for c in critiques) + synth_time

    return TopologyResult(
        topology="peer_review",
        final_output=final_output,
        specialist_outputs=all_outputs,
        total_time=total_time,
        parallel_time=max(d["time"] for d in drafts) + max(c["time"] for c in critiques) + synth_time,
    )


TOPOLOGY_RUNNERS = {
    "star": run_star,
    "pipeline": run_pipeline,
    "peer_review": run_peer_review,
}
