# MachineMachine Real Benchmark Results
**Task:** Incident Response Protocol Design for a 5-Agent AI Organization  
**Model:** Cerebras zai-glm-4.7 — same model for all runs. Architecture is the isolated variable.

---

## Evolution Summary

| Run | Single Agent | Multi-Agent Org | Delta | Fix Applied |
|-----|-------------|-----------------|-------|-------------|
| Run 1 | 90/100 | 73/100 | **−17** | Baseline — free-text synthesis |
| Run 2 | 84/100 | 87/100 | **+3 ✅** | Structured JSON handoff between specialists |
| Run 3 | 85/100 | 87/100 | **+2 ✅** | Phase-locked synthesis (Detect→Alert→Redistribute→Recover→Learn) |

**Multi-agent org has won the last two runs. MA improved from 73 → 87 in two learning cycles.**

---

## Run 3 — Detailed Breakdown

| Dimension | Single Agent | Multi-Agent Org | Winner |
|-----------|-------------|-----------------|--------|
| Coverage | 17/20 | 16/20 | SA |
| Technical Depth | 17/20 | **19/20** | **MA** |
| Coherence | **18/20** | 17/20 | SA |
| Implementability | 17/20 | **18/20** | **MA** |
| Edge Cases | 16/20 | **17/20** | **MA** |
| **TOTAL** | **85/100** | **87/100** | **MA wins (3 of 5 dimensions)** |

**What multi-agent produced that single agent missed (Run 3):**
- ✅ Triple-layer detection at 3 different timescales: UDP heartbeat (200ms) + HTTP/2 health check (1000ms) + gRPC circuit breaker (5000ms)
- ✅ Phi Accrual algorithm (vs simple timeout) — distinguishes transient jitter from real failure
- ✅ AnomalyMulticast schema: `source_agent_id` (UUID), `anomaly_type` (Enum), `timestamp_int64_ms` (Int64), `payload_hash` (String)
- ✅ Multi-step consensus chain with exact timings: 5ms → 50ms → 25ms → 60ms
- ✅ AMQP 1.0 priority queuing with exponential backoff
- ✅ "Zombie" process detection (agent is network-reachable but computationally stuck)
- ✅ Canary reintegration: 10% → 50% → 100% with 60s hold at each stage
- ✅ Raft log replay for state sync on recovery
- ✅ Rollback trigger at error_rate > 2%

---

## Run 2 — What Changed

**Run 1 failure root cause:** Synthesis received ~5,000 words of free prose and compressed by abstracting — replacing `timing_ms: 500` with "standard timeouts" and dropping concrete schema definitions.

**Fix applied:** Specialists output structured JSON (not prose). Synthesizer receives machine-readable input and has explicit "preserve all concrete values verbatim" rules.

**Result:** Technical depth 15 → 19, delta swung from −17 to +3.

---

## What the Org Learns After Each Run

| Run | Protocol Amendment | Effect |
|-----|-------------------|--------|
| Run 1→2 | Mandate structured JSON handoff from specialists | +14 pts on technical depth |
| Run 2→3 | Enforce 5-phase output structure in synthesis | Coherence maintained, MA won again |
| Run 3→4 | Dedicated retry for Phase 3 + Phase 5 (both had thin input) | Expected: coverage 16→18 |

**Every amendment is a git commit on [fleet-governance](https://github.com/machine-machine/fleet-governance).**

---

## Methodology

- Same model (Cerebras zai-glm-4.7) for single agent, all 5 specialists, synthesis, and scoring
- Single agent: 1 API call with full task
- Multi-agent: 5 specialist calls + 1 synthesis = 6 total
- Specialists output structured JSON — synthesis receives machine-readable input
- Parallel execution: wall time ≈ max(specialist times) + synthesis time ≈ 14s vs 5s for single agent
- Weekly cron runs automatically every Sunday 08:00 UTC

**Source:** [github.com/machine-machine/agent-org-simulator/tree/main/evolving_org](https://github.com/machine-machine/agent-org-simulator/tree/main/evolving_org)

---

## Next: Run 4

**Known fix:** Phase 3 (Redistribute Work) and Phase 5 (Post-Incident Learning) were thin because two specialist JSON calls failed and used simplified retries. Next run adds retry logic with explicit short prompts on first attempt.

Expected improvement: Coverage 16 → 18, potentially pushing MA to 90+.
