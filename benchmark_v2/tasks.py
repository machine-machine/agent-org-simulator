"""
BenchmarkSuite v2 — Task Definitions
Three task domains for generalizability testing.
"""
from dataclasses import dataclass, field

RUBRIC_DIMENSIONS = [
    ("coverage",         "Addresses ALL 5 required areas completely"),
    ("technical_depth",  "Specific mechanisms, numbers, schemas, named protocols"),
    ("coherence",        "Logically consistent, well-structured, no contradictions"),
    ("implementability", "A dev team could actually build this from the spec"),
    ("edge_cases",       "Handles failure modes, race conditions, degraded states"),
]

@dataclass
class SpecialistRole:
    name: str
    memory_query: str   # for org memory retrieval
    domain_instruction: str  # specialist-specific focus

@dataclass
class Task:
    id: str
    name: str
    prompt: str
    specialist_roles: list[SpecialistRole]
    rubric: list[tuple[str, str]] = field(default_factory=lambda: RUBRIC_DIMENSIONS)


AI_INCIDENT_RESPONSE = Task(
    id="ai_incident_response",
    name="AI Incident Response Protocol",
    prompt=(
        "Design a complete incident response protocol for a 5-agent AI organization. "
        "Cover all of: (1) failure detection mechanisms, (2) inter-agent communication during incidents, "
        "(3) work redistribution when an agent goes offline, (4) agent recovery and reintegration, "
        "(5) post-incident knowledge capture. Be as comprehensive and technically specific as possible."
    ),
    specialist_roles=[
        SpecialistRole(
            name="Systems Architect",
            memory_query="failure detection heartbeat protocols",
            domain_instruction="technical detection mechanisms for agent failure: heartbeat protocols, timeout thresholds, health check APIs, circuit breaker patterns. Include timing values and protocol specs.",
        ),
        SpecialistRole(
            name="Coordination Specialist",
            memory_query="inter-agent communication incident",
            domain_instruction="inter-agent communication during incidents: message formats, escalation paths, consensus mechanisms. Include message schemas and routing logic.",
        ),
        SpecialistRole(
            name="Governance Designer",
            memory_query="governance decision incident response",
            domain_instruction="decision framework for incident response: authority levels, escalation thresholds, audit requirements, rollback procedures. Include decision trees.",
        ),
        SpecialistRole(
            name="Emergence Engineer",
            memory_query="work redistribution load balancing",
            domain_instruction="work redistribution when capacity drops: algorithms for load balancing, quality preservation under degraded conditions. Use concrete algorithms, not metaphors.",
        ),
        SpecialistRole(
            name="Network Analyst",
            memory_query="post-incident learning knowledge capture",
            domain_instruction="post-incident learning: metrics to capture, org memory updates, pattern detection, preventing recurrence. Include specific data schemas.",
        ),
    ],
)


SOFTWARE_ARCHITECTURE = Task(
    id="software_architecture",
    name="Distributed B2B SaaS Backend",
    prompt=(
        "Design a production-grade distributed backend for a B2B SaaS platform serving 1 million users. "
        "Cover all of: (1) service decomposition and API design, (2) data storage and caching strategy, "
        "(3) async processing and event streaming, (4) deployment and horizontal scaling approach, "
        "(5) observability, alerting, and incident response. Be as technically specific as possible — "
        "include technology choices, data schemas, SLA targets, and concrete implementation details."
    ),
    specialist_roles=[
        SpecialistRole(
            name="Systems Architect",
            memory_query="microservices decomposition API gateway design",
            domain_instruction="service decomposition: domain boundaries, API contracts (REST/gRPC), gateway routing, authentication. Include OpenAPI schema patterns and service mesh choices.",
        ),
        SpecialistRole(
            name="Database Engineer",
            memory_query="database storage caching strategy multi-tenant",
            domain_instruction="data storage strategy: primary DB choice with rationale, read replica topology, caching layers (Redis patterns), multi-tenant isolation, backup/PITR. Include connection pool sizing.",
        ),
        SpecialistRole(
            name="Infrastructure Lead",
            memory_query="kubernetes deployment scaling horizontal auto-scale",
            domain_instruction="deployment and scaling: container orchestration (K8s), HPA/VPA configs, CI/CD pipeline, IaC approach, cost optimization. Include specific resource requests/limits.",
        ),
        SpecialistRole(
            name="API Designer",
            memory_query="event streaming async processing queue",
            domain_instruction="async processing and event streaming: message broker choice (Kafka/SQS/etc), event schemas, consumer group patterns, dead-letter handling, backpressure. Include throughput targets.",
        ),
        SpecialistRole(
            name="Observability Engineer",
            memory_query="monitoring alerting SLO SLA observability",
            domain_instruction="observability stack: metrics (Prometheus/OTEL), distributed tracing, log aggregation, SLO definitions, alert routing, on-call runbooks. Include specific SLA targets.",
        ),
    ],
)


STRATEGIC_PLANNING = Task(
    id="strategic_planning",
    name="Developer-Tools GTM Roadmap",
    prompt=(
        "Design a 90-day go-to-market roadmap for a developer-tools startup with a working prototype "
        "and 3 design partners. Seed funding of $500K just closed. "
        "Cover all of: (1) ICP definition and positioning against alternatives, "
        "(2) developer acquisition channels and content strategy, "
        "(3) activation funnel and onboarding optimization, "
        "(4) early revenue milestones and pricing model, "
        "(5) team structure and resource allocation for the 90 days. "
        "Be specific with metrics, timelines, budgets, and decision criteria."
    ),
    specialist_roles=[
        SpecialistRole(
            name="Market Strategist",
            memory_query="ICP positioning messaging competitive differentiation",
            domain_instruction="ICP definition and positioning: firmographic/psychographic profile, jobs-to-be-done, differentiation from alternatives, messaging hierarchy. Include specific ICP criteria and example companies.",
        ),
        SpecialistRole(
            name="Growth Engineer",
            memory_query="developer acquisition channels content SEO community",
            domain_instruction="developer acquisition: channel prioritization (SEO/content/community/OSS/paid), content calendar, distribution strategy. Include cost-per-acquisition targets and channel ROI estimates.",
        ),
        SpecialistRole(
            name="Product Manager",
            memory_query="activation funnel onboarding time-to-value retention",
            domain_instruction="activation and onboarding: funnel stages, time-to-first-value target, onboarding flow, activation metric definition, A/B test plan. Include specific conversion rate targets.",
        ),
        SpecialistRole(
            name="Revenue Lead",
            memory_query="pricing model revenue milestone freemium PLG",
            domain_instruction="revenue model and milestones: pricing tiers with rationale, freemium/PLG thresholds, monthly revenue targets per month (M1-M3), upsell triggers, expansion revenue strategy.",
        ),
        SpecialistRole(
            name="Ops Planner",
            memory_query="team structure hiring resource allocation budget",
            domain_instruction="team and resource plan: org structure for 90 days, hiring priorities vs contractor, budget allocation across channels/product/ops, decision gates at 30/60/90 days.",
        ),
    ],
)


ALL_TASKS = [AI_INCIDENT_RESPONSE, SOFTWARE_ARCHITECTURE, STRATEGIC_PLANNING]
TASK_MAP = {t.id: t for t in ALL_TASKS}
