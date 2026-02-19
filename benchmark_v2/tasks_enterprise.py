"""
BenchmarkSuite v2 — Enterprise Cost-Center Task Definitions

Three enterprise benchmark tasks targeting realistic B2B cost-center scenarios:
  1. contract_review       — Legal & Compliance
  2. code_review_protocol  — Software Engineering
  3. support_triage_system — Customer Support

These are designed to generate sales proof data showing org > single-agent
on real-world, high-stakes enterprise workflows.
"""
from dataclasses import dataclass, field

# Re-use the same base dataclasses from tasks.py (import them)
from benchmark_v2.tasks import SpecialistRole, Task

# ---------------------------------------------------------------------------
# Custom rubric dimensions per task (replacing standard RUBRIC_DIMENSIONS)
# ---------------------------------------------------------------------------

CONTRACT_REVIEW_RUBRIC = [
    ("risk_identification", "Identifies all HIGH severity risks with specific clause language"),
    ("specificity",         "Cites exact legal standards (GDPR Article numbers, case law, standard clauses)"),
    ("actionability",       "Every risk has a specific recommended amendment or mitigation"),
    ("completeness",        "All 5 required areas covered with substantive analysis"),
    ("commercial_balance",  "Balances legal protection with deal viability (not just risk-averse)"),
]

CODE_REVIEW_RUBRIC = [
    ("technical_precision",   "Specific tool names, config values, thresholds — no vague recommendations"),
    ("automation_coverage",   "What percentage of the gate can run without human intervention"),
    ("velocity_balance",      "Catches real bugs without creating bottlenecks (shipping 3x/day remains achievable)"),
    ("failure_handling",      "What happens when CI fails, reviewer is OOO, rollback is needed"),
    ("implementability",      "A team could set this up in 1 sprint"),
]

SUPPORT_TRIAGE_RUBRIC = [
    ("schema_completeness",   "Ticket schema, KB schema, escalation schema are all defined"),
    ("automation_ratio",      "What fraction of tickets can be resolved without human touch"),
    ("sla_rigor",             "SLA tracking is precise, breach prevention is proactive not reactive"),
    ("learning_loop",         "System gets measurably better over time (not static rules)"),
    ("client_tier_awareness", "Enterprise vs SMB clients handled differently"),
]

# ---------------------------------------------------------------------------
# Domain grounding strings (prepended to every specialist prompt)
# ---------------------------------------------------------------------------

CONTRACT_GROUNDING = (
    "You are a specialist in B2B SaaS contract law. This is a real enterprise software contract "
    "negotiation. Be specific about legal language, clause references (e.g. 'Section 12.3'), and "
    "actionable recommendations. Do not give generic legal advice — give specific contract amendments."
)

CODE_REVIEW_GROUNDING = (
    "You are a senior engineer in a high-velocity software organization shipping production code 3x "
    "daily. This is NOT theoretical — give concrete tool names (Ruff, Pyright, Snyk, Semgrep, etc.), "
    "specific thresholds (e.g. 'coverage must not drop below 80%'), and exact config snippets. "
    "Every recommendation must be immediately implementable."
)

SUPPORT_TRIAGE_GROUNDING = (
    "You are designing a real enterprise support system for a B2B SaaS company. Be specific: include "
    "ticket schema fields, routing rule logic (pseudo-code is fine), SLA calculation formulas, KB "
    "article templates, and escalation decision trees. This must be implementable by a support ops "
    "team in 60 days."
)

# ---------------------------------------------------------------------------
# TASK 1: contract_review — Legal & Compliance
# ---------------------------------------------------------------------------

