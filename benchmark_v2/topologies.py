"""
BenchmarkSuite v2 — Org Topologies
Four multi-agent organizational structures to compare:
  - star:        5 parallel specialists → 1 synthesizer
  - pipeline:    5 specialists in serial, each refining prior output
  - peer_review: draft → cross-critique → synthesis
  - hrm:         Hierarchical Reasoning Model — recurrent f_H/f_L loop
                 (inspired by arxiv:2506.21734)
"""
import json
import re
import time
from dataclasses import dataclass, field
from .tasks import Task
from .llm_clients import cerebras_call, load_cerebras_key, token_tracker

@dataclass
class TopologyResult:
    topology: str
    final_output: str
    specialist_outputs: list[dict]
    total_time: float
    parallel_time: float  # min possible if specialists ran in parallel
    metadata: dict = field(default_factory=dict)  # topology-specific extras (e.g. HRM loop data)
    token_summary: dict = None  # cost tracking: tokens + USD cost for this run


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
    token_tracker.reset()
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
        token_summary=token_tracker.summary(),
    )


def run_pipeline(task: Task, org_memory: dict = None) -> TopologyResult:
    """Specialists in series — each sees and refines previous output."""
    token_tracker.reset()
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
        token_summary=token_tracker.summary(),
    )


def run_peer_review(task: Task, org_memory: dict = None) -> TopologyResult:
    """Phase 1: draft independently. Phase 2: cross-critique. Phase 3: synthesize with critiques."""
    token_tracker.reset()
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
        token_summary=token_tracker.summary(),
    )


def _hrm_coordinator_prompt(
    task: Task,
    loop: int,
    max_loops: int,
    current_outputs: dict,  # {role_name: output_text}
    org_memory: dict,
) -> str:
    """
    Build the f_H (high-level coordinator) prompt.
    On loop 1: no specialist output yet — issue initial instructions.
    On subsequent loops: assess quality, identify gaps, decide LOOP or DONE.
    """
    if current_outputs:
        outputs_section = "\n\nCURRENT SPECIALIST OUTPUTS (assess these critically):\n"
        for role_name, output in current_outputs.items():
            snippet = output[:700].rstrip()
            outputs_section += f"\n--- {role_name} ---\n{snippet}\n[...truncated...]\n"
    else:
        outputs_section = "\n\nThis is loop 1 — no specialist outputs yet. Issue comprehensive initial instructions."

    mem_section = ""
    if org_memory:
        mem_json = json.dumps(org_memory, indent=2)[:600]
        mem_section = f"\n\nORG MEMORY (lessons from previous benchmark runs — apply these):\n{mem_json}"

    final_loop_note = (
        f"\nIMPORTANT: This is the FINAL loop ({loop}/{max_loops}). Output status=DONE. "
        "In specialist_instructions, provide synthesis guidance summarising everything achieved."
        if loop >= max_loops else ""
    )

    return (
        "You are the High-Level Coordinator (f_H) of a Hierarchical Reasoning Model.\n"
        "Your role: strategic oversight, gap analysis, and specialist orchestration.\n\n"
        f"TASK:\n{task.prompt}"
        f"{outputs_section}"
        f"{mem_section}\n\n"
        f"CURRENT LOOP: {loop} of {max_loops}{final_loop_note}\n\n"
        "YOUR RESPONSIBILITIES:\n"
        "1. Assess what specialists have produced: what is STRONG, what is MISSING or too vague\n"
        "2. Decide: if all hard constraints are covered with sufficient technical depth → DONE\n"
        "   Otherwise → LOOP with targeted refinement instructions\n"
        "3. Instructions must be SPECIFIC: say 'add exact RSI threshold and lookback period' "
        "not 'improve technical depth'\n"
        "4. On loop 1, always output LOOP with full bootstrap instructions for each specialist\n\n"
        "OUTPUT FORMAT — respond with ONLY valid JSON, no other text:\n"
        '{"status": "LOOP", "specialist_instructions": {"RoleName": "specific instruction"}, '
        '"refinement_focus": "brief: what still needs work", "quality_assessment": "what was good"}\n'
        "OR\n"
        '{"status": "DONE", "specialist_instructions": {}, '
        '"refinement_focus": "", "quality_assessment": "summary of what was achieved"}\n\n'
        "RULES:\n"
        "- specialist_instructions must cover ALL specialist roles by exact name\n"
        "- Be concrete: reference specific missing values, formulas, or protocol names\n"
        "- Loop 1: always LOOP; Final loop: always DONE"
    )


