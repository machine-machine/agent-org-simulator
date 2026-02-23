"""
BenchmarkSuite v2 — Blind Evaluator
Uses Cerebras qwen-3-235b (different model family from GLM-4.7 generators).
Runs n_runs evaluations with shuffled A/B labels to eliminate position bias.
Returns statistical scores: mean, std, p-value, Cohen's d.
"""
import re, random
from dataclasses import dataclass, field
from .tasks import Task, RUBRIC_DIMENSIONS
from .llm_clients import anthropic_call

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class DimensionScore:
    """Dynamic dimension score container. Stores arbitrary rubric dimension scores."""
    scores: dict = field(default_factory=dict)  # {dim_name: int}

    # Legacy fixed fields for backward compat (populated if rubric matches default)
    coverage: int = 0
    technical_depth: int = 0
    coherence: int = 0
    implementability: int = 0
    edge_cases: int = 0

    @property
    def total(self) -> int:
        if self.scores:
            return sum(self.scores.values())
        return self.coverage + self.technical_depth + self.coherence + self.implementability + self.edge_cases


@dataclass
class EvalResult:
    sa_scores: list[int] = field(default_factory=list)
    ma_scores: list[int] = field(default_factory=list)
    sa_dim_scores: list[DimensionScore] = field(default_factory=list)
    ma_dim_scores: list[DimensionScore] = field(default_factory=list)
    sa_mean: float = 0.0
    ma_mean: float = 0.0
    sa_std: float = 0.0
    ma_std: float = 0.0
    delta_mean: float = 0.0
    delta_std: float = 0.0
    p_value: float = 1.0
    cohens_d: float = 0.0
    n_runs: int = 0
    winner: str = "tie"  # "sa" | "ma" | "tie"

    def compute_stats(self):
        import math
        n = len(self.sa_scores)
        self.n_runs = n
        if n == 0:
            return
        self.sa_mean = sum(self.sa_scores) / n
        self.ma_mean = sum(self.ma_scores) / n
        self.delta_mean = self.ma_mean - self.sa_mean

        def std(vals, mean):
            if len(vals) < 2:
                return 0.0
            return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))

        self.sa_std = std(self.sa_scores, self.sa_mean)
        self.ma_std = std(self.ma_scores, self.ma_mean)
        deltas = [m - s for m, s in zip(self.ma_scores, self.sa_scores)]
        delta_mean_check = sum(deltas) / n
        self.delta_std = std(deltas, delta_mean_check)

        # Cohen's d (pooled std)
        pooled_std = math.sqrt((self.sa_std ** 2 + self.ma_std ** 2) / 2) if (self.sa_std or self.ma_std) else 1.0
        self.cohens_d = self.delta_mean / pooled_std if pooled_std else 0.0

        # p-value (t-test if scipy available, else rough approximation)
        if HAS_SCIPY and n >= 2:
            _, self.p_value = scipy_stats.ttest_rel(self.ma_scores, self.sa_scores)
        else:
            self.p_value = 0.5  # placeholder when scipy unavailable

        # Winner
        if self.delta_mean > 3:
            self.winner = "ma"
        elif self.delta_mean < -3:
            self.winner = "sa"
        else:
            self.winner = "tie"


def _build_eval_prompt(output_a: str, output_b: str, task: Task) -> str:
    # Use task-specific rubric if available, fall back to default
    rubric = task.rubric if hasattr(task, 'rubric') and task.rubric else RUBRIC_DIMENSIONS
    dim_names = [dim[0] for dim in rubric]

    rubric_lines = "\n".join(
        f"{i+1}. {dim[0].upper().replace('_',' ')} (0-20 points): {dim[1]}"
        for i, dim in enumerate(rubric)
    )

    # Build expected score block with concrete format (no brackets)
    score_template_a = "\n".join(f"A_{d}: <integer 0-20>" for d in dim_names)
    score_template_b = "\n".join(f"B_{d}: <integer 0-20>" for d in dim_names)

    return f"""You are an expert technical evaluator. Score two AI responses to this task independently.

TASK:
{task.prompt[:800]}

SCORING RUBRIC — rate EACH dimension 0 to 20 (integers only):
{rubric_lines}

Maximum total = {len(rubric) * 20} points.

---
OUTPUT A:
{output_a[:2500]}

---
OUTPUT B:
{output_b[:2500]}

---
INSTRUCTIONS:
1. Evaluate A and B independently against EACH rubric dimension
2. Give concrete reasons for each score (1-2 sentences per dimension)
3. At the very END of your response, output ONLY the score block below — integers, no brackets, no ranges

SCORE BLOCK (copy this exactly and fill integers):
{score_template_a}
A_total: <sum of A scores>
{score_template_b}
B_total: <sum of B scores>"""


