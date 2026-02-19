"""
BenchmarkSuite v2 — Algorithm 1: Formal Organizational Learning Loop

For each (task, topology) condition:
  1. Run SA baseline (cached per task)
  2. Run MA org with current protocol + org_memory
  3. Evaluate blind (n_eval_runs × haiku evaluator)
  4. If delta > threshold OR iter >= max_iter: STOP
  5. Run retrospective → update org_memory
  6. Repeat

This is the core publishable algorithm.
"""
import json, time, datetime
from dataclasses import dataclass, field
from pathlib import Path

from .tasks import Task
from .topologies import TOPOLOGY_RUNNERS, TopologyResult
from .evaluator import evaluate_blind, EvalResult, format_eval_summary
from .retrospective import run_retrospective, FixProposal
from .llm_clients import cerebras_call


@dataclass
class IterationRecord:
    iteration: int
    topology: str
    sa_score: float
    ma_score: float
    delta: float
    p_value: float
    cohens_d: float
    sa_std: float
    ma_std: float
    failure_mode: str
    protocol_fix: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


@dataclass
class LearningResult:
    task_id: str
    topology: str
    iterations: list[IterationRecord] = field(default_factory=list)
    final_delta: float = 0.0
    final_sa_score: float = 0.0
    final_ma_score: float = 0.0
    convergence_iter: int = 0
    learning_rate: float = 0.0   # mean delta improvement per iteration
    converged: bool = False
    org_memory: dict = field(default_factory=dict)
    total_time_s: float = 0.0

    def compute_learning_rate(self):
        if len(self.iterations) < 2:
            self.learning_rate = 0.0
            return
        deltas = [r.delta for r in self.iterations]
        improvements = [deltas[i+1] - deltas[i] for i in range(len(deltas)-1)]
        self.learning_rate = sum(improvements) / len(improvements)


def run_sa_baseline(task: Task, verbose: bool = True) -> str:
    """Run single-agent baseline. Returns output string."""
    if verbose:
        print(f"  [SA Baseline] Running...")
    prompt = f"You are an expert. {task.prompt}\nBe comprehensive and technically specific."
    output, elapsed = cerebras_call(prompt, max_tokens=3000)
    if verbose:
        print(f"  [SA Baseline] Done — {len(output.split())} words ({elapsed:.1f}s)")
    return output


def learning_loop(
    task: Task,
    topology: str,
    sa_output: str = None,           # pass if already computed (shared baseline)
    max_iterations: int = 5,
    convergence_threshold: float = 10.0,
    evaluator_runs: int = 3,
    org_memory: dict = None,
    output_dir: Path = None,
    verbose: bool = True,
) -> LearningResult:
    """
    Algorithm 1: Formal Organizational Learning Loop.
    """
    result = LearningResult(task_id=task.id, topology=topology)
    result.org_memory = org_memory or {}
    run_fn = TOPOLOGY_RUNNERS[topology]
    t_start = time.time()

    # SA baseline (shared across topologies for same task)
    if sa_output is None:
        sa_output = run_sa_baseline(task, verbose=verbose)

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'─'*60}")
        print(f"  [{task.id}] [{topology}] Iteration {iteration}/{max_iterations}")
        print(f"{'─'*60}")

        # Run MA org
        if verbose:
            print(f"  [MA Org] Running {topology} topology...")
        topo_result: TopologyResult = run_fn(task, org_memory=result.org_memory)
        ma_output = topo_result.final_output
        if verbose:
            print(f"  [MA Org] Done — {len(ma_output.split())} words, {topo_result.total_time:.1f}s")

        # Blind evaluation
        if verbose:
            print(f"  [Evaluator] Blind evaluation ({evaluator_runs} runs)...")
        eval_result: EvalResult = evaluate_blind(
            sa_output, ma_output, task,
            n_runs=evaluator_runs, verbose=verbose
        )
        print(f"  → {format_eval_summary(eval_result)}")

        # Record iteration
        record = IterationRecord(
            iteration=iteration,
            topology=topology,
            sa_score=eval_result.sa_mean,
            ma_score=eval_result.ma_mean,
            delta=eval_result.delta_mean,
            p_value=eval_result.p_value,
            cohens_d=eval_result.cohens_d,
            sa_std=eval_result.sa_std,
            ma_std=eval_result.ma_std,
            failure_mode="",
            protocol_fix="",
        )

        # Check convergence
        converged = eval_result.delta_mean >= convergence_threshold or iteration >= max_iterations
        result.final_delta = eval_result.delta_mean
        result.final_sa_score = eval_result.sa_mean
        result.final_ma_score = eval_result.ma_mean

        if converged:
            result.convergence_iter = iteration
            result.converged = eval_result.delta_mean >= convergence_threshold
            record.failure_mode = "converged"
            result.iterations.append(record)
            if verbose:
                reason = f"delta={eval_result.delta_mean:.1f} >= {convergence_threshold}" if result.converged else "max iterations"
                print(f"  [Convergence] Stopping — {reason}")
            # Save intermediate
            _save_intermediate(result, output_dir, task, topology, iteration)
            break

        # Retrospective
        fix: FixProposal = run_retrospective(
            task_name=task.name,
            task_prompt=task.prompt,
            sa_output=sa_output,
            ma_output=ma_output,
            eval_result=eval_result,
            topology=topology,
            iteration=iteration,
            org_memory=result.org_memory,
            verbose=verbose,
        )
        record.failure_mode = fix.failure_mode
        record.protocol_fix = fix.protocol_fix
        result.iterations.append(record)

        # Save intermediate results after each iteration
        _save_intermediate(result, output_dir, task, topology, iteration)

    result.total_time_s = time.time() - t_start
    result.compute_learning_rate()
    return result


def _save_intermediate(result: LearningResult, output_dir: Path, task: Task, topology: str, iteration: int):
    if output_dir is None:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = output_dir / f"{task.id}_{topology}_iter{iteration:02d}.json"
    with open(fname, "w") as f:
        json.dump(_result_to_dict(result), f, indent=2)


def _result_to_dict(result: LearningResult) -> dict:
    return {
        "task_id": result.task_id,
        "topology": result.topology,
        "final_delta": result.final_delta,
        "final_sa_score": result.final_sa_score,
        "final_ma_score": result.final_ma_score,
        "convergence_iter": result.convergence_iter,
        "learning_rate": result.learning_rate,
        "converged": result.converged,
        "total_time_s": result.total_time_s,
        "org_memory": result.org_memory,
        "iterations": [
            {
                "iteration": r.iteration,
                "sa_score": r.sa_score,
                "ma_score": r.ma_score,
                "delta": r.delta,
                "p_value": r.p_value,
                "cohens_d": r.cohens_d,
                "sa_std": r.sa_std,
                "ma_std": r.ma_std,
                "failure_mode": r.failure_mode,
                "protocol_fix": r.protocol_fix,
                "timestamp": r.timestamp,
            }
            for r in result.iterations
        ],
    }
