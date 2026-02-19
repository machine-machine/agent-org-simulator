# Org Evolution Puzzle Specification

> **What this document covers:** Why certain benchmark tasks create better evolutionary
> pressure for multi-agent orgs, how the DeFi strategy design task was designed as an
> "org evolution puzzle," how the Hierarchical Reasoning Model (HRM) topology maps to
> published theory, and the full benchmark matrix for comparative studies.

---

## 1. What Makes a Good Org Evolution Puzzle?

A benchmark task is an *org evolution puzzle* when it satisfies three properties simultaneously:

### 1.1 Verifiable Constraint Satisfaction
Some dimensions of quality must be **binary and checkable**, not just impressionistic.
If every evaluation dimension is a matter of opinion ("was this technically deep enough?"),
the signal is noisy and cannot reliably discriminate between org designs. Good puzzles
have hard constraints that either are or aren't met — a circuit breaker either fires at
20% drawdown or it doesn't.

*Why this matters for evolution:* The org's protocol can be amended based on failure modes.
If constraint C7 (emergency exit) is consistently missing, the retrospective agent can
add a targeted instruction. Verifiable constraints give the amendment system a clear target.

### 1.2 Multi-Dimensional, Non-Collapsible Quality
A single dimension can be gamed. The task must require genuine **specialist depth** across
multiple independent axes that cannot all be maximised by a single generalist agent.
A DeFi strategy needs both:
- exact mathematical signal formulas (Quant Strategist domain), AND
- specific protocol mechanics like CLMM tick ranges (Protocol Analyst domain), AND
- on-chain tx routing and MEV defence (Execution Engineer domain)

These domains are sufficiently distant that a single-agent response must either be
shallow across all three or deep in one while ignoring the others. Multi-agent orgs
with genuine specialisation have structural advantage.

### 1.3 No Canonical Answer, But Some Clearly Better
The puzzle must not have a lookup-table solution (then a retrieval agent wins trivially),
but it also cannot be purely creative (then scoring is impossible). Good puzzles sit in
the zone where:
- Domain knowledge is required (not general reasoning alone)
- Multiple valid strategies exist (no single right answer)
- Quality differences are observable and rankable (e.g. strategy A has backtestable
  entry signals, strategy B does not)

---

## 2. Why DeFi Strategy Design Fits

The `defi_strategy_design` task was selected as the inaugural puzzle task because it
satisfies all three criteria exceptionally well.

### 2.1 Stakes Are Real
DeFi strategies have measurable outcomes — €50,000 of actual capital, concrete weekly
yield targets, real drawdown events. Unlike software architecture (which is evaluated
on logical consistency) or GTM planning (which is evaluated on plausibility), a DeFi
strategy either earns 5%/week or it doesn't. The concreteness forces precision.

### 2.2 Constraints Are Binary
All 10 hard constraints are binary (see `puzzle_scorer.py`). Either the output:
- specifies a €50,000 capital figure ✓/✗
- defines an exact 20% drawdown halt trigger ✓/✗
- names specific token pairs ✓/✗

There is no partial credit ambiguity. This gives the learning loop a clean error signal.

### 2.3 Domain Requires Genuine Specialist Depth
The five specialist roles are not interchangeable:

| Specialist | Domain | Why a Generalist Fails |
|---|---|---|
| Quant Strategist | Signal design, backtestable rules | Requires on-chain data intuition + stat thinking |
| Risk Manager | Circuit breakers, IL, correlation | Needs DeFi-specific risk topology (IL ≠ equity drawdown) |
| Execution Engineer | TX routing, MEV, gas | Solana program architecture differs from EVM |
| Protocol Analyst | Raydium/Jupiter/Meteora mechanics | Pool-specific knowledge (CLMM tick ranges, fee tiers) |
| Compliance & Ops | Runbook, alerting, emergency exit | Ops knowledge orthogonal to quant/execution |

A single-agent baseline will consistently lack depth in 2-3 of these. The benchmark
should show a clear multi-agent advantage specifically because of genuine specialisation.

