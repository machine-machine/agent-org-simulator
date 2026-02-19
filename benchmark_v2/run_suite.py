#!/usr/bin/env python3
"""
BenchmarkSuite v2 — Main Entry Point

Usage:
  python run_suite.py                                      # all tasks, star only, 3 iters
  python run_suite.py --tasks all --topologies all         # full suite
  python run_suite.py --tasks ai_incident_response --topologies star pipeline --iterations 4
  python run_suite.py --tasks software_architecture --topologies peer_review --eval-runs 3 --dry-run
  python run_suite.py --resume results/                    # resume from saved intermediates

Outputs in: benchmark_v2/results/ (or --output)
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # add parent to path

from benchmark_v2.tasks import ALL_TASKS, TASK_MAP
from benchmark_v2.topologies import TOPOLOGY_RUNNERS
from benchmark_v2.learning_loop import learning_loop, run_sa_baseline, LearningResult
from benchmark_v2.stats_report import generate_all_reports

ALL_TOPOLOGIES = list(TOPOLOGY_RUNNERS.keys())


def print_header(task_ids: list, topologies: list, iterations: int, eval_runs: int):
    print("\n" + "="*70)
    print("  MachineMachine BenchmarkSuite v2")
    print("="*70)
    print(f"  Tasks:      {', '.join(task_ids)}")
    print(f"  Topologies: {', '.join(topologies)}")
    print(f"  Iterations: {iterations} per condition")
    print(f"  Eval runs:  {eval_runs} (blind Anthropic haiku evaluator)")
    print(f"  Conditions: {len(task_ids) * len(topologies)} total")
    print("="*70 + "\n")


def print_final_table(all_results: list):
    print("\n" + "="*70)
    print("  FINAL RESULTS SUMMARY")
    print("="*70)
    print(f"  {'Task':<25} {'Topology':<15} {'SA':>6} {'MA':>6} {'Δ':>6} {'p':>7} {'d':>6}")
    print("-"*70)
    for r in all_results:
        last = r.iterations[-1] if r.iterations else None
        if last:
            p_str = f"{last.p_value:.3f}" if last.p_value < 1.0 else "  —  "
            d_str = f"{last.cohens_d:+.2f}" if last.cohens_d != 0 else "  —  "
            winner = "✓" if r.final_delta > 3 else ("✗" if r.final_delta < -3 else "~")
            print(f"  {r.task_id:<25} {r.topology:<15} {r.final_sa_score:>6.1f} {r.final_ma_score:>6.1f} {r.final_delta:>+6.1f} {p_str:>7} {d_str:>6}  {winner}")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="MachineMachine BenchmarkSuite v2")
    parser.add_argument("--tasks", nargs="+", default=["ai_incident_response"],
                        help=f"Task IDs or 'all'. Options: {[t.id for t in ALL_TASKS]}")
    parser.add_argument("--topologies", nargs="+", default=["star"],
                        help=f"Topologies or 'all'. Options: {ALL_TOPOLOGIES}")
    parser.add_argument("--iterations", type=int, default=3, help="Max learning iterations per condition")
    parser.add_argument("--eval-runs", type=int, default=3, help="Evaluator runs per condition (blind)")
    parser.add_argument("--convergence", type=float, default=10.0, help="Delta threshold to stop early")
    parser.add_argument("--output", type=str, default="benchmark_v2/results", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without running")
    parser.add_argument("--no-transfer", action="store_true", help="Skip cross-domain memory transfer")
    args = parser.parse_args()

    # Resolve tasks
    if "all" in args.tasks:
        tasks = ALL_TASKS
    else:
        tasks = [TASK_MAP[t] for t in args.tasks if t in TASK_MAP]
        unknown = [t for t in args.tasks if t not in TASK_MAP and t != "all"]
        if unknown:
            print(f"Unknown tasks: {unknown}. Available: {list(TASK_MAP.keys())}")
            sys.exit(1)

    # Resolve topologies
    if "all" in args.topologies:
        topologies = ALL_TOPOLOGIES
    else:
        topologies = [t for t in args.topologies if t in TOPOLOGY_RUNNERS]
        unknown = [t for t in args.topologies if t not in TOPOLOGY_RUNNERS and t != "all"]
        if unknown:
            print(f"Unknown topologies: {unknown}. Available: {ALL_TOPOLOGIES}")
            sys.exit(1)

    output_dir = Path(args.output)
    task_ids = [t.id for t in tasks]

    print_header(task_ids, topologies, args.iterations, args.eval_runs)

    if args.dry_run:
        print("  [DRY RUN] Would run these conditions:")
        for task in tasks:
            for topology in topologies:
                print(f"    - {task.id} × {topology}")
        return

    all_results: list[LearningResult] = []
    # Cache SA baselines per task (shared across topologies for same task)
    sa_cache: dict[str, str] = {}

    for task in tasks:
        print(f"\n{'#'*70}")
        print(f"  TASK: {task.name}")
        print(f"{'#'*70}")

        # Shared SA baseline for all topologies on this task
        if task.id not in sa_cache:
            print(f"\n  Computing SA baseline for {task.id}...")
            sa_cache[task.id] = run_sa_baseline(task, verbose=True)

        # Shared org_memory across topologies for this task (cross-topology transfer)
        shared_memory: dict = {}

        for topology in topologies:
            print(f"\n  {'='*60}")
            print(f"  CONDITION: {task.id} × {topology}")
            print(f"  {'='*60}")

            result = learning_loop(
                task=task,
                topology=topology,
                sa_output=sa_cache[task.id],
                max_iterations=args.iterations,
                convergence_threshold=args.convergence,
                evaluator_runs=args.eval_runs,
                org_memory=shared_memory.copy() if not args.no_transfer else {},
                output_dir=output_dir,
                verbose=True,
            )

            # Cross-topology memory transfer: share lessons with next topology
            if not args.no_transfer:
                shared_memory.update(result.org_memory)

            all_results.append(result)

    # Final reports
    print("\n\nGenerating reports...")
    report_paths = generate_all_reports(all_results, output_dir)
    print_final_table(all_results)

    print("\nOutputs:")
    for label, path in report_paths.items():
        print(f"  {label:<10} → {path}")

    # Notify if running in OpenClaw context
    import subprocess
    subprocess.run(
        ["openclaw", "system", "event",
         "--text", f"BenchmarkSuite v2 done: {len(all_results)} conditions, mean Δ={sum(r.final_delta for r in all_results)/len(all_results):+.1f}",
         "--mode", "now"],
        capture_output=True
    )


if __name__ == "__main__":
    main()
