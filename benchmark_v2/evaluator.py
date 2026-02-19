"""
BenchmarkSuite v2 — Blind Evaluator
Uses Anthropic claude-haiku-4-5 (different model family from Cerebras generators).
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
    coverage: int = 0
    technical_depth: int = 0
    coherence: int = 0
    implementability: int = 0
    edge_cases: int = 0

    @property
    def total(self) -> int:
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
    rubric_lines = "\n".join(
        f"{i+1}. {dim[0].upper().replace('_',' ')} (0-20): {dim[1]}"
        for i, dim in enumerate(RUBRIC_DIMENSIONS)
    )
    return f"""You are an expert technical evaluator. Rate two responses to this task:

TASK: {task.prompt}

RUBRIC (score each 0-20, total 100):
{rubric_lines}

OUTPUT A:
{output_a[:2000]}

OUTPUT B:
{output_b[:2000]}

Evaluate each output independently against the rubric. Think through each dimension carefully.
Then provide your scores in this EXACT format at the END of your response:

A_coverage: [0-20]
A_technical_depth: [0-20]
A_coherence: [0-20]
A_implementability: [0-20]
A_edge_cases: [0-20]
A_total: [0-100]
B_coverage: [0-20]
B_technical_depth: [0-20]
B_coherence: [0-20]
B_implementability: [0-20]
B_edge_cases: [0-20]
B_total: [0-100]"""


def _parse_scores(text: str, prefix: str) -> DimensionScore:
    """Parse KEY: VALUE patterns from evaluator output. Uses LAST match (end of reasoning)."""
    def extract(key):
        pattern = rf'{re.escape(prefix)}_{re.escape(key)}:\s*(\d+)'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if matches:
            try:
                return int(matches[-1].group(1))
            except:
                pass
        return 0

    dims = DimensionScore(
        coverage=extract("coverage"),
        technical_depth=extract("technical_depth"),
        coherence=extract("coherence"),
        implementability=extract("implementability"),
        edge_cases=extract("edge_cases"),
    )
    # If individual dims parsed, compute total; else try to extract total directly
    computed = dims.total
    explicit_total = extract("total")
    if explicit_total and abs(explicit_total - computed) > 10:
        # Something weird — trust the sum of dimensions if they add up
        pass
    return dims


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
    Uses claude-haiku-4-5 — different model family from Cerebras generators.
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

        eval_text, elapsed = anthropic_call(prompt, max_tokens=1200)

        a_scores = _parse_scores(eval_text, "A")
        b_scores = _parse_scores(eval_text, "B")

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