### 2.4 Domain Grounding Is Testable
The task includes a **domain grounding instruction** in every specialist prompt:
"Focus on on-chain mechanics: liquidity pools, AMMs, MEV, sandwich attacks, impermanent
loss, slippage." This creates a measurable variable: orgs with strong domain grounding
produce outputs with more Solana-specific content, which scores higher on both
constraint satisfaction and quality dimensions.

---

## 3. HRM Architecture: Mapping to f_H/f_L

The HRM topology (`run_hrm` in `topologies.py`) is inspired by the Hierarchical Reasoning
Model paper (arxiv:2506.21734), which proposes two recurrent modules operating at different
temporal and abstraction scales.

### 3.1 Paper's Architecture vs Our Implementation

| Concept (Paper) | Our Implementation | Notes |
|---|---|---|
| `f_H` — high-level module | `_hrm_coordinator_prompt` | Sees full task + all specialist outputs |
| `f_L` — low-level module | `_hrm_specialist_prompt` | Sees coordinator instruction + own prior output |
| Recurrent state `h_H` | `coordinator_plans[]` list | Coordinator's plan history |
| Recurrent state `h_L` | `current_specialist_outputs` dict | Each specialist's latest output |
| "Slow" processing | Coordinator: 1000-token budget | Strategic overview, gap analysis |
| "Fast" processing | Specialists: 2500-token budget | Dense technical content |
| Termination signal | `{"status": "DONE"}` JSON field | Coordinator decides when to stop |

### 3.2 What Recurrence Adds vs Single-Pass Orgs

The key difference from `star` and `pipeline`:

**Star topology:** Specialists run once in parallel, with no ability to refine based on
gaps identified after the fact. If the Quant Strategist forgets specific entry thresholds,
that gap persists into synthesis.

**Pipeline topology:** Specialists run in sequence, but there is no high-level coordinator
assessing the overall state. Each specialist only sees the previous specialist's output,
not a strategic evaluation of what's missing globally.

**HRM topology:** The coordinator (f_H) explicitly evaluates "what is MISSING or too vague"
after each loop and issues targeted refinement instructions. Example:

> Loop 1: Coordinator sees Quant Strategist output lacks RSI thresholds and exact lookback
> periods. Issues instruction: "Add exact RSI threshold (e.g. <28) and 14-period lookback
> for the mean-reversion signal."
>
> Loop 2: Quant Strategist refines with the specific values. Coordinator assesses overall
> completeness → DONE.

This targeted recurrence is precisely what the paper claims as the key advantage of
hierarchical over flat architectures.

### 3.3 Loop Count as a Variable

`max_loops` (default 3, configurable via `--max-loops`) is a first-class benchmark variable.
Hypotheses to test:
- Does quality increase monotonically with loop count, or does it plateau?
- Is loop 2 or loop 3 where the biggest quality jump occurs?
- Does HRM with 1 loop approximate the star topology (coordinator adds overhead but no refinement)?

Setting `--max-loops 1` collapses HRM to approximately star topology (coordinator + parallel
specialists + synthesis, but no refinement loop). This is a useful control condition.

---

## 4. Evolution Mechanism: Org Amendment + HRM Loop Count

The learning loop in `learning_loop.py` implements Algorithm 1 — iterative org improvement
via retrospective analysis. With HRM, two distinct evolution mechanisms are now available:

### 4.1 Protocol Amendment (from `evolving_org/`)
After each benchmark run, the retrospective agent identifies failure modes and updates
`org_memory` with targeted lessons. These lessons propagate into specialist prompts
in the next iteration. This is the **prompt-level** evolution.

Example evolution path:
- Iter 1: Missing gas accounting → retrospective adds "always include Solana priority fee
  budget in PnL math" to org_memory under key `on-chain execution gas optimization`
- Iter 2: Specialist prompt now includes this lesson → output improves

### 4.2 Architecture-Level Variable: Loop Count
`max_loops` can itself be evolved. An outer meta-optimization loop could:
1. Run `max_loops=1, 2, 3` and observe quality curves
2. Select the `max_loops` value that maximises quality delta over single-agent baseline
3. Fix `max_loops` for subsequent production runs

