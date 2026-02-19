# BenchmarkSuite v2 — MachineMachine AI Organizational Learning

# Auto-register enterprise tasks into the canonical TASK_MAP / ALL_TASKS
# so that run_suite.py --tasks contract_review ... resolves correctly.
# This import is safe: tasks_enterprise.py only imports SpecialistRole/Task
# from tasks.py, creating no circular dependency.
try:
    from benchmark_v2.tasks_enterprise import ENTERPRISE_TASKS, ENTERPRISE_TASK_MAP
    from benchmark_v2 import tasks as _tasks

    for _task in ENTERPRISE_TASKS:
        if _task.id not in _tasks.TASK_MAP:
            _tasks.ALL_TASKS.append(_task)
            _tasks.TASK_MAP[_task.id] = _task
except Exception as _e:
    import warnings
    warnings.warn(f"Could not register enterprise tasks: {_e}")
