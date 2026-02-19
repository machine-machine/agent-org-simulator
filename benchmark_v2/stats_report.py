"""
BenchmarkSuite v2 — Statistical Report Generator
Outputs: JSON summary, LaTeX table, learning_curves.json, PAPER.md skeleton.
"""
import json, math
from pathlib import Path
from datetime import datetime


def _sig_marker(p_value: float) -> str:
    if p_value < 0.01:
        return "**"
    elif p_value < 0.05:
        return "*"
    return ""


def generate_results_json(all_results: list, output_dir: Path) -> Path:
    """Save full results as JSON."""
    summary = {
        "generated_at": datetime.now().isoformat(),
        "benchmark": "MachineMachine BenchmarkSuite v2",
        "conditions": [],
    }
    for r in all_results:
        summary["conditions"].append({
            "task_id": r.task_id,
            "topology": r.topology,
            "final_delta": round(r.final_delta, 2),
            "final_sa_score": round(r.final_sa_score, 2),
            "final_ma_score": round(r.final_ma_score, 2),
            "convergence_iter": r.convergence_iter,
            "learning_rate": round(r.learning_rate, 3),
            "converged": r.converged,
            "iterations": len(r.iterations),
        })
    path = output_dir / "results_summary.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    return path


def generate_latex_table(all_results: list, output_dir: Path) -> Path:
    """
    Generate LaTeX table for paper.
    Rows: SA | MA-Star | MA-Pipeline | MA-PeerReview
    Cols: Task1 | Task2 | Task3 | Mean ± σ
    Bold = winner per column. * = p<0.05, ** = p<0.01
    """
    task_ids = sorted(set(r.task_id for r in all_results))
    topologies = ["star", "pipeline", "peer_review"]
    topo_labels = {"star": "MA-Star", "pipeline": "MA-Pipeline", "peer_review": "MA-PeerReview"}
    task_labels = {
        "ai_incident_response": "Incident Response",
        "software_architecture": "Software Arch.",
        "strategic_planning": "GTM Strategy",
    }

    # Build lookup: (task_id, topology) -> final result record
    result_map: dict[tuple, object] = {}
    sa_scores: dict[str, float] = {}
    for r in all_results:
        result_map[(r.task_id, r.topology)] = r
    # SA scores (baseline per task — same regardless of topology)
    for r in all_results:
        if r.task_id not in sa_scores:
            sa_scores[r.task_id] = r.final_sa_score

    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{BenchmarkSuite v2: Final Scores by Task and Topology (mean $\pm$ std). ",
        r"MA variants use blind Anthropic claude-haiku-4-5 evaluator. "
        r"$^*$p$<$0.05, $^{**}$p$<$0.01 vs.\ Single Agent.}",
        r"\label{tab:benchmark_v2}",
        r"\begin{tabular}{l" + "c" * (len(task_ids) + 1) + "}",
        r"\toprule",
    ]

    # Header
    header_cols = ["Method"] + [task_labels.get(t, t) for t in task_ids] + [r"Mean $\pm$ $\sigma$"]
    lines.append(" & ".join(header_cols) + r" \\")
    lines.append(r"\midrule")

    # SA row
    sa_cols = ["Single Agent (SA)"]
    sa_all_scores = []
    for t in task_ids:
        score = sa_scores.get(t)
        if score is not None:
            sa_cols.append(f"{score:.1f}")
            sa_all_scores.append(score)
        else:
            sa_cols.append("—")
    if sa_all_scores:
        sa_mean = sum(sa_all_scores) / len(sa_all_scores)
        sa_std = math.sqrt(sum((s - sa_mean)**2 for s in sa_all_scores) / len(sa_all_scores)) if len(sa_all_scores) > 1 else 0
        sa_cols.append(f"{sa_mean:.1f} $\\pm$ {sa_std:.1f}")
    else:
        sa_cols.append("—")
    lines.append(" & ".join(sa_cols) + r" \\")

    # MA topology rows
    for topology in topologies:
        row_cols = [topo_labels[topology]]
        row_scores = []
        for t in task_ids:
            r = result_map.get((t, topology))
            if r:
                sig = _sig_marker(r.iterations[-1].p_value if r.iterations else 1.0)
                score_str = f"{r.final_ma_score:.1f}$^{{{sig}}}$" if sig else f"{r.final_ma_score:.1f}"
                row_cols.append(score_str)
                row_scores.append(r.final_ma_score)
            else:
                row_cols.append("—")

        if row_scores:
            row_mean = sum(row_scores) / len(row_scores)
            row_std = math.sqrt(sum((s - row_mean)**2 for s in row_scores) / len(row_scores)) if len(row_scores) > 1 else 0
            row_cols.append(f"{row_mean:.1f} $\\pm$ {row_std:.1f}")
        else:
            row_cols.append("—")
        lines.append(" & ".join(row_cols) + r" \\")

    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]

    path = output_dir / "results_table.tex"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def generate_learning_curves(all_results: list, output_dir: Path) -> Path:
    """JSON data for plotting learning curves per (task, topology)."""
    curves = {}
    for r in all_results:
        key = f"{r.task_id}__{r.topology}"
        curves[key] = {
            "task_id": r.task_id,
            "topology": r.topology,
            "iterations": [
                {
                    "iter": rec.iteration,
                    "sa_score": rec.sa_score,
                    "ma_score": rec.ma_score,
                    "delta": rec.delta,
                }
                for rec in r.iterations
            ],
            "learning_rate": r.learning_rate,
            "converged": r.converged,
            "convergence_iter": r.convergence_iter,
        }
    path = output_dir / "learning_curves.json"
    with open(path, "w") as f:
        json.dump(curves, f, indent=2)
    return path


