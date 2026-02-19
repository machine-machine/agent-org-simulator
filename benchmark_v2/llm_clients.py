"""
BenchmarkSuite v2 — LLM Client Helpers
Cerebras (generators) + Anthropic claude-haiku (blind evaluator).
"""
import httpx, os, time

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
    return content, time.time() - t0


# ── Anthropic Haiku (blind evaluator) ────────────────────────────────────────

def load_anthropic_key() -> str:
    cfg_path = os.path.expanduser("~/.config/anthropic/config")
    if os.path.exists(cfg_path):
        for line in open(cfg_path).read().splitlines():
            if "ANTHROPIC_API_KEY" in line and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    raise ValueError("Anthropic API key not found in ~/.config/anthropic/config or ANTHROPIC_API_KEY env")

_ANTHROPIC_KEY = None

def anthropic_call(prompt: str, max_tokens: int = 1000, system: str = "") -> tuple[str, float]:
    global _ANTHROPIC_KEY
    if _ANTHROPIC_KEY is None:
        _ANTHROPIC_KEY = load_anthropic_key()
    t0 = time.time()
    body = {
        "model": "claude-haiku-4-5",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": _ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=body,
        timeout=60,
    )
    data = resp.json()
    content = data["content"][0]["text"] if data.get("content") else ""
    return content, time.time() - t0
