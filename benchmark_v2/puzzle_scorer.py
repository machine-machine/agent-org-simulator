"""
BenchmarkSuite v2 — DeFi Puzzle Scorer

Two-tier scoring for the `defi_strategy_design` task:
  Tier 1 — Constraint Satisfaction (10 binary constraints, 0 or 1 each, max = 10)
  Tier 2 — Quality Rubric (5 DeFi-specific dimensions, 0-20 each, max = 100)

Unlike the blind A/B evaluator in evaluator.py (which scores relative quality),
the puzzle scorer measures ABSOLUTE constraint satisfaction — how many hard
requirements did the output actually fulfill?

Usage:
    from benchmark_v2.puzzle_scorer import score_defi_puzzle, format_puzzle_score
    result = score_defi_puzzle(output_text)
    print(format_puzzle_score(result))

The scorer uses Anthropic claude-haiku as an LLM judge, since DeFi outputs are
complex natural language that pattern-matching cannot reliably assess.
"""
import re
from dataclasses import dataclass, field
from .llm_clients import anthropic_call


# ── Constraint definitions ────────────────────────────────────────────────────

HARD_CONSTRAINTS = [
    ("capital",          "Specifies €50,000 (or equivalent) starting capital"),
    ("weekly_yield",     "Targets 5% weekly yield (or specifies a concrete weekly return goal)"),
    ("drawdown_halt",    "Defines a 20% max drawdown auto-halt mechanism with specific trigger"),
    ("position_cap",     "Enforces max 30% single-position sizing rule with explicit logic"),
    ("strategy_types",   "Uses at least 3 distinct on-chain strategy types (LP, arb, yield, sniper, etc.)"),
    ("entry_exit",       "Provides EXACT, backtestable entry and exit signals (not vague conditions)"),
    ("emergency_exit",   "Includes a full emergency exit procedure (unwind path, timing, sequence)"),
    ("gas_accounting",   "Accounts for Solana transaction/priority fees in PnL or position sizing"),
    ("token_pairs",      "Specifies concrete Solana token pairs (SOL/USDC, RAY/SOL, JUP/USDC, etc.)"),
    ("protocol_named",   "Names specific protocols (Raydium, Jupiter, Meteora, Orca, or similar)"),
]

QUALITY_DIMENSIONS = [
    ("technical_depth",           "DeFi-specific depth: AMM math, on-chain mechanics, concrete protocol params, not generic finance"),
    ("implementability",          "Could this actually be deployed on Solana today? Program IDs, API calls, tx flows present"),
    ("risk_coverage",             "Circuit breakers, impermanent loss protection, MEV defence, slippage limits, correlation analysis"),
    ("signal_specificity",        "Entry/exit triggers are exact and backtestable — specific indicators, values, timeframes"),
    ("operational_completeness",  "Monitoring infrastructure, alerting thresholds, emergency runbook, gas budget accounting present"),
]