contract_review = Task(
    id="contract_review",
    name="Enterprise SaaS Contract Review & Risk Analysis",
    prompt=(
        "You are reviewing a prospective enterprise SaaS contract for a B2B software company. "
        "The vendor is a mid-size US-based company, the client is a European enterprise (GDPR-applicable). "
        "Contract value: €480K/year, 3-year term.\n\n"
        "Produce a complete contract risk analysis covering ALL of:\n"
        "1. **Data sovereignty & GDPR compliance** — data residency, processor agreements, breach notification timelines\n"
        "2. **SLA and liability caps** — uptime guarantees, penalty structure, liability ceiling vs contract value\n"
        "3. **IP and data ownership** — who owns derived data, model outputs, client-specific fine-tuning\n"
        "4. **Exit and portability** — termination clauses, data export format, transition assistance obligations\n"
        "5. **Renewal and price escalation** — auto-renewal traps, CPI escalation caps, renegotiation rights\n\n"
        "Be as specific as possible: cite standard clause language, flag specific risks with severity "
        "(High/Medium/Low), and recommend exact contract amendments."
    ),
    specialist_roles=[
        SpecialistRole(
            name="GDPR & Privacy Counsel",
            memory_query="GDPR DPA data residency cross-border transfer SCCs adequacy",
            domain_instruction=(
                f"{CONTRACT_GROUNDING}\n\n"
                "Your focus: data protection law and GDPR compliance. Analyze: "
                "(a) whether a Data Processing Agreement (DPA) per GDPR Art. 28 is present and adequate; "
                "(b) data residency commitments — must data remain in EU/EEA or is US storage permitted; "
                "(c) cross-border transfer mechanism (Standard Contractual Clauses per Commission Decision "
                "2021/914, adequacy decisions, BCRs); "
                "(d) breach notification timelines — contract must require 72-hour notification per GDPR Art. 33; "
                "(e) data subject rights obligations passed to vendor (erasure, portability, access). "
                "Flag every gap as HIGH/MEDIUM/LOW severity and provide exact amendment language."
            ),
        ),
        SpecialistRole(
            name="Commercial Lawyer",
            memory_query="liability cap indemnification SLA penalty warranty disclaimer breach remedy",
            domain_instruction=(
                f"{CONTRACT_GROUNDING}\n\n"
                "Your focus: commercial and liability terms. Analyze: "
                "(a) liability cap — is it capped at 1× or 2× annual fees? Is it sufficient for a €480K/year deal? "
                "Industry standard for SaaS is 12 months of fees; "
                "(b) SLA and service credits — what uptime is guaranteed (99.9% = 8.7h downtime/year), "
                "are credits the sole remedy or is termination for cause available; "
                "(c) indemnification scope — IP infringement, data breaches, third-party claims; "
                "(d) warranty disclaimers — AS-IS disclaimers that nullify fitness for purpose; "
                "(e) force majeure overreach — vendor using FM to excuse controllable outages. "
                "Provide amendment language for each flagged clause."
            ),
        ),
        SpecialistRole(
            name="IP & Technology Counsel",
            memory_query="IP ownership data usage AI ML model rights derivative works fine-tuning",
            domain_instruction=(
                f"{CONTRACT_GROUNDING}\n\n"
                "Your focus: intellectual property and technology rights. Analyze: "
                "(a) ownership of client data — does vendor claim any license to use client data beyond "
                "service delivery? Watch for broad 'improve our services' language; "
                "(b) derived data and analytics — if vendor aggregates anonymized usage data, who owns it; "
                "(c) AI/ML model training — if the service uses ML, can vendor train on client data? "
                "Client-specific fine-tuned models — who owns them on termination; "
                "(d) derivative works — any work product created during the engagement (configs, integrations, "
                "custom modules); "
                "(e) license grant scope — is the license limited to client's internal use or transferable. "
                "Flag overreaching IP clauses with HIGH severity and provide restrictive amendment language."
            ),
        ),
        SpecialistRole(
            name="Procurement Specialist",
            memory_query="pricing renewal escalation auto-renewal negotiation leverage commercial terms",
            domain_instruction=(
                f"{CONTRACT_GROUNDING}\n\n"
                "Your focus: commercial terms, pricing mechanics, and negotiation leverage. Analyze: "
                "(a) auto-renewal traps — notice periods for non-renewal (should be ≥90 days), evergreen "
                "clauses that lock-in at higher rates; "
                "(b) price escalation — uncapped CPI or vendor-discretion increases are HIGH risk on a "
                "3-year term; recommend cap at CPI or 3%, whichever is lower; "
                "(c) renegotiation rights — trigger points if vendor is acquired, changes ownership, or "
                "materially changes the product; "
                "(d) volume discounts and MFN — most-favored-nation pricing protection; "
                "(e) payment terms — net-30 vs net-60, invoice dispute rights, late payment penalties. "
                "Identify where client has negotiation leverage (annual prepay, reference customer, etc.)."
            ),
        ),
        SpecialistRole(
            name="Risk & Compliance Officer",
            memory_query="enterprise risk scoring regulatory exposure audit rights insurance subprocessors",
            domain_instruction=(
                f"{CONTRACT_GROUNDING}\n\n"
                "Your focus: enterprise risk assessment and compliance requirements. Analyze: "
                "(a) subprocessor controls — vendor's right to change subprocessors without notice is HIGH risk; "
                "require 30-day advance notice and right to object; "
                "(b) audit rights — client's right to audit vendor's security posture (SOC 2 Type II, "
                "ISO 27001, pen test reports); "
                "(c) cyber insurance requirements — minimum coverage amounts vendor must maintain "
                "(recommend ≥$5M cyber liability); "
                "(d) business continuity — vendor's DR/BCP obligations, RTO/RPO commitments; "
                "(e) regulatory exposure — if client is in regulated industry (finance, healthcare), "
                "does vendor support compliance (FCA, EBA, NIS2). "
                "Score overall vendor risk as LOW/MEDIUM/HIGH/CRITICAL with justification."
            ),
        ),
    ],
    rubric=CONTRACT_REVIEW_RUBRIC,
)

