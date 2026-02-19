"""
Default organizational memory — lessons from Runs 1-6 of incident response benchmark.
Applied to ALL new tasks from day 1 so we don't repeat the failure→recovery arc.
"""

DEFAULT_ORG_MEMORY = {
    # Lesson from Run 1→2: structured handoff prevents abstraction loss
    "synthesis_protocol": (
        "CRITICAL: Specialists must output structured, specific content. "
        "Synthesis must preserve ALL concrete values verbatim — never replace "
        "specific numbers, schemas, or protocol names with abstract metaphors. "
        "If a specialist says 'timeout_ms: 500', synthesis must keep '500', not 'standard timeout'."
    ),

    # Lesson from Run 4: never truncate specialist input
    "synthesis_truncation": (
        "NEVER truncate specialist input for synthesis. A single synthesis call "
        "with full specialist input is better than split calls with truncated input. "
        "If the model hits token limits, retry with higher max_tokens."
    ),

    # Lesson from Run 5→6: domain grounding prevents drift
    "domain_grounding": (
        "All specialist prompts must include explicit domain grounding. "
        "LLMs pattern-match to their training data distribution — if the task "
        "mentions 'incident response', specialists will drift to cybersecurity. "
        "Always specify the actual domain context explicitly."
    ),

    # Lesson from Run 3: phase-locked structure
    "output_structure": (
        "Multi-agent output must follow a consistent phase structure matching "
        "the task's required areas. Each required area must have a dedicated section. "
        "Specialists should output JSON with clearly labeled sections."
    ),
}


def get_default_memory() -> dict:
    """Return default org memory for new task runs."""
    return dict(DEFAULT_ORG_MEMORY)
