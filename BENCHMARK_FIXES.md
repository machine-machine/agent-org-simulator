# Benchmark Fixes — Elicitation Rounds 1 & 2
*2026-02-19 — Applied pre-mortem + red team analysis*

## Critical Fixes (before Monday cron)

### FIX 1: Add Execution Benchmark (code_review_execution)
**Problem:** All 4 tasks are "design a system" — none process real inputs.
**Fix:** Create `code_review_execution` task that gives the org 5 real Python code diffs and asks it to:
- Identify bugs, security issues, style violations
- Suggest specific fixes
- Approve or request changes
This tests execution, not design. Verifiable: we know the bugs we planted.

### FIX 2: Apply Run 6 Optimizations from Day 1
**Problem:** New tasks would repeat the failure→recovery arc.
**Fix:** All tasks already have domain grounding (done by build agents ✅). Additionally:
- Structured JSON handoff between specialists (add to all topologies)
- Single synthesis call with full specialist output (never truncate)
- Claude Sonnet for synthesis step (not just Cerebras)
These are encoded as default org_memory entries, not learned through failure.

### FIX 3: Track Cost-Per-Quality
**Problem:** Org makes 6+ API calls vs single agent's 1. Enterprise buyers need cost justification.
**Fix:** Add to every run result:
- `total_tokens_consumed` (input + output, all calls)
- `total_cost_usd` (Cerebras pricing: ~$0.60/M input, $2.40/M output)
- `quality_per_dollar` = score / cost
- `wall_time_seconds`
- Report as: "Org scored 97 at $0.08/run vs SA scored 86 at $0.02/run — 12.8% better quality for 4x cost"

### FIX 4: Separate Enterprise vs Finance Tracks
**Problem:** DeFi task in enterprise pitch creates positioning confusion.
**Fix:** Two benchmark tracks:
- **Enterprise Track:** code_review_protocol, code_review_execution, ai_incident_response, support_triage_system, contract_review
- **Finance Track:** defi_strategy_design (+ future: portfolio_rebalancing, risk_report_generation)
Enterprise blog posts only reference Enterprise Track results.

### FIX 5: Self-Decomposition Variant
**Problem:** Pre-defined specialist roles test assembly, not organizational intelligence.
**Fix:** Add `--no-roles` flag to run_suite.py. When set:
- Single agent gets the full task (same as now)
- Multi-agent org gets the task + instruction: "You are an AI organization. Decide what specialist roles are needed, define their responsibilities, then execute each role, then synthesize."
- Coordinator (HRM f_H) must output: role definitions + assignments + instructions
- This tests whether the org can self-organize, not just execute pre-assigned roles.

### FIX 6: Human Validation Gate
**Problem:** AI scoring AI is not credible for enterprise sales.
**Fix:**
- After first successful run of each task, export SA output + MA output (anonymized as "Output A" vs "Output B")
- Send to domain expert for blind review:
  - Code Review → Nasr (ML PhD) + any senior engineer contact
  - Contract Review → find lawyer contact (ask master)
  - IT Ops → already validated by 6 runs + domain expertise
- One human validation per task is enough for blog credibility

### FIX 7: Add Real Input Data
**Problem:** Contract review has no contract; code review has no code.
**Fix for code_review_execution:**
- Create 5 synthetic Python code diffs with planted issues:
  1. SQL injection vulnerability (f-string in query)
  2. Race condition (shared state without lock)
  3. Missing error handling (bare except)
  4. Performance issue (N+1 query in loop)
  5. Clean code (no issues — tests false positive rate)
- Store in benchmark_v2/fixtures/code_diffs/

## Priority Order
1. FIX 3 (cost tracking) — trivial to add, high impact on credibility
2. FIX 1 (execution task) — biggest credibility gap
3. FIX 2 (Run 6 optimizations) — prevents wasted runs
4. FIX 4 (track separation) — prevents positioning confusion
5. FIX 7 (real input data) — needed for execution task
6. FIX 5 (self-decomposition) — adds research novelty
7. FIX 6 (human validation) — needs external people, slower

## Verdict
STRENGTHEN — implement fixes 1-5 before first Monday cron run.
Fix 6-7 can follow in week 2.