# ---------------------------------------------------------------------------
# TASK 2: code_review_protocol — Software Engineering
# ---------------------------------------------------------------------------

code_review_protocol = Task(
    id="code_review_protocol",
    name="Production Code Review & Quality Gate Protocol",
    prompt=(
        "Design a complete code review and quality gate system for a 20-engineer Python/TypeScript "
        "monorepo shipping to production 3x per day. The system must handle:\n"
        "1. **Automated pre-review checks** — what runs before a human sees the PR (linting, type "
        "checking, test coverage, security scanning, dependency audit)\n"
        "2. **Review assignment logic** — how PRs are routed to reviewers (expertise matching, load "
        "balancing, conflict of interest rules, on-call rotation)\n"
        "3. **Review quality standards** — what constitutes an acceptable review (checklist items, "
        "required depth per change type, AI-assist integration)\n"
        "4. **Merge gate criteria** — exact conditions required to merge (approvals, CI status, "
        "coverage delta, performance regression thresholds)\n"
        "5. **Post-merge validation** — canary deployment logic, rollback triggers, production "
        "monitoring window\n\n"
        "Be extremely specific: include CLI commands, config file snippets, threshold values, timing "
        "windows, and escalation paths."
    ),
    specialist_roles=[
        SpecialistRole(
            name="DevOps / CI Engineer",
            memory_query="GitHub Actions CI pipeline deployment automation rollback canary",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: CI/CD pipeline architecture and deployment mechanics. Specify: "
                "(a) GitHub Actions workflow structure — exact job sequence (lint → test → security → build → deploy); "
                "provide a .github/workflows/pr-checks.yml skeleton with concrete step definitions; "
                "(b) parallelization strategy — which jobs can run in parallel to keep PR feedback under 5 minutes; "
                "(c) canary deployment config — what percentage of traffic routes to canary (1%→10%→50%→100%), "
                "bake time per stage (minimum 15 minutes), health check endpoints; "
                "(d) rollback mechanics — automated rollback trigger conditions, kubectl rollout undo vs "
                "Argo Rollouts, maximum rollback time target (< 3 minutes); "
                "(e) deployment frequency support — how the pipeline handles 3 deploys/day without "
                "queueing or blocking (feature flags, deploy locks, slot management)."
            ),
        ),
        SpecialistRole(
            name="Security Engineer",
            memory_query="SAST DAST dependency scanning secret detection CVE Snyk Semgrep",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: automated security gates in the PR pipeline. Specify: "
                "(a) SAST tooling — Semgrep with rulesets (p/python, p/typescript, p/owasp-top-ten); "
                "exact Semgrep CLI invocation and fail-on-severity threshold (CRITICAL/HIGH block merge, "
                "MEDIUM = warning only); "
                "(b) dependency scanning — Snyk or pip-audit + npm audit; CVE severity policy "
                "(CRITICAL: block immediately, HIGH: block after 7-day grace, MEDIUM: ticket only); "
                "(c) secret detection — Gitleaks or TruffleHog pre-commit + CI; zero-tolerance policy, "
                "any detected secret blocks merge and triggers incident; "
                "(d) container scanning — Trivy on Docker images before push to registry; "
                "(e) DAST — OWASP ZAP smoke scan against staging after deploy, before canary promotion. "
                "Include exact config file snippets for each tool."
            ),
        ),
        SpecialistRole(
            name="Senior Software Engineer",
            memory_query="code quality standards review depth technical debt architecture",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: code quality standards and review depth requirements. Specify: "
                "(a) automated quality checks — Ruff (Python linting + formatting, ruff.toml config), "
                "Pyright (strict mode for new code, basic for legacy), ESLint + Prettier for TypeScript; "
                "provide exact ruff.toml and pyrightconfig.json snippets; "
                "(b) test coverage thresholds — overall coverage must stay ≥80%, new code must be ≥90%; "
                "use diff-cover to check per-PR coverage delta; "
                "(c) review checklist by change type — hotfix (security review required), feature (design "
                "doc linked, test plan), refactor (benchmark before/after if perf-sensitive); "
                "(d) complexity gates — cyclomatic complexity ≤10 per function (enforced by Radon/lizard); "
                "(e) AI-assist integration — GitHub Copilot review suggestions as non-blocking annotations, "
                "CodeRabbit or similar for first-pass automated review comments."
            ),
        ),
        SpecialistRole(
            name="Engineering Manager",
            memory_query="review assignment load balancing on-call rotation conflict of interest velocity",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: review assignment algorithms and process governance. Specify: "
                "(a) reviewer assignment algorithm — CODEOWNERS file for expertise routing; "
                "load balancing: assign to engineer with fewest open reviews (tracked via GitHub GraphQL API); "
                "conflict of interest: no self-review, author's direct reports cannot approve; "
                "(b) on-call rotation integration — on-call engineer gets 50% fewer review assignments "
                "during their week; fallback: if primary reviewer unresponsive after 4 hours, auto-assign backup; "
                "(c) review SLAs — initial response within 2 business hours, full review within 4 hours "
                "for normal PRs, 1 hour for hotfixes; Slack alerts for SLA breaches; "
                "(d) minimum approvals by change type — hotfix: 1 senior, feature: 2 peers, "
                "API contract change: arch review required; "
                "(e) team velocity impact — target: PR cycle time ≤4 hours, merge-to-deploy ≤15 minutes."
            ),
        ),
        SpecialistRole(
            name="SRE / Reliability Engineer",
            memory_query="production validation SLO protection canary rollback monitoring window",
            domain_instruction=(
                f"{CODE_REVIEW_GROUNDING}\n\n"
                "Your focus: post-merge production validation and SLO protection. Specify: "
                "(a) canary health metrics — error rate (baseline ±0.1%), p99 latency (baseline +10ms max), "
                "CPU/memory within 115% of baseline; canary fails if any metric breaches for >2 minutes; "
                "(b) automated rollback decision tree — (1) error rate spike → immediate rollback, "
                "(2) latency degradation → wait 5 min then rollback if not recovering, "
                "(3) SLO burn rate alert (1h window >2% budget burn) → page on-call + pause rollout; "
                "(c) production monitoring window — 30-minute mandatory observation after each canary stage "
                "promotion before proceeding; SRE can override to fast-track hotfixes; "
                "(d) feature flag integration — all new features behind LaunchDarkly flags; canary can be "
                "instantly disabled via flag without redeploy; "
                "(e) deploy lock — no deploys during business-critical windows (e.g. month-end, major "
                "customer go-lives); deploy lock calendar managed in PagerDuty."
            ),
        ),
    ],
    rubric=CODE_REVIEW_RUBRIC,
)