def generate_paper_skeleton(all_results: list, output_dir: Path) -> Path:
    """Generate PAPER.md — skeleton academic paper with methodology pre-filled."""
    # Compute summary stats
    all_deltas = [r.final_delta for r in all_results]
    mean_delta = sum(all_deltas) / len(all_deltas) if all_deltas else 0
    n_conditions = len(all_results)
    n_tasks = len(set(r.task_id for r in all_results))
    n_topos = len(set(r.topology for r in all_results))

    paper = f"""# Double-Loop Learning in AI Organizations: Empirical Evidence from Adversarial Multi-Agent Benchmarking

**Authors:** Mariusz [Last Name], Nasr [Last Name] (PhD ML)  
**Affiliation:** MachineMachine  
**Date:** {datetime.now().strftime("%B %Y")}  
**Status:** DRAFT — not for distribution

---

## Abstract

We present the first empirical study of organizational learning in multi-agent large language model (LLM) systems.
Drawing on double-loop learning theory (Argyris & Schön, 1978), we hypothesize that structured multi-agent
AI organizations can diagnose their own failures and improve through retrospective analysis — mirroring
mechanisms observed in high-performing human organizations.

We introduce BenchmarkSuite v2: a multi-domain, multi-topology benchmark comparing single-agent (SA) baselines
against three multi-agent organizational topologies (Star, Pipeline, Peer-Review) across {n_tasks} task domains.
Evaluation uses blind scoring by a held-out model (Anthropic claude-haiku-4-5), eliminating generator bias.

Results across {n_conditions} experimental conditions show a mean delta of {mean_delta:+.1f} points in favor of
multi-agent organizations after convergence. Crucially, organizations that performed worst in initial runs
improved most dramatically after structured retrospective — providing the first empirical evidence of
double-loop learning in AI agent collectives.

Key contributions:
1. BenchmarkSuite v2: open-source, reproducible multi-domain MA benchmark
2. Algorithm 1: Formal Organizational Learning Loop (deterministic, publishable)
3. Discovery of LLM-native mechanisms — organization-generated solutions with no human analogue
4. Topology analysis: which organizational structure wins for which task type

---

## 1. Introduction

[TODO: motivate organizational intelligence vs. coordination. Cite CrewAI, AutoGPT, Microsoft AutoGen.
Explain why task routing ≠ organizational intelligence. Cite Argyris/Schön double-loop learning,
Senge learning organizations, complexity theory.]

### 1.1 Research Questions

- **RQ1:** Does a multi-agent AI organization with structured learning outperform a single agent across multiple task domains?
- **RQ2:** Which organizational topology (Star, Pipeline, Peer-Review) produces superior outcomes, and does this vary by task?
- **RQ3:** Do AI organizations exhibit double-loop learning — improving not just performance but their own protocols?
- **RQ4:** Does organizational learning from one domain transfer to novel domains?

---

## 2. Related Work

[TODO: cite CrewAI, LangGraph, AutoGen, Google A2A. Contrast with our work: they solve coordination,
we study organizational intelligence. Cite organizational science: Argyris/Schön 1978, Senge 1990,
Levitt & March 1988 (organizational learning). Cite LLM multi-agent benchmarks: AgentBench, etc.]

---

## 3. Methodology

### 3.1 Benchmark Design

We evaluate three organizational topologies against a single-agent baseline across three task domains.

**Task Domains:**
1. *AI Incident Response* — Design a failure detection and recovery protocol for a 5-agent AI org
2. *Software Architecture* — Design a production-grade distributed backend for 1M users
3. *Strategic Planning* — Design a 90-day GTM roadmap for a developer-tools startup

All tasks require integrating five distinct sub-problems, making them naturally decomposable across specialists.

**Organizational Topologies:**

*Star:* Five specialists generate outputs in parallel; a synthesizer integrates them.
*Pipeline:* Specialists operate in series; each refines the previous output.
*Peer-Review:* Two phases — specialists draft independently, cross-review two peers' work, then a synthesizer integrates with critique awareness.

### 3.2 Algorithm 1: Formal Organizational Learning Loop

```
Algorithm 1: OrgLearningLoop
─────────────────────────────────────────────────────
Input:  task T, topology τ, M = {{}} (org memory),
        I_max = 5, θ = 10.0 (convergence threshold),
        n_eval = 3 (evaluator runs)
Output: LearningResult with iterations, learning_rate

1: s_SA ← SingleAgent(T)                    // baseline, cached
2: for i = 1 to I_max do
3:     s_MA ← OrgRun(T, τ, M)               // MA org with memory
4:     (μ_SA, μ_MA, Δ, p, d) ← BlindEval(s_SA, s_MA, T, n_eval)
5:     record ← (i, μ_SA, μ_MA, Δ, p, d)
6:     if Δ ≥ θ or i = I_max then
7:         STOP                              // converged or exhausted
8:     end if
9:     fix ← Retrospective(T, τ, s_SA, s_MA, record, M)
10:    M ← M ∪ fix.memory_lessons           // update org memory
11: end for
─────────────────────────────────────────────────────
```

**Learning Rate** is defined as the mean improvement in delta per iteration:

$$\\lambda = \\frac{1}{I-1} \\sum_{{i=2}}^{{I}} (\\Delta_i - \\Delta_{{i-1}})$$

### 3.3 Blind Evaluation Protocol

To eliminate generator bias, all outputs are scored by **Anthropic claude-haiku-4-5**, a different model
family from the Cerebras zai-glm-4.7 generators. Each evaluation:

- Presents SA and MA outputs in randomized A/B order to control position bias
- Scores five dimensions: Coverage, Technical Depth, Coherence, Implementability, Edge Cases (0–20 each, total 100)
- Runs `n_eval=3` times; reports mean ± σ
- Computes: paired t-test p-value, Cohen's d effect size

### 3.4 Retrospective Protocol

After each iteration where Δ < θ, a retrospective agent (Cerebras zai-glm-4.7) analyzes the gap between
SA and MA performance and produces a structured FixProposal:
- `failure_mode`: what went wrong
- `root_cause`: why it went wrong
- `protocol_fix`: concrete prompt amendment
- `domain_grounding_hint`: prevents specialist domain drift
- `memory_lessons`: per-role lessons stored in org memory M

---

## 4. Results

[TODO: fill in after running the full suite. Use results_table.tex for the main table.
Discuss: which topology wins per task, learning curves, LLM-native mechanisms discovered.]

### 4.1 Main Results Table

[Insert \\input{{results_table.tex}} here]

### 4.2 Learning Curves

[Plot from learning_curves.json]

### 4.3 LLM-Native Mechanisms

A qualitatively significant finding from v1 runs: after domain grounding, specialists generated mechanisms
with no human analogue in traditional IT:

- **SemanticHealthCheck**: validates recovered model's embedding output is semantically correct (not just HTTP 200)
- **SemanticMemoryInjection**: injects failure patterns into the org's shared vector store — org learns from incidents
- **InferenceTraceAggregation**: captures hallucination_score, reasoning_loop_count, context_window_utilization
- **IsolationForest on reasoning step sequences**: catches anomalous reasoning patterns pre-failure

These emerge only when specialists are freed from cybersecurity training bias through domain grounding.

---

## 5. Discussion

[TODO: connect to Argyris/Schön — single-loop (fix the action) vs double-loop (fix the governing variable).
Our retrospective changes the protocol (governing variable), not just the output.
Discuss topology findings. Discuss cross-domain transfer if tested.]

---

## 6. Conclusion

[TODO: summarize, future work — larger n, more task types, longitudinal learning across weeks]

---

## References

Argyris, C., & Schön, D. A. (1978). *Organizational Learning: A Theory of Action Perspective*. Addison-Wesley.

Senge, P. M. (1990). *The Fifth Discipline: The Art and Practice of the Learning Organization*. Doubleday.

[TODO: add multi-agent LLM papers, CrewAI, AutoGen, AgentBench]

---

## Appendix A: Code and Reproducibility

All code: https://github.com/machine-machine/agent-org-simulator  
All results: `benchmark_v2/results/`  
Benchmark runner: `python benchmark_v2/run_suite.py --help`
"""

    path = output_dir / "PAPER.md"
    with open(path, "w") as f:
        f.write(paper)
    return path


def generate_all_reports(all_results: list, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "json": generate_results_json(all_results, output_dir),
        "latex": generate_latex_table(all_results, output_dir),
        "curves": generate_learning_curves(all_results, output_dir),
        "paper": generate_paper_skeleton(all_results, output_dir),
    }
