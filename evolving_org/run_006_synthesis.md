# Unified Incident Response Protocol — MachineMachine v1.0
**Synthesized by:** Claude Sonnet 4.6 from 6 specialist LLM agent outputs
**Date:** 2026-02-19 | **Run:** 006

## TL;DR
- **Detect:** Three-layer failure detection — UDP heartbeat/Phi Accrual (250ms) catches crashes, gRPC token-stream watchdog (EWMA on TTFT) catches LLM inference hangs, gRPC circuit breaker (50% error/10s) catches cascade failures
- **Alert → Redistribute:** Redis Pub/Sub fanout (5ms) broadcasts failure state; gRPC Two-Phase Commit (150ms) achieves consensus; AMQP OrphanedTaskMigrator (200ms) takes over queue via exclusive rebind with consistent hashing
- **Recover → Learn:** AMQP QoS LoadShedGuard ramps prefetch 5→25→unlimited with 30/60s holds; Redis Streams VectorStreamReplay replays missed events; SemanticMemoryInjection upserts incident patterns into the org's vector store to prevent recurrence

---

## Phase 1: Detect

*Sources: LLM Systems Architect + Single Agent contribution*

### AgentHeartbeat (LLM Systems Architect)
- **Protocol:** UDP
- **Timing:** `250ms` interval
- **Threshold:** `3 missed intervals`
- **Algorithm:** Phi Accrual Failure Detector
- **Message schema:** `{agent_id: UUID, iteration: int64, timestamp_ms: int64, queue_depth: int}`
- **Failure modes:** process termination, network congestion, runtime panic

### ModelLivenessProbe (LLM Systems Architect)
- **Protocol:** HTTP/2
- **Timing:** `5000ms`
- **Threshold:** `latency > 5000ms OR HTTP 503`
- **Algorithm:** Active Polling with Timeout
- **Message schema:** `{endpoint: "/v1/readiness", state: enum[READY,BUSY,ERROR], vram_usage: float}`
- **Failure modes:** OOM, GPU CUDA error, deadlock

### TokenStreamWatchdog (Single Agent — unique contribution)
- **Protocol:** gRPC streaming (HTTP/2)
- **Timing:** `100ms` check frequency on active inference streams
- **Algorithm:** EWMA on Time-To-First-Token (TTFT) — alert if chunk latency exceeds EWMA by `3σ`
- **Message schema:** `{observer_id: str, target_agent: str, stream_id: UUID, stagnation_duration_ms: int, threshold_limit_ms: int, anomaly_type: enum[HANG,LOOP]}`
- **Failure modes:** false positive on deep reasoning (threshold too tight), undetected token loops (tokens generated fast but meaninglessly)

### OrchestrationCircuitBreaker (LLM Systems Architect)
- **Protocol:** gRPC
- **Timing:** `1000ms` window evaluation
- **Threshold:** `50% failure rate in 10s window`
- **Algorithm:** Sliding Window Counter
- **Message schema:** `{requester_id: str, provider_id: str, state: enum[CLOSED,OPEN,HALF_OPEN], consecutive_failures: int}`
- **Failure modes:** cascade failure, upstream latency spike

> **Conflict resolved:** Single agent used UDP 500ms / Phi threshold at EWMA-based. Specialist used UDP 250ms / 3-missed-interval threshold. **Recommend:** 250ms (faster detection) + Phi Accrual (fewer false positives). Both approaches preserved above.

---

## Phase 2: Alert & Communication

*Sources: Orchestration Controller + Incident Response Governor*

### PeerFailureBroadcast (Orchestration Controller)
- **Protocol:** Redis Pub/Sub
- **Timing:** `5ms` post-detection
- **Threshold:** `heartbeat_missed > 3 OR exit_code != 0`
- **Algorithm:** Fanout
- **Message schema:** `{node_id: UUID, last_known_state: str, exit_signal: str, trace_id: str}`
- **Failure modes:** subscriber_lag, memory_pressure

