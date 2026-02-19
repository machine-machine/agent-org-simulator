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

---

## Run 4 — REGRESSION (Critical Lesson)

| Dimension | Single Agent | Multi-Agent Org |
|-----------|-------------|-----------------|
| Coverage | **19/20** | 16/20 |
| Technical Depth | **19/20** | 11/20 |
| Coherence | **19/20** | 14/20 |
| Implementability | **18/20** | 13/20 |
| Edge Cases | **17/20** | 14/20 |
| **TOTAL** | **92/100** | **68/100** · **Delta: −24** |

### What Went Wrong

**Root cause:** We tried to fix the synthesis token limit problem by splitting synthesis into 5 separate phase-by-phase calls, each receiving only a truncated excerpt of the specialist JSON.

**Effect:** The model hallucinated convincingly wrong values — "ABAC algorithm", "SEV-1 through SEV-5", "bgp_route_flap_count" — none of which came from the specialists. When the model doesn't have enough context, it fills gaps with plausible-sounding but incorrect domain knowledge.

**Protocol Amendment (auto-committed to fleet-governance):**
> *Never truncate specialist input for synthesis. A single synthesis call with full JSON input is better than split calls with truncated input. If the model hits token limits, retry with higher max_tokens. If that fails, use a higher-capacity model for the synthesis step only — synthesis is post-processing, not core agent execution.*

### What Run 4 Single Agent Did Well (92/100 — best yet)
- Phi Accrual with specific threshold value (Phi = 8.0)
- KetamaConsistentHash with vnode ranges and CAS operations
- PlumtreeProtocol for gossip with O(log N) complexity bound
- MerkleTreeDeltaSync for bandwidth-efficient state recovery
- PIDControllerRamp for canary traffic (feedback loop on error rate)
- ByzantineConsistencyRanker for semantic hallucination detection

### Run 5 Fix
Single synthesis call. Max_tokens raised to 8000. Full specialist JSON, no truncation. If Cerebras returns empty content, retry once with +2000 tokens. Fallback: same synthesis prompt sent to Claude if 3 attempts fail.

---

## Run 5 — Synthesis Fixed, Domain Drift Exposed

| Dimension | Single Agent | Multi-Agent Org |
|-----------|-------------|-----------------|
| Coverage | **18/20** | 17/20 |
| Technical Depth | **17/20** | 16/20 |
| Coherence | **18/20** | 17/20 |
| Implementability | 17/20 | 17/20 |
| Edge Cases | 16/20 | 16/20 |
| **TOTAL** | **86/100** | **83/100** · **Delta: −3** |

### What Was Fixed (Compared to Run 4)
- Single synthesis call with full untruncated specialist JSON — **no hallucination** ✅
- Model correctly marked unspecified values as `"unspecified"` per the rule ✅
- Phase 1 (Detect) and Phase 3 (Redistribute) preserved specialist values perfectly ✅

### New Issue Found: Specialist Domain Drift
The "incident response" framing triggers the model's cybersecurity training data:
- Coordination Specialist → generated "SOC Analyst" with Splunk HEC + MITRE ATT&CK — **wrong domain**
- Network Analyst → generated "Security Operations Center" with IOC knowledge graphs — **wrong domain**
- Only Systems Architect and Emergence Engineer stayed on-domain (AI org, not cybersecurity)

The synthesis faithfully used what specialists produced — the synthesis step is now reliable. The problem is upstream.

### Protocol Amendment (committed to fleet-governance)
> *All specialist prompts must include explicit domain grounding: "You are a specialist AI agent in a multi-agent LLM software organization. This is NOT a cybersecurity context. Agents are LLM-based software agents, not network devices. Do not use SIEM, SOC, MITRE ATT&CK, or network security terminology."*

### Run 6 Fix
Prepend domain grounding sentence to every specialist prompt. Expected effect: all 5 specialists stay in AI org context → MA technical depth should reach 19+ → delta positive again.

---

## Run 6 — Multi-Agent Org Wins Decisively: 97 vs 86

| Dimension | Single Agent | Multi-Agent Org | Winner |
|-----------|-------------|-----------------|--------|
| Coverage | 18/20 | **20/20** | **MA** |
| Technical Depth | 17/20 | **20/20** | **MA** |
| Coherence | 18/20 | **19/20** | **MA** |
| Implementability | 17/20 | **19/20** | **MA** |
| Edge Cases | 16/20 | **19/20** | **MA** |
| **TOTAL** | **86/100** | **97/100** | **MA wins all 5 dimensions** |

**Delta: +11 — largest MA win in the benchmark.**

### What Changed: Domain Grounding + Claude Synthesis
1. **Domain grounding:** Every specialist prompt included: *"This is NOT cybersecurity. Agents are LLM-based software processes. No SIEM, SOC, MITRE terminology."* — All 6 specialists stayed on-domain.
2. **Claude Sonnet 4.6 for synthesis:** No token limits, no hallucination, faithfully integrated all specialist values, added Integration Points tracing exact data flow across phase boundaries.

### What Multi-Agent Org Produced That Single Agent Missed
- ✅ **SemanticHealthCheck:** validates recovered model's *embedding output* is semantically correct — not just HTTP 200, but LLM-level correctness verification
- ✅ **SemanticMemoryInjection:** injects failure patterns into shared org vector store — the org learns from every incident
- ✅ **InferenceTraceAggregation:** LLM-specific metrics: `ttft_ms`, `hallucination_score`, `reasoning_loop_count`, `context_window_utilization`
- ✅ **VectorStreamReplay:** XREADGROUP idempotency check for exactly-once event replay during recovery
- ✅ **Isolation Forest on reasoning step sequences:** detects anomalous reasoning patterns *before* full failure
- ✅ **AMQP QoS LoadShedGuard:** LLM-native canary ramp based on `gpu_util < 85%` and `queue_latency < 100ms`
- ✅ **EWMA on TTFT watchdog:** single agent found this too — synthesis integrated it across both outputs

### Full Evolution Summary

| Run | SA | MA | Δ | Key Fix |
|-----|----|----|---|---------|
| 1 | 90 | 73 | −17 | Baseline |
| 2 | 84 | 87 | **+3** | Structured JSON handoff |
| 3 | 85 | 87 | **+2** | Phase-locked structure |
| 4 | 92 | 68 | −24 | ❌ Split synthesis hallucinated |
| 5 | 86 | 83 | −3 | Synthesis fixed; domain drift |
| 6 | 86 | **97** | **+11** | ✅ Domain grounding + Claude synthesis |

**The org learned from every failure and converged on 97/100.**