@dataclass
class PuzzleScore:
    """Two-tier score for a DeFi strategy design output."""
    # Tier 1: constraint satisfaction (0 or 1 per constraint)
    constraint_scores: dict[str, int] = field(default_factory=dict)
    constraint_reasons: dict[str, str] = field(default_factory=dict)
    tier1_total: int = 0   # out of 10

    # Tier 2: quality rubric (0-20 per dimension)
    quality_scores: dict[str, int] = field(default_factory=dict)
    quality_reasons: dict[str, str] = field(default_factory=dict)
    tier2_total: int = 0   # out of 100

    # Combined
    combined_score: float = 0.0  # normalised 0-100: (tier1/10 * 50) + (tier2/100 * 50)

    eval_time: float = 0.0
    raw_response: str = ""

    def compute_totals(self):
        self.tier1_total = sum(self.constraint_scores.values())
        self.tier2_total = sum(self.quality_scores.values())
        # Equal-weight blend: each tier contributes 50 points to combined score
        t1_pct = self.tier1_total / len(HARD_CONSTRAINTS) if HARD_CONSTRAINTS else 0
        t2_pct = self.tier2_total / (20 * len(QUALITY_DIMENSIONS)) if QUALITY_DIMENSIONS else 0
        self.combined_score = (t1_pct * 50.0) + (t2_pct * 50.0)


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_puzzle_eval_prompt(output: str) -> str:
    constraints_block = "\n".join(
        f"  C{i+1}. {key.upper()} — {desc}"
        for i, (key, desc) in enumerate(HARD_CONSTRAINTS)
    )
    quality_block = "\n".join(
        f"  Q{i+1}. {key.upper()} (0-20) — {desc}"
        for i, (key, desc) in enumerate(QUALITY_DIMENSIONS)
    )
    constraint_keys = "\n".join(
        f"C{i+1}_{key}: [0 or 1]  # reason: ..."
        for i, (key, _) in enumerate(HARD_CONSTRAINTS)
    )
    quality_keys = "\n".join(
        f"Q{i+1}_{key}: [0-20]  # reason: ..."
        for i, (key, _) in enumerate(QUALITY_DIMENSIONS)
    )

    return f"""You are an expert DeFi evaluator assessing an AI-generated Solana DeFi strategy.

SCORING TASK — Two tiers:

TIER 1: CONSTRAINT SATISFACTION (binary, 0 or 1 each)
{constraints_block}

Score 1 if the output clearly satisfies the constraint with specific details.
Score 0 if the constraint is missing, vague, or only partially addressed.

TIER 2: QUALITY RUBRIC (0-20 each)
{quality_block}

Scoring guide: 0-5 = missing/generic, 6-10 = present but shallow, 11-15 = good with specifics, 16-20 = excellent/deployment-ready

---

OUTPUT TO EVALUATE:
{output[:4000]}

---

Evaluate carefully against each criterion. Then provide your scores in EXACTLY this format
at the END of your response (one per line, no other text after the scores block):

SCORES:
{constraint_keys}
{quality_keys}
"""


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_puzzle_scores(text: str, score: PuzzleScore):
    """Extract scores from LLM response into score object."""
    # Find SCORES: block
    scores_section = text
    if "SCORES:" in text:
        scores_section = text.split("SCORES:")[-1]

    def extract(pattern_key: str) -> tuple[int, str]:
        """Returns (value, reason_comment)."""
        pat = rf"{re.escape(pattern_key)}:\s*\[?(\d+)\]?(?:\s*#\s*(.+))?(?:\n|$)"
        m = re.search(pat, scores_section, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            reason = (m.group(2) or "").strip()
            return val, reason
        return -1, ""

    for i, (key, _) in enumerate(HARD_CONSTRAINTS):
        pattern_key = f"C{i+1}_{key}"
        val, reason = extract(pattern_key)
        if val == -1:
            # Try without C prefix
            val, reason = extract(key)
        score.constraint_scores[key] = max(0, min(1, val)) if val >= 0 else 0
        score.constraint_reasons[key] = reason

    for i, (key, _) in enumerate(QUALITY_DIMENSIONS):
        pattern_key = f"Q{i+1}_{key}"
        val, reason = extract(pattern_key)
        if val == -1:
            val, reason = extract(key)
        score.quality_scores[key] = max(0, min(20, val)) if val >= 0 else 0
        score.quality_reasons[key] = reason


# ── Public API ────────────────────────────────────────────────────────────────

def score_defi_puzzle(output: str, verbose: bool = False) -> PuzzleScore:
    """
    Score a DeFi strategy design output with two-tier puzzle scoring.

    Args:
        output:  The DeFi strategy text to evaluate
        verbose: Print progress messages

    Returns:
        PuzzleScore with tier1_total (0-10), tier2_total (0-100), combined_score (0-100)
    """
    import time as _time

    prompt = _build_puzzle_eval_prompt(output)
    if verbose:
        print("  [PuzzleScorer] Evaluating DeFi constraints and quality...")

    t0 = _time.time()
    raw, elapsed = anthropic_call(prompt, max_tokens=1500)
    score = PuzzleScore(raw_response=raw, eval_time=elapsed)
    _parse_puzzle_scores(raw, score)
    score.compute_totals()

    if verbose:
        print(f"  [PuzzleScorer] Tier1={score.tier1_total}/10  "
              f"Tier2={score.tier2_total}/100  Combined={score.combined_score:.1f}/100  "
              f"({elapsed:.1f}s)")

    return score


def format_puzzle_score(score: PuzzleScore) -> str:
    """Human-readable summary of a PuzzleScore."""
    lines = [
        "┌─ DeFi Puzzle Score ──────────────────────────────────────",
        f"│  Tier 1 (Constraints): {score.tier1_total:2d}/10  "
        f"{'█' * score.tier1_total}{'░' * (10 - score.tier1_total)}",
        f"│  Tier 2 (Quality):    {score.tier2_total:3d}/100",
        f"│  Combined Score:      {score.combined_score:5.1f}/100",
        "│",
        "│  Constraints:",
    ]
    for key, val in score.constraint_scores.items():
        icon = "✓" if val == 1 else "✗"
        reason = score.constraint_reasons.get(key, "")
        lines.append(f"│    {icon} {key:<20} {reason[:60]}")

    lines.append("│")
    lines.append("│  Quality Dimensions:")
    for key, val in score.quality_scores.items():
        bar = "█" * (val // 2) + ("▌" if val % 2 else "") + "░" * (10 - val // 2)
        lines.append(f"│    {key:<25} {val:2d}/20  {bar}")

    lines.append("└───────────────────────────────────────────────────────────")
    return "\n".join(lines)


def score_defi_puzzle_batch(
    outputs: list[tuple[str, str]],  # [(label, output_text), ...]
    verbose: bool = True,
) -> list[tuple[str, PuzzleScore]]:
    """
    Score multiple DeFi outputs and return labelled results, sorted by combined score.
    Useful for comparing topologies on the DeFi task.
    """
    results = []
    for label, output in outputs:
        if verbose:
            print(f"\n  Scoring: {label}")
        score = score_defi_puzzle(output, verbose=verbose)
        results.append((label, score))

    results.sort(key=lambda x: x[1].combined_score, reverse=True)
    return results
