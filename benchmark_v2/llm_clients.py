"""
BenchmarkSuite v2 — LLM Client Helpers
Cerebras (generators) + Anthropic claude-haiku (blind evaluator).
"""
import httpx, os, time, threading


# ── Token / Cost Tracking ─────────────────────────────────────────────────────

class TokenTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0

    def record(self, input_tokens: int, output_tokens: int):
        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.call_count += 1

    def reset(self):
        with self._lock:
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.call_count = 0

    def summary(self) -> dict:
        with self._lock:
            input_cost = self.total_input_tokens * 0.60 / 1_000_000
            output_cost = self.total_output_tokens * 2.40 / 1_000_000
            return {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "call_count": self.call_count,
                "cost_usd": round(input_cost + output_cost, 4),
            }


token_tracker = TokenTracker()

# ── Cerebras ─────────────────────────────────────────────────────────────────

def load_cerebras_key() -> str:
    cfg_path = os.path.expanduser("~/.config/cerebras/config")
    if os.path.exists(cfg_path):
        for line in open(cfg_path).read().splitlines():
            if line.startswith("CEREBRAS_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("CEREBRAS_API_KEY", "")
    if key:
        return key
    raise ValueError("Cerebras API key not found in ~/.config/cerebras/config or CEREBRAS_API_KEY env")

_CEREBRAS_KEY = None

def cerebras_call(prompt: str, max_tokens: int = 2000) -> tuple[str, float]:
    global _CEREBRAS_KEY
    if _CEREBRAS_KEY is None:
        _CEREBRAS_KEY = load_cerebras_key()
    t0 = time.time()
    resp = httpx.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {_CEREBRAS_KEY}", "Content-Type": "application/json"},
        json={"model": "zai-glm-4.7", "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
        timeout=90,
    )
    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content") or msg.get("reasoning") or ""
    # Track token usage for cost accounting
    usage = data.get("usage", {})
    token_tracker.record(
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
    )
    return content, time.time() - t0


# ── Cerebras Evaluator (blind evaluator — different model family from generators) ─────────────
# Generators use zai-glm-4.7. Evaluator uses qwen-3-235b to eliminate model-family bias.

EVALUATOR_MODEL = "qwen-3-235b-a22b-instruct-2507"

def anthropic_call(prompt: str, max_tokens: int = 1200, system: str = "") -> tuple[str, float]:
    """Evaluator call — uses Cerebras qwen-3-235b (different family from GLM-4.7 generators).
    Named anthropic_call for backward compatibility with evaluator.py."""
    t0 = time.time()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    resp = httpx.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {_CEREBRAS_KEY or load_cerebras_key()}", "Content-Type": "application/json"},
        json={
            "model": EVALUATOR_MODEL,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,  # low temp for consistent scoring
        },
        timeout=120,
    )
    data = resp.json()
    if "choices" not in data:
        # Log the error for debugging
        import sys
        print(f"  [Evaluator ERROR] {data.get('error', data)}", file=sys.stderr)
        return "", time.time() - t0
    content = data["choices"][0]["message"].get("content", "")
    return content, time.time() - t0