def _parse_coordinator_plan(raw: str, task: Task) -> dict:
    """
    Parse coordinator JSON plan. Falls back gracefully if output is malformed.
    Returns a dict with keys: status, specialist_instructions, refinement_focus, quality_assessment.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

    # Try direct JSON parse
    try:
        plan = json.loads(cleaned)
        if "status" in plan:
            return plan
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            plan = json.loads(match.group())
            if "status" in plan:
                return plan
        except (json.JSONDecodeError, ValueError):
            pass

    # Hard fallback: extract status keyword, use default instructions
    status = "DONE" if "DONE" in raw.upper() else "LOOP"
    default_instructions = {role.name: role.domain_instruction for role in task.specialist_roles}
    return {
        "status": status,
        "specialist_instructions": default_instructions,
        "refinement_focus": "[coordinator JSON parse failed — using domain defaults]",
        "quality_assessment": "",
    }


def _hrm_specialist_prompt(
    role,
    task: Task,
    instruction: str,
    org_memory: dict,
    prior_output: str,
    loop: int,
) -> str:
    """
    Build the f_L (low-level specialist) prompt for HRM.
    Incorporates coordinator's specific instruction + prior loop output for refinement.
    """
    lessons = ""
    if org_memory:
        key = role.memory_query
        lesson_text = org_memory.get(key, "")
        if lesson_text:
            lessons = f"\n\nLESSONS FROM PREVIOUS BENCHMARK RUNS:\n{lesson_text}\nApply these.\n"

    prior = ""
    if prior_output:
        prior = (
            f"\n\nYOUR PREVIOUS OUTPUT (loop {loop - 1}) — refine this, don't restart:\n"
            f"{prior_output[:2000]}\n"
            "Focus on what the coordinator asked you to improve. Build on what's already good.\n"
        )

    return (
        f"You are the {role.name} specialist in a hierarchical multi-agent system (loop {loop}).\n\n"
        f"TASK CONTEXT:\n{task.prompt[:600]}\n\n"
        f"COORDINATOR INSTRUCTION FOR YOU:\n{instruction}\n"
        f"{prior}"
        f"{lessons}\n"
        "Be extremely specific: use concrete numbers, named protocols, exact formulas, "
        "code-ready logic. This is a DeFi system — vague finance language is not acceptable.\n\n"
        "Output a comprehensive JSON response:\n"
        '{"role": "' + role.name + '", "analysis": "...", "recommendations": [...], '
        '"technical_specs": "...", "implementation_notes": "..."}'
    )


def _hrm_synthesis_prompt(
    task: Task,
    coordinator_plans: list[dict],
    all_specialist_outputs: list[dict],
    org_memory: dict,
) -> str:
    """
    Build the final synthesis prompt for HRM, including full loop history context.
    """
    lessons = ""
    if org_memory:
        synth_lessons = org_memory.get("synthesis_protocol", "")
        if synth_lessons:
            lessons = f"\n\nSYNTHESIS LESSONS FROM PREVIOUS RUNS:\n{synth_lessons}\n"

    # Group outputs by loop
    by_loop: dict[int, list] = {}
    for out in all_specialist_outputs:
        lp = out.get("loop", 1)
        by_loop.setdefault(lp, []).append(out)

    history = ""
    for lp in sorted(by_loop.keys()):
        plan_entry = next((p for p in coordinator_plans if p["loop"] == lp), {})
        coord_assessment = plan_entry.get("plan", {}).get("quality_assessment", "")
        coord_focus = plan_entry.get("plan", {}).get("refinement_focus", "")
        history += f"\n\n{'='*40}\nLOOP {lp}"
        if coord_focus:
            history += f" (coordinator focus: {coord_focus})"
        history += f"\n{'='*40}\n"
        for out in by_loop[lp]:
            history += f"\n--- {out['role']} ---\n{out.get('output', '')[:600]}\n"

    # Use final loop outputs as primary content
    final_loop = max(by_loop.keys()) if by_loop else 1
    final_outputs = by_loop.get(final_loop, [])
    final_text = "\n\n".join(
        f"=== {o['role']} (final) ===\n{o.get('output', '')}"
        for o in final_outputs
    )

    total_loops = len(coordinator_plans)
    final_coord_assessment = ""
    if coordinator_plans:
        last_plan = coordinator_plans[-1].get("plan", {})
        final_coord_assessment = last_plan.get("quality_assessment", "")

    return (
        "You are the MachineMachine Synthesis Agent.\n\n"
        f"Integrate {len(final_outputs)} specialist outputs into ONE unified response for:\n\n"
        f"TASK:\n{task.prompt}\n\n"
        f"This HRM ran {total_loops} coordinator loop(s). Final coordinator assessment: "
        f"{final_coord_assessment or 'see history below'}\n\n"
        "SYNTHESIS RULES:\n"
        "• Preserve ALL technical specifics (numbers, formulas, protocol names, token addresses)\n"
        "• Do NOT replace concrete specs with abstract descriptions\n"
        "• Resolve conflicts by noting both options with tradeoffs\n"
        "• Structure output with clear sections for each required area\n"
        f"{lessons}\n"
        f"FINAL SPECIALIST OUTPUTS:\n{'='*50}\n{final_text[:5000]}\n{'='*50}\n\n"
        f"FULL LOOP HISTORY (for context on refinements):\n{history[:2000]}\n\n"
        "Produce a single, technically detailed, fully integrated response. "
        "Include ALL concrete specs. This is the deliverable that gets evaluated."
    )


def run_hrm(task: Task, org_memory: dict = None, max_loops: int = 3) -> TopologyResult:
    """
    Hierarchical Reasoning Model (HRM) topology.

    Implements two recurrent modules inspired by arxiv:2506.21734:
      f_H (high-level coordinator): slow, abstract, strategic planning — decides what work
                                     needs to happen and whether to loop again
      f_L (low-level specialists):  fast, detailed, domain-specific execution — produce
                                     the actual technical content

    Recurrence is the key differentiator vs single-pass orgs: the coordinator can
    identify gaps and route targeted refinement instructions back to specialists.

    Args:
        task:       Task definition including specialist roles and prompt
        org_memory: Org memory dict from prior benchmark iterations (lessons/patches)
        max_loops:  Maximum f_H/f_L iterations (default 3; set via --max-loops CLI arg)

    Returns:
        TopologyResult with full loop history in metadata
    """
    token_tracker.reset()
    coordinator_plans: list[dict] = []
    all_specialist_outputs: list[dict] = []
    current_specialist_outputs: dict[str, str] = {}  # role_name → latest output text
    total_time: float = 0.0
    loop_parallel_times: list[float] = []

    for loop in range(1, max_loops + 1):
        # ── 1. HIGH-LEVEL COORDINATOR (f_H) ─────────────────────────────────
        coord_prompt = _hrm_coordinator_prompt(
            task, loop, max_loops, current_specialist_outputs, org_memory or {}
        )
        coord_raw, coord_time = cerebras_call(coord_prompt, max_tokens=1000)
        total_time += coord_time

        plan = _parse_coordinator_plan(coord_raw, task)
        coordinator_plans.append({
            "loop": loop,
            "plan": plan,
            "raw": coord_raw,
            "time": coord_time,
        })

        # Exit early if coordinator says DONE (only valid after loop 1)
        if plan.get("status") == "DONE" and loop > 1:
            break

        # ── 2. LOW-LEVEL SPECIALISTS (f_L) — conceptually parallel ───────────
        specialist_instructions: dict = plan.get("specialist_instructions", {})
        loop_outputs: list[dict] = []
        loop_times: list[float] = []

        for role in task.specialist_roles:
            # Use coordinator's specific instruction, fall back to role's domain instruction
            instruction = specialist_instructions.get(role.name) or role.domain_instruction
            prior_output = current_specialist_outputs.get(role.name)

            sp_prompt = _hrm_specialist_prompt(
                role, task, instruction, org_memory or {}, prior_output, loop
            )
            output, elapsed = cerebras_call(sp_prompt, max_tokens=2500)

            entry = {
                "loop": loop,
                "role": role.name,
                "output": output,
                "instruction": instruction,
                "time": elapsed,
            }
            loop_outputs.append(entry)
            loop_times.append(elapsed)
            current_specialist_outputs[role.name] = output

        all_specialist_outputs.extend(loop_outputs)
        total_time += sum(loop_times)
        if loop_times:
            loop_parallel_times.append(max(loop_times))

    # ── 3. SYNTHESIS (same semantics as star, but with full history context) ──
    synth_prompt = _hrm_synthesis_prompt(
        task, coordinator_plans, all_specialist_outputs, org_memory or {}
    )
    final_output, synth_time = cerebras_call(synth_prompt, max_tokens=4000)
    total_time += synth_time

    # parallel_time = sum of per-loop max specialist times + coordinator times + synth
    coord_total_time = sum(p["time"] for p in coordinator_plans)
    parallel_time = sum(loop_parallel_times) + coord_total_time + synth_time

    return TopologyResult(
        topology="hrm",
        final_output=final_output,
        specialist_outputs=all_specialist_outputs,
        total_time=total_time,
        parallel_time=parallel_time,
        metadata={
            "loop_count": len(coordinator_plans),
            "coordinator_plans": [
                {
                    "loop": p["loop"],
                    "status": p["plan"].get("status"),
                    "refinement_focus": p["plan"].get("refinement_focus", ""),
                    "quality_assessment": p["plan"].get("quality_assessment", ""),
                    "time": p["time"],
                }
                for p in coordinator_plans
            ],
            "max_loops_configured": max_loops,
        },
        token_summary=token_tracker.summary(),
    )


def run_self_decompose(task: Task, org_memory: dict = None) -> TopologyResult:
    """Self-decomposing org — no pre-defined specialist roles.

    The org receives the task and must:
    1. Decide what specialist roles are needed
    2. Define each role's focus area
    3. Execute each role
    4. Synthesize

    Tests organizational intelligence, not just assembly.
    """
    token_tracker.reset()

    # Step 1: Decomposition call
    decomp_prompt = (
        f"You are an AI organization that must solve this task:\n\n{task.prompt}\n\n"
        "First, decide what specialist roles are needed. Output EXACTLY this JSON format:\n"
        '{"roles": [{"name": "Role Name", "focus": "What this specialist should analyze"}]}\n\n'
        "Choose 3-5 roles. Each role should cover a distinct domain. "
        "Do not overlap responsibilities. Be specific about each role's focus."
    )
    decomp_raw, decomp_time = cerebras_call(decomp_prompt, max_tokens=800)

    # Parse roles from decomposition
    try:
        json_match = re.search(r'\{.*\}', decomp_raw, re.DOTALL)
        roles_data = json.loads(json_match.group()) if json_match else {"roles": []}
    except (json.JSONDecodeError, AttributeError):
        roles_data = {"roles": [
            {"name": "Analyst 1", "focus": "Primary analysis"},
            {"name": "Analyst 2", "focus": "Secondary analysis"},
            {"name": "Analyst 3", "focus": "Quality review"},
        ]}

    # Step 2: Execute each self-defined role
    specialist_outputs = []
    specialist_times = []

    for role_def in roles_data.get("roles", [])[:5]:  # cap at 5
        sp_prompt = (
            f"You are the {role_def['name']} specialist. Your focus: {role_def['focus']}\n\n"
            f"Task: {task.prompt}\n\n"
            "Be extremely specific with technical details. Use concrete engineering specs."
        )
        output, elapsed = cerebras_call(sp_prompt, max_tokens=2500)
        specialist_outputs.append({
            "role": role_def["name"],
            "focus": role_def["focus"],
            "output": output,
            "time": elapsed,
        })
        specialist_times.append(elapsed)

    # Step 3: Synthesis
    specialists_text = "\n\n".join(
        f"=== {s['role']} ({s['focus']}) ===\n{s['output']}"
        for s in specialist_outputs
    )
    synth_prompt = (
        f"Integrate these specialist outputs into ONE unified response:\n\n"
        f"Task: {task.prompt}\n\n{specialists_text}\n\n"
        "Preserve ALL technical specifics. Structure clearly."
    )
    final_output, synth_time = cerebras_call(synth_prompt, max_tokens=4000)

    total_time = decomp_time + sum(specialist_times) + synth_time

    return TopologyResult(
        topology="self_decompose",
        final_output=final_output,
        specialist_outputs=[{"decomposition": roles_data}] + specialist_outputs,
        total_time=total_time,
        parallel_time=decomp_time + (max(specialist_times) if specialist_times else 0) + synth_time,
        token_summary=token_tracker.summary(),
    )


TOPOLOGY_RUNNERS = {
    "star": run_star,
    "pipeline": run_pipeline,
    "peer_review": run_peer_review,
    "hrm": run_hrm,
    "self_decompose": run_self_decompose,
}
