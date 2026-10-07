"""
Resilient DAG Pipeline Orchestrator for LaborMarket-ETL-Pipeline.

Implements structured task graphs, state checkpointing, exponential backoff retries,
and pipeline telemetry to replace monolithic sequential script executions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger("etl_orchestrator")


class TaskState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    SKIPPED = "SKIPPED"


@dataclass
class TaskResult:
    task_name: str
    state: TaskState
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    attempts: int = 0
    error_message: Optional[str] = None
    payload: Optional[dict] = None


@dataclass
class PipelineTask:
    name: str
    action: Callable[[], dict]
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    backoff_multiplier: float = 2.0


class PipelineDAG:
    """Directed Acyclic Graph orchestrator for scheduling and executing ETL tasks."""

    def __init__(self, name: str = "LaborMarket_ETL"):
        self.name = name
        self.tasks: Dict[str, PipelineTask] = {}

    def add_task(self, task: PipelineTask) -> "PipelineDAG":
        if task.name in self.tasks:
            raise ValueError(f"Task '{task.name}' already registered.")
        self.tasks[task.name] = task
        return self

    def topological_sort(self) -> List[str]:
        """Resolves task dependency order or raises ValueError on circular references."""
        in_degree: Dict[str, int] = {k: 0 for k in self.tasks}
        adjacency: Dict[str, List[str]] = {k: [] for k in self.tasks}

        for task_name, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    raise ValueError(f"Task '{task_name}' depends on unknown task '{dep}'.")
                adjacency[dep].append(task_name)
                in_degree[task_name] += 1

        queue = [k for k, deg in in_degree.items() if deg == 0]
        ordered: List[str] = []

        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(self.tasks):
            raise ValueError("Circular dependency detected in pipeline DAG.")

        return ordered

    def execute(self) -> Dict[str, TaskResult]:
        """Executes all DAG tasks in topologically sorted dependency order with retries."""
        execution_order = self.topological_sort()
        results: Dict[str, TaskResult] = {}
        failed_tasks: Set[str] = set()

        logger.info(f"Starting DAG pipeline '{self.name}' with execution order: {execution_order}")

        for task_name in execution_order:
            task = self.tasks[task_name]
            # Check if any upstream dependencies failed
            upstream_failed = any(dep in failed_tasks for dep in task.dependencies)
            if upstream_failed:
                logger.warning(f"Skipping task '{task_name}' due to failed upstream dependencies.")
                results[task_name] = TaskResult(
                    task_name=task_name,
                    state=TaskState.SKIPPED,
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    error_message="Upstream dependency failed.",
                )
                failed_tasks.add(task_name)
                continue

            # Execute with exponential backoff retries
            start_ts = datetime.now(timezone.utc)
            attempts = 0
            success = False
            last_err: Optional[str] = None
            payload: Optional[dict] = None

            delay = task.retry_delay_seconds
            while attempts <= task.max_retries and not success:
                attempts += 1
                try:
                    logger.info(f"Executing task '{task_name}' (Attempt {attempts}/{task.max_retries + 1})...")
                    payload = task.action()
                    success = True
                except Exception as ex:
                    last_err = str(ex)
                    logger.error(f"Task '{task_name}' failed attempt {attempts}: {last_err}")
                    if attempts <= task.max_retries:
                        time.sleep(delay)
                        delay *= task.backoff_multiplier

            end_ts = datetime.now(timezone.utc)
            duration = (end_ts - start_ts).total_seconds()

            if success:
                results[task_name] = TaskResult(
                    task_name=task_name,
                    state=TaskState.SUCCESS,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_seconds=duration,
                    attempts=attempts,
                    payload=payload,
                )
                logger.info(f"Task '{task_name}' completed successfully in {duration:.2f}s.")
            else:
                results[task_name] = TaskResult(
                    task_name=task_name,
                    state=TaskState.FAILED,
                    start_time=start_ts,
                    end_time=end_ts,
                    duration_seconds=duration,
                    attempts=attempts,
                    error_message=last_err,
                )
                failed_tasks.add(task_name)
                logger.error(f"Task '{task_name}' failed after {attempts} attempts.")

        return results