### IncidentConsensus (Orchestration Controller)
- **Protocol:** gRPC
- **Timing:** `150ms`
- **Threshold:** `majority vote (51%)`
- **Algorithm:** Two-Phase Commit
- **Message schema:** `{transaction_id: UUID, coordinator_id: UUID, vote: enum[ACK,NACK], context_checksum: str}`
- **Failure modes:** coordinator_timeout, network_partition

### WorkflowEscalation (Orchestration Controller)
- **Protocol:** AMQP
- **Timing:** `25ms`
- **Threshold:** `consensus=ABORT`
- **Algorithm:** PriorityRouting
- **Message schema:** `{session_id: UUID, frozen_state: bytes, retry_count: int32, target_capability: str}`
- **Failure modes:** queue_saturation, state_serialization_error

### ConsensusBroadcast — Authority Tiers (Incident Response Governor)
- **Protocol:** Redis Pub/Sub
- **Timing:** `75ms`
- **Tiers:**
  - L0: quorum=1, auto=true, sla=`100ms`
  - L1: quorum=majority, auto=true, sla=`1000ms`
  - L2: quorum=unanimous, requires_human=true, sla=`10000ms`
- **Failure modes:** subscription lag, network partition

### RollbackCoordinator (Incident Response Governor)
- **Protocol:** gRPC
- **Algorithm:** Two-Phase Commit
- **Message schema:** `{transaction_id: UUID, target_version: str, participant_nodes: []str, coordinator_decision: str, ts: ISO8601}`
- **Failure modes:** lock timeout, prepare phase failure

> **Note:** Both Coordination Specialist and Governance Designer use Two-Phase Commit for consensus. This is consistent — the governance layer wraps the coordination layer. Execution order: PeerFailureBroadcast (5ms) → IncidentConsensus (150ms) → ConsensusBroadcast/authority check (75ms) → WorkflowEscalation if needed.

---

## Phase 3: Redistribute Work

*Source: Resilience Architect (Emergence Engineer)*

### OrphanedTaskMigrator (Resilience Architect)
- **Protocol:** AMQP
- **Timing:** `200ms`
- **Threshold:** `TCP connection reset / heartbeat timeout`
- **Algorithm:** Exclusive queue rebind (AMQP exclusive consumers)
- **Message schema:** `{task_id: UUID, state_snapshot: bytes, context_headers: map[str]str, offset: int64}`
- **Failure modes:** state deserialization error, duplicate redelivery

### CapacityAwareRebalancer (Resilience Architect)
- **Protocol:** gRPC
- **Timing:** `500ms`
- **Threshold:** `agent_load_variance > 15%`
- **Algorithm:** Work stealing
- **Message schema:** `{target_peer: str, steal_count: int32, vector_clock: int64, ack_deadline: int64}`
- **Failure modes:** thundering herd, chatty synchronization overhead

### FlowControlGate (Resilience Architect)
- **Protocol:** HTTP/2
- **Timing:** `10ms`
- **Threshold:** `pending_requests > max_concurrency`
- **Algorithm:** Adaptive window size
- **Message schema:** `{window_size: int32, current_latency_ms: float, rejected: bool}`
- **Failure modes:** buffer bloat, head-of-line blocking

---

## Phase 4: Recover & Reintegrate

*Source: State Reconciliation Architect (Recovery Specialist)*

### SemanticHealthCheck (State Reconciliation Architect)
- **Protocol:** gRPC Unary
- **Threshold:** `warmup_latency < 50ms AND vocab_load_success`
- **Algorithm:** Embedding Distance Verification (confirms recovered model produces embeddings within acceptable distance from baseline)
- **Failure modes:** OOM on GPU, Model Weight Corruption, Tokenizer Version Drift
- *Note: This is LLM-specific — not just "HTTP 200 OK" but semantic correctness of the model itself*

### LoadShedGuard — Canary Ramp (State Reconciliation Architect)
- **Protocol:** AMQP QoS Prefetch
- **Threshold per stage:** `gpu_util < 85% AND queue_latency < 100ms`
- **Stages:**
  - Stage 1: prefetch_count=`5`, hold=`30s`
  - Stage 2: prefetch_count=`25`, hold=`60s`
  - Stage 3: prefetch_count=`0` (unlimited), hold=`0s`
