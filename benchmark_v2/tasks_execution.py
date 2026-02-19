"""
BenchmarkSuite v2 — Execution Tasks

Unlike design tasks that ask "design a system", execution tasks give the org
real inputs to process. This tests operational capability, not planning.
"""
from pathlib import Path
from benchmark_v2.tasks import SpecialistRole, Task

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "code_diffs"

CODE_REVIEW_EXECUTION_RUBRIC = [
    ("bug_detection",       "Correctly identifies all planted bugs (SQL injection, race condition, error handling, N+1)"),
    ("false_positive_rate", "Does NOT flag clean code as buggy (diff_005 should pass)"),
    ("fix_quality",         "Suggested fixes are correct, specific, and immediately applicable"),
    ("severity_accuracy",   "Correctly ranks severity (SQL injection > race condition > N+1 > error handling)"),
    ("review_completeness", "Every diff gets a clear verdict: APPROVE, REQUEST_CHANGES, or BLOCK"),
]


def _load_diffs() -> str:
    """Load all fixture diffs into a single prompt block."""
    diffs = []
    for f in sorted(FIXTURES_DIR.glob("diff_*.py")):
        diffs.append(f"### {f.name}\n```python\n{f.read_text()}\n```")
    return "\n\n".join(diffs)


CODE_REVIEW_GROUNDING = (
    "You are a senior engineer performing actual code review on real pull requests. "
    "This is NOT a design exercise — you are reviewing actual code diffs. "
    "For each diff: identify specific issues (cite exact line), explain the risk, "
    "provide a concrete fix, assign severity (CRITICAL/HIGH/MEDIUM/LOW), "
    "and give a verdict (APPROVE/REQUEST_CHANGES/BLOCK)."
)

code_review_execution = Task(
    id="code_review_execution",
    name="Production Code Review — Execute on Real Diffs",
    prompt=(
        "You are reviewing 5 pull requests for a production Python web service. "
        "For EACH diff, provide:\n"
        "1. **Issues found** — specific bugs, vulnerabilities, or quality problems (cite exact lines)\n"
        "2. **Severity** — CRITICAL / HIGH / MEDIUM / LOW for each issue\n"
        "3. **Suggested fix** — exact code change (not vague advice)\n"
        "4. **Verdict** — APPROVE, REQUEST_CHANGES, or BLOCK (with justification)\n\n"
        "Here are the 5 diffs:\n\n"
        + _load_diffs()
    ),
    specialist_roles=[
        SpecialistRole(
            name="Security Reviewer",
            memory_query="SQL injection SSRF input validation security vulnerability",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: security vulnerabilities. Look for: SQL injection, "
                "command injection, SSRF, path traversal, auth bypass, secrets in code, "
                "unsafe deserialization. For each finding, cite the CWE number."
            ),
        ),
        SpecialistRole(
            name="Concurrency Reviewer",
            memory_query="race condition thread safety lock deadlock shared state",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: concurrency and thread safety. Look for: shared mutable state "
                "without synchronization, TOCTOU bugs, missing locks, potential deadlocks, "
                "non-atomic operations that should be atomic."
            ),
        ),
        SpecialistRole(
            name="Performance Reviewer",
            memory_query="N+1 query optimization batch SQL performance profiling",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: performance issues. Look for: N+1 query patterns, "
                "missing indexes, unbounded loops over DB results, missing pagination, "
                "inefficient algorithms, unnecessary memory allocation."
            ),
        ),
        SpecialistRole(
            name="Reliability Reviewer",
            memory_query="error handling retry resilience exception bare except timeout",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: error handling and reliability. Look for: bare except clauses, "
                "swallowed exceptions, missing retry logic, no timeout handling, "
                "silent failures, inadequate logging, missing cleanup (finally blocks)."
            ),
        ),
        SpecialistRole(
            name="Code Quality Reviewer",
            memory_query="code style type hints documentation clean code readability",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: code quality and maintainability. Look for: missing type hints, "
                "unclear naming, missing docstrings, code duplication, overly complex logic, "
                "violated SOLID principles. Also: identify well-written code and note it."
            ),
        ),
    ],
    rubric=CODE_REVIEW_EXECUTION_RUBRIC,
)

# Ground truth for scoring (used by puzzle_scorer)
GROUND_TRUTH = {
    "diff_001_sql_injection.py": {
        "issues": ["SQL injection via f-string (2 instances)"],
        "severity": "CRITICAL",
        "verdict": "BLOCK",
    },
    "diff_002_race_condition.py": {
        "issues": ["Thread-unsafe global dict without lock", "Non-atomic read-modify-write"],
        "severity": "HIGH",
        "verdict": "REQUEST_CHANGES",
    },
    "diff_003_error_handling.py": {
        "issues": ["Bare except clauses (2 instances)", "Swallowed exceptions hide failures", "No logging"],
        "severity": "MEDIUM",
        "verdict": "REQUEST_CHANGES",
    },
    "diff_004_n_plus_one.py": {
        "issues": ["N+1 query: SELECT per order in loop", "Should use JOIN or IN clause"],
        "severity": "MEDIUM",
        "verdict": "REQUEST_CHANGES",
    },
    "diff_005_clean.py": {
        "issues": [],
        "severity": "NONE",
        "verdict": "APPROVE",
    },
}

EXECUTION_TASKS = [code_review_execution]
EXECUTION_TASK_MAP = {t.id: t for t in EXECUTION_TASKS}