This represents **architecture-level** evolution — the org not just improving its prompts
but choosing its own reasoning depth.

### 4.3 Combined Evolution
The most powerful setup combines both:
1. Protocol amendments (what the specialists are told)
2. HRM loop count selection (how many refinement passes)
3. Topology selection (is HRM actually better than peer_review for this task?)

---

## 5. Benchmark Matrix

The full benchmark experiment space:

### 5.1 Primary Variables

| Variable | Options | Notes |
|---|---|---|
| Task | `ai_incident_response`, `software_architecture`, `strategic_planning`, `defi_strategy_design` | Task difficulty increases left→right |
| Topology | `star`, `pipeline`, `peer_review`, `hrm` | Org complexity increases left→right |
| Domain grounding | On (default), Off (ablation) | Remove DEFI_GROUNDING from specialist prompts |
| Loop count | 1, 2, 3 (HRM only) | Recurrence depth |
| Iterations | 1–5 | Learning loop iterations |

### 5.2 Key Experiments

**Experiment A: Topology Comparison on DeFi Task**
```
python run_suite.py --tasks defi_strategy_design \
  --topologies star pipeline peer_review hrm \
  --iterations 3
```
*Question:* Does HRM outperform flat topologies on a puzzle task?

**Experiment B: HRM Loop Count Ablation**
```
python run_suite.py --tasks defi_strategy_design \
  --topologies hrm --iterations 3 --max-loops 1
python run_suite.py --tasks defi_strategy_design \
  --topologies hrm --iterations 3 --max-loops 2
python run_suite.py --tasks defi_strategy_design \
  --topologies hrm --iterations 3 --max-loops 3
```
*Question:* Where does quality plateau — loop 2 or loop 3?

**Experiment C: Domain Grounding Ablation**
Run `defi_strategy_design` with `DEFI_GROUNDING` stripped from specialist prompts.
*Question:* How much of the quality improvement is specialisation vs domain grounding?

**Experiment D: Cross-Task Generalization**
```
python run_suite.py --tasks all --topologies star hrm --iterations 3
```
*Question:* Does HRM's advantage on DeFi (a puzzle task) transfer to other task types?

### 5.3 Scoring Matrix

For each condition we collect:
- `evaluate_blind` score: relative A/B quality vs single-agent baseline (0-100)
- `score_defi_puzzle` (DeFi task only): absolute constraint satisfaction (0-10) + quality (0-100)
- `TopologyResult.metadata.loop_count`: actual loops used (HRM may exit early)
- Time metrics: `total_time`, `parallel_time`
- Learning curve: delta per iteration across the learning loop

### 5.4 Success Criteria

HRM is considered **validated** for puzzle tasks if:
- Mean constraint satisfaction ≥ 8/10 (vs ≤ 6/10 for star topology)
- Combined puzzle score ≥ 70/100 (vs ≤ 55/100 for single-agent baseline)
- Cohen's d ≥ 0.5 (medium effect size) vs star topology on DeFi task
- Quality improvement plateaus at loop 2-3, not loop 1 (confirming recurrence value)

---

## 6. Adding New Puzzle Tasks

To add a new puzzle task to the benchmark:

1. **Define hard constraints** — binary, observable, domain-specific (aim for 8-12)
2. **Design specialist roles** with non-overlapping domain knowledge
3. **Add domain grounding** — a one-paragraph instruction that anchors specialists in the domain
4. **Write a puzzle scorer** — extend `puzzle_scorer.py` or create a new module
5. **Add to `tasks.py`** — define `Task` with `rubric=CUSTOM_RUBRIC_DIMENSIONS`
6. **Add to `ALL_TASKS`** and `TASK_MAP`

Good puzzle task candidates (for future work):
- **Zero-knowledge proof circuit design** — cryptographic constraints are checkable
- **Kubernetes multi-cluster failover design** — specific SLA/RTO targets are binary
- **Options market maker strategy** — gamma exposure limits, vol surface specifics
- **Distributed consensus protocol** — fault tolerance guarantees are provable

---

*Document version: v1.0 | Created: 2026-02-19 | benchmark_v2/PUZZLE_SPEC.md*