- **Failure modes:** Context Window Overflow, VRAM Saturation, Inference Timeout Spike

### VectorStreamReplay (State Reconciliation Architect)
- **Protocol:** Redis Streams
- **Timing:** dynamic based on lag
- **Algorithm:** XREADGROUP Idempotency Check (ensures events processed exactly-once during replay)
- **Message schema:** `{stream_key: str, event_id: UUID, vector_delta: []float32, meta_ts: int64}`
- **Failure modes:** Stream Truncation, Checksum Mismatch, Duplicate Entry Collision

---

## Phase 5: Post-Incident Learning

*Source: Model Behavior Synthesizer (Network Analyst)*

### InferenceTraceAggregation (Model Behavior Synthesizer)
- **Protocol:** gRPC
- **Threshold:** `on_task_failure`
- **LLM-specific metrics captured:** `ttft_ms`, `tokens_per_second`, `context_window_utilization`, `tool_execution_latency`, `reasoning_loop_count`, `hallucination_score`
- **Message schema:** `{trace_id: UUID, agent_id: str, prompt_hash: str, termination_reason: str, intermediate_steps: []obj}`
- **Failure modes:** trace_dropping, high_dimensional_clustering_failure

### SemanticMemoryInjection (Model Behavior Synthesizer)
- **Protocol:** AMQP
- **Algorithm:** Vector Embedding & Upsert into vector store
- **Schema:** `{collection: "negative_constraints", vector: float[], payload: {incident_id: UUID, forbidden_pattern: str, mitigation_strategy: str}}`
- **Failure modes:** semantic_collision, index_corruption
- *Key insight: Learned failure patterns are injected back into the org's shared vector memory — future agents query this before taking actions that match failure signatures*

### ReasoningPatternAnomalyDetector (Model Behavior Synthesizer)
- **Threshold:** `drift_score > 0.75`
- **Algorithm:** Isolation Forest on reasoning step sequences
- **Message schema:** `{anomaly_id: UUID, deviation_type: str, confidence: float, affected_model_version: str}`
- **Failure modes:** overfitting to noise, false_positive_suppression

---

## Open Questions

1. **Circuit breaker reset authority:** Who resets an OPEN circuit breaker — auto on HALF_OPEN success, or requires L1 quorum? (Governance Designer: unspecified)
2. **Max reintegration SLA:** If LoadShedGuard stages take >90s total, should the agent be force-restarted instead? (Recovery Specialist: unspecified)
3. **Recurrence auto-action:** If `ReasoningPatternAnomalyDetector` flags drift_score > 0.75 and matches a known failure signature in negative_constraints, should an incident be pre-emptively declared? (Network Analyst: open)
4. **T1 auto-rollback:** Can Tier 1 (majority quorum) auto-approve rollbacks without human token? (Governance Designer: open)

---

## Integration Points Between Phases

1. **Detect → Alert:** `AgentHeartbeat` or `TokenStreamWatchdog` fires → `trace_id` passed to `PeerFailureBroadcast` → `IncidentConsensus` uses the same `trace_id` for audit correlation
2. **Alert → Redistribute:** `IncidentConsensus` returns `CONFIRMED` + `frozen_state` from Context Serialization → `OrphanedTaskMigrator` uses `frozen_state` bytes as the state_snapshot for queue rebind
3. **Redistribute → Recover:** `FlowControlGate` signals stable (`pending_requests < max_concurrency`) → triggers `SemanticHealthCheck` gate; agent not reintegrated until flow is stable
4. **Recover → Learn:** `LoadShedGuard` completes Stage 3 → `InferenceTraceAggregation` collects full trace from the incident + recovery → `SemanticMemoryInjection` upserts failure pattern to shared vector store
5. **Learn → Detect:** `negative_constraints` collection grows → future `AgentHeartbeat` observers and `TokenStreamWatchdog` can query it to tune thresholds; `ReasoningPatternAnomalyDetector` drift threshold tightens over time
