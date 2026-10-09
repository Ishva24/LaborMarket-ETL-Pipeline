"""
Unit and integration test suite for the LaborMarket ETL Orchestrator.
"""

import pytest
from src.orchestrator import PipelineDAG, PipelineTask, TaskState


def test_topological_sort_linear():
    dag = PipelineDAG("linear_test")
    dag.add_task(PipelineTask(name="extract", action=lambda: {"rows": 100}))
    dag.add_task(PipelineTask(name="transform", action=lambda: {"transformed": True}, dependencies=["extract"]))
    dag.add_task(PipelineTask(name="load", action=lambda: {"loaded": True}, dependencies=["transform"]))

    order = dag.topological_sort()
    assert order == ["extract", "transform", "load"]


def test_topological_sort_circular_detection():
    dag = PipelineDAG("circular_test")
    dag.add_task(PipelineTask(name="task_a", action=lambda: {}, dependencies=["task_b"]))
    dag.add_task(PipelineTask(name="task_b", action=lambda: {}, dependencies=["task_a"]))

    with pytest.raises(ValueError, match="Circular dependency"):
        dag.topological_sort()


def test_execution_success():
    call_log = []

    def step1():
        call_log.append("step1")
        return {"data": 1}

    def step2():
        call_log.append("step2")
        return {"data": 2}

    dag = PipelineDAG("exec_test")
    dag.add_task(PipelineTask(name="step1", action=step1))
    dag.add_task(PipelineTask(name="step2", action=step2, dependencies=["step1"]))

    results = dag.execute()
    assert results["step1"].state == TaskState.SUCCESS
    assert results["step2"].state == TaskState.SUCCESS
    assert call_log == ["step1", "step2"]


def test_retry_on_failure_then_recover():
    attempt_count = 0

    def flaky_task():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise ConnectionError("Temporary DB timeout")
        return {"status": "recovered"}

    dag = PipelineDAG("retry_test")
    dag.add_task(PipelineTask(name="flaky", action=flaky_task, max_retries=2, retry_delay_seconds=0.01))

    results = dag.execute()
    assert results["flaky"].state == TaskState.SUCCESS
    assert results["flaky"].attempts == 2


def test_skipped_downstream_on_failure():
    def broken_task():
        raise RuntimeError("Fatal extraction crash")

    dag = PipelineDAG("skip_test")
    dag.add_task(PipelineTask(name="extract", action=broken_task, max_retries=0))
    dag.add_task(PipelineTask(name="load", action=lambda: {}, dependencies=["extract"]))

    results = dag.execute()
    assert results["extract"].state == TaskState.FAILED
    assert results["load"].state == TaskState.SKIPPED