# ---------------------------------------------------------------------------
# TASK 3: support_triage_system — Customer Support
# ---------------------------------------------------------------------------

support_triage_system = Task(
    id="support_triage_system",
    name="Enterprise Support Triage & Resolution System Design",
    prompt=(
        "Design a complete customer support triage and resolution system for a B2B SaaS company with "
        "500 enterprise clients, 3 support tiers (L1/L2/L3), and a 4-hour SLA for critical issues. "
        "The system must cover:\n"
        "1. **Intake & classification** — how tickets are received, parsed, and classified by "
        "type/severity/customer tier\n"
        "2. **Routing logic** — which tickets go to L1 vs L2 vs L3, and when to escalate automatically\n"
        "3. **Knowledge base integration** — how the system uses existing KB articles, when to create "
        "new ones, KB quality maintenance\n"
        "4. **SLA management** — tracking, alerting, breaching prevention, executive escalation paths\n"
        "5. **Resolution quality & feedback loop** — how resolved tickets improve the system over time\n\n"
        "Include specific data schemas, routing decision trees, SLA timing logic, and escalation triggers."
    ),
    specialist_roles=[
        SpecialistRole(
            name="Support Operations Engineer",
            memory_query="ticket system architecture routing workflow automation Zendesk Linear",
            domain_instruction=(
                f"{SUPPORT_TRIAGE_GROUNDING}\n\n"
                "Your focus: ticket system architecture and workflow automation. Specify: "
                "(a) complete ticket schema — define all fields: ticket_id, created_at, updated_at, "
                "source (email/API/Slack/portal), severity (P0/P1/P2/P3), type (bug/question/feature/"
                "incident), customer_id, customer_tier (Enterprise/Growth/Starter), assigned_agent, "
                "current_tier (L1/L2/L3), sla_deadline, escalation_count, tags[], custom_fields{}; "
                "(b) intake pipeline — email parsing (regex + NLP pre-classification), API webhook schema, "
                "Slack /support slash command integration; "
                "(c) routing rule engine — pseudo-code decision tree: if severity==P0 → L3 directly, "
                "elif customer_tier==Enterprise AND severity==P1 → L2, else → L1; "
                "(d) workflow automation — auto-assignment, auto-acknowledgment within 15 minutes, "
                "templated initial responses by ticket type; "
                "(e) tooling recommendation — Zendesk + custom middleware vs Linear for engineering "
                "escalations vs fully custom (Postgres + FastAPI). Justify choice for 500-client scale."
            ),
        ),
        SpecialistRole(
            name="Customer Success Manager",
            memory_query="customer tier prioritization escalation relationship impact enterprise",
            domain_instruction=(
                f"{SUPPORT_TRIAGE_GROUNDING}\n\n"
                "Your focus: customer tier prioritization and relationship-aware escalation. Specify: "
                "(a) tier definitions and SLA mapping — Enterprise (ARR >€100K): P0=1h, P1=4h, P2=24h; "
                "Growth (ARR €10-100K): P0=2h, P1=8h, P2=48h; Starter (<€10K): P0=4h, P1=24h, P2=72h; "
                "(b) escalation judgment criteria — beyond automated rules, when should CSM manually "
                "escalate? (renewal within 90 days, client recently flagged as churn risk, executive "
                "sponsor is involved in the ticket); "
                "(c) relationship impact scoring — assign 'relationship heat' score (1-5) based on: "
                "open ticket count, CSAT trend, NPS score, upcoming renewal date; heat ≥4 triggers CSM "
                "personal involvement regardless of severity; "
                "(d) executive escalation path — if P0 for Enterprise client breaches 2h without resolution, "
                "CSM Director + VP Customer Success are auto-notified via PagerDuty; "
                "(e) post-resolution follow-up — Enterprise clients get personal CSM call within 24h of "
                "P0/P1 resolution; standardized post-mortem template for client-facing incidents."
            ),
        ),
        SpecialistRole(
            name="ML / AI Engineer",
            memory_query="ticket classification NLP KB semantic search response suggestion pattern detection",
            domain_instruction=(
                f"{SUPPORT_TRIAGE_GROUNDING}\n\n"
                "Your focus: ML/AI systems for ticket classification and KB integration. Specify: "
                "(a) classification model — fine-tuned sentence-transformers (e.g. all-MiniLM-L6-v2) for "
                "ticket type + severity classification; training data: historical tickets with labels; "
                "retrain monthly; target accuracy ≥85% on severity, ≥90% on type; "
                "(b) KB semantic search — embed all KB articles using the same model; on new ticket, "
                "cosine similarity search returns top-3 candidate articles (threshold >0.75 for auto-suggest); "
                "(c) response suggestion — LLM (GPT-4o or Claude) drafts L1 response using: ticket text + "
                "top-3 KB articles + similar resolved tickets; agent reviews before sending; "
                "(d) pattern detection — sliding window analysis: if same error code appears in >3 tickets "
                "in 4h window → auto-create P1 incident and alert L3 + SRE; "
                "(e) feedback loop — agents rate AI suggestions (thumbs up/down); poor suggestions "
                "are flagged for retraining dataset; weekly model drift monitoring with Evidently AI."
            ),
        ),
        SpecialistRole(
            name="Knowledge Management Specialist",
            memory_query="KB structure article quality gap analysis KB update triggers templates",
            domain_instruction=(
                f"{SUPPORT_TRIAGE_GROUNDING}\n\n"
                "Your focus: knowledge base architecture and quality governance. Specify: "
                "(a) KB article schema — article_id, title, category, subcategory, product_area, "
                "severity_applicability[], created_by, reviewed_by, last_reviewed_at, "
                "version, status (draft/published/archived), linked_tickets[], "
                "resolution_rate (% of tickets this article resolved), thumbs_up_count, thumbs_down_count; "
                "(b) article quality standards — required sections: Problem Statement, Root Cause, "
                "Step-by-Step Resolution, Verification Steps, Related Articles; max 800 words; "
                "must be reviewed by L2/L3 before publishing; reviewed every 90 days or after product change; "
                "(c) gap detection — if a ticket is resolved without an existing KB article match, "
                "system creates a 'KB gap ticket' assigned to Knowledge Management queue; "
                "L2+ who resolved the ticket must draft article within 5 business days; "
                "(d) automated update triggers — product changelog events trigger KB review workflow "
                "for all articles tagged with the changed product_area; "
                "(e) KB health metrics — weekly report: coverage ratio (tickets resolved via KB / total), "
                "stale articles (not reviewed in >90 days), low-performing articles (resolution_rate <20%)."
            ),
        ),
        SpecialistRole(
            name="SLA & Compliance Analyst",
            memory_query="SLA breach tracking audit trail executive reporting compliance",
            domain_instruction=(
                f"{SUPPORT_TRIAGE_GROUNDING}\n\n"
                "Your focus: SLA management, breach prevention, and compliance audit trail. Specify: "
                "(a) SLA calculation formula — SLA clock starts at ticket_created_at for email/portal; "
                "for after-hours P0: clock starts at next business hour start UNLESS client is on "
                "24/7 SLA addendum (Enterprise tier option); business hours = 08:00-18:00 CET Mon-Fri "
                "excluding public holidays (configurable per client locale); "
                "(b) breach prevention alerting — alert assigned agent at 50% SLA consumed, "
                "alert agent + team lead at 75%, auto-escalate to next tier + notify CSM at 90%; "
                "(c) SLA breach tracking schema — breach_id, ticket_id, sla_deadline, actual_resolution_time, "
                "breach_duration_minutes, breach_reason (capacity/complexity/escalation_delay/other), "
                "responsible_tier, compensable (bool per contract); "
                "(d) audit trail requirements — immutable log of all ticket state transitions with "
                "timestamp + agent_id; retained for 3 years (GDPR Art. 5(1)(e) storage limitation balance "
                "with contract audit rights); exportable to CSV/JSON for customer audits; "
                "(e) executive reporting — weekly SLA scorecard: breach rate by tier, MTTR by severity, "
                "top-10 ticket categories, KB deflection rate; monthly board-level summary."
            ),
        ),
    ],
    rubric=SUPPORT_TRIAGE_RUBRIC,
)

# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

ENTERPRISE_TASKS = [contract_review, code_review_protocol, support_triage_system]
ENTERPRISE_TASK_MAP = {t.id: t for t in ENTERPRISE_TASKS}