def _extract_score(text: str, prefix: str, key: str) -> int:
    """Extract a score value from evaluator text. Handles both '15' and '[15]' formats.
    Uses the LAST match (end of text, after reasoning chain)."""
    # Match: PREFIX_KEY: 15  OR  PREFIX_KEY: [15]  OR  PREFIX_KEY: 15/20
    pattern = rf'{re.escape(prefix)}_{re.escape(key)}:\s*\[?(\d+)\]?'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    if matches:
        try:
            val = int(matches[-1].group(1))
            return max(0, min(100, val))  # clamp to sane range
        except (ValueError, IndexError):
            pass
    return 0


def _parse_scores(text: str, prefix: str, dim_names: list[str] | None = None) -> DimensionScore:
    """Parse dimension scores from evaluator output.
    dim_names: list of dimension keys to extract (task-specific rubric).
    Falls back to default RUBRIC_DIMENSIONS keys if not provided."""
    if dim_names is None:
        dim_names = [d[0] for d in RUBRIC_DIMENSIONS]

    scores = {dim: _extract_score(text, prefix, dim) for dim in dim_names}

    # Create DimensionScore with dynamic scores + legacy fields for default rubric
    ds = DimensionScore(scores=scores)
    # Populate legacy fields if they exist in this rubric
    for field_name in ("coverage", "technical_depth", "coherence", "implementability", "edge_cases"):
        if field_name in scores:
            setattr(ds, field_name, scores[field_name])
    return ds


def evaluate_blind(
    sa_output: str,
    ma_output: str,
    task: Task,
    n_runs: int = 3,
    verbose: bool = True,
) -> EvalResult:
    """
    Blind evaluation: run n_runs times with shuffled A/B labels.
    This eliminates position bias (first-output advantage).
    Uses Cerebras qwen-3-235b — different model family from GLM-4.7 generators.
    """
    result = EvalResult()

    for run_i in range(n_runs):
        # Shuffle which output is A vs B
        if random.random() > 0.5:
            a_output, b_output = sa_output, ma_output
            a_is_sa = True
        else:
            a_output, b_output = ma_output, sa_output
            a_is_sa = False

        prompt = _build_eval_prompt(a_output, b_output, task)

        if verbose:
            print(f"    [Evaluator run {run_i+1}/{n_runs}] {'SA=A, MA=B' if a_is_sa else 'SA=B, MA=A'}...")

        eval_text, elapsed = anthropic_call(prompt, max_tokens=2000)

        rubric = task.rubric if hasattr(task, 'rubric') and task.rubric else RUBRIC_DIMENSIONS
        dim_names = [d[0] for d in rubric]
        a_scores = _parse_scores(eval_text, "A", dim_names)
        b_scores = _parse_scores(eval_text, "B", dim_names)

        if verbose and not any(v > 0 for v in a_scores.scores.values()):
            print(f"    [WARN] All scores parsed as 0 — last 300 chars of response:")
            print(f"    {repr(eval_text[-300:])}")

        if a_is_sa:
            sa_dim, ma_dim = a_scores, b_scores
        else:
            sa_dim, ma_dim = b_scores, a_scores

        sa_total = sa_dim.total
        ma_total = ma_dim.total

        result.sa_scores.append(sa_total)
        result.ma_scores.append(ma_total)
        result.sa_dim_scores.append(sa_dim)
        result.ma_dim_scores.append(ma_dim)

        if verbose:
            delta = ma_total - sa_total
            print(f"    SA={sa_total}  MA={ma_total}  delta={delta:+d}  ({elapsed:.1f}s)")

    result.compute_stats()
    return result


def format_eval_summary(result: EvalResult) -> str:
    sig = ""
    if result.p_value < 0.01:
        sig = "**"
    elif result.p_value < 0.05:
        sig = "*"
    winner_str = {
        "ma": f"MA WINS{sig}",
        "sa": f"SA WINS{sig}",
        "tie": "TIE",
    }[result.winner]
    return (
        f"{winner_str}  SA={result.sa_mean:.1f}±{result.sa_std:.1f}  "
        f"MA={result.ma_mean:.1f}±{result.ma_std:.1f}  "
        f"Δ={result.delta_mean:+.1f}  p={result.p_value:.3f}  d={result.cohens_d:.2f}"
    )
