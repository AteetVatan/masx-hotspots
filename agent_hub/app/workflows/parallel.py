# ┌───────────────────────────────────────────────────────────────┐
# │  Copyright (c) 2025 Ateet Vatan Bahmani                      │
# │  Project: MASX AI – Strategic Agentic AI System              │
# │  All rights reserved.                                        │
# └───────────────────────────────────────────────────────────────┘
#
# MASX AI is a proprietary software system developed and owned by Ateet Vatan Bahmani.
# The source code, documentation, workflows, designs, and naming (including "MASX AI")
# are protected by applicable copyright and trademark laws.
#
# Redistribution, modification, commercial use, or publication of any portion of this
# project without explicit written consent is strictly prohibited.
#
# This project is not open-source and is intended solely for internal, research,
# or demonstration use by the author.
#
# Contact: ab@masxai.com | MASXAI.com

"""
Parallel execution utilities for MASX-HOTSPOTS Agentic AI System.

Provides utilities for parallel task execution in workflows:
- Async task execution with proper coordination
- Result aggregation and error handling
- Performance monitoring and optimization
- Resource management and throttling

Usage: from app.workflows.parallel import execute_parallel_tasks, ParallelTaskExecutor
    results = await execute_parallel_tasks(tasks)
    executor = ParallelTaskExecutor(max_concurrent=5)
    results = await executor.execute(tasks)
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from ..core.exceptions import WorkflowException
from ..core.utils import measure_execution_time
from ..config.logging_config import get_workflow_logger


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ParallelTask:
    """Represents a task for parallel execution."""

    id: str
    func: Callable
    args: tuple = ()
    kwargs: dict = None
    timeout: Optional[float] = None
    retries: int = 0
    priority: int = 0

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


@dataclass
class TaskResult:
    """Result of a parallel task execution."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


class ParallelTaskExecutor:
    """
    Executor for parallel task execution with resource management.

    Features:
    - Configurable concurrency limits
    - Task prioritization
    - Automatic retries with backoff
    - Resource monitoring
    - Error handling and recovery
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_retries: int = 3,
        timeout: Optional[float] = 300.0,
        enable_monitoring: bool = True,
    ):
        """
        Initialize the parallel task executor.

        Args:
            max_concurrent: Maximum number of concurrent tasks
            max_retries: Maximum number of retries per task
            timeout: Default timeout for tasks (seconds)
            enable_monitoring: Enable performance monitoring
        """
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.default_timeout = timeout
        self.enable_monitoring = enable_monitoring
        self.logger = get_workflow_logger("ParallelExecutor")

        # Performance tracking
        self.total_tasks_executed = 0
        self.total_execution_time = 0.0
        self.failed_tasks = 0
        self.retry_count = 0

        # Resource management
        # limits the number of concurrent tasks accessing a shared resource.
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_tasks = set()

    async def execute(self, tasks: List[ParallelTask]) -> List[TaskResult]:
        """
        Execute tasks in parallel.

        Args:
            tasks: List of tasks to execute

        Returns:
            List of task results
        """
        if not tasks:
            return []

        self.logger.info(
            f"Starting parallel execution of {len(tasks)} tasks",
            max_concurrent=self.max_concurrent,
        )

        start_time = time.time()
        results = []

        try:
            # Sort tasks by priority (higher priority first)
            sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)

            # Execute tasks with concurrency control
            task_futures = []
            for task in sorted_tasks:
                future = asyncio.create_task(self._execute_single_task(task))
                task_futures.append(future)

            # Wait for all tasks to complete
            task_results = await asyncio.gather(*task_futures, return_exceptions=True)

            # Process results
            for i, result in enumerate(task_results):
                if isinstance(result, Exception):
                    # Handle unexpected exceptions
                    task_id = (
                        sorted_tasks[i].id if i < len(sorted_tasks) else f"unknown_{i}"
                    )
                    results.append(
                        TaskResult(
                            task_id=task_id,
                            status=TaskStatus.FAILED,
                            error=str(result),
                            execution_time=0.0,
                        )
                    )
                    self.failed_tasks += 1
                else:
                    results.append(result)

            # Update performance metrics
            execution_time = time.time() - start_time
            self.total_tasks_executed += len(tasks)
            self.total_execution_time += execution_time

            self.logger.info(
                f"Parallel execution completed",
                total_tasks=len(tasks),
                successful=len(
                    [r for r in results if r.status == TaskStatus.COMPLETED]
                ),
                failed=len([r for r in results if r.status == TaskStatus.FAILED]),
                execution_time=execution_time,
            )

        except Exception as e:
            self.logger.error(f"Parallel execution failed: {e}")
            raise WorkflowException(f"Parallel execution failed: {str(e)}")

        return results

    async def _execute_single_task(self, task: ParallelTask) -> TaskResult:
        """
        Execute a single task with retry logic.

        Args:
            task: Task to execute

        Returns:
            TaskResult: Result of task execution
        """
        async with self._semaphore:
            self._active_tasks.add(task.id)

            try:
                start_time = time.time()
                retry_count = 0

                while retry_count <= task.retries:
                    try:
                        # Execute task with timeout
                        timeout = task.timeout or self.default_timeout
                        if timeout:
                            result = await asyncio.wait_for(
                                self._run_task(task), timeout=timeout
                            )
                        else:
                            result = await self._run_task(task)

                        execution_time = time.time() - start_time

                        return TaskResult(
                            task_id=task.id,
                            status=TaskStatus.COMPLETED,
                            result=result,
                            execution_time=execution_time,
                            retry_count=retry_count,
                        )

                    except asyncio.TimeoutError:
                        retry_count += 1
                        self.retry_count += 1

                        if retry_count <= task.retries:
                            self.logger.warning(
                                f"Task {task.id} timed out, retrying ({retry_count}/{task.retries})"
                            )
                            await asyncio.sleep(2**retry_count)  # Exponential backoff
                        else:
                            execution_time = time.time() - start_time
                            return TaskResult(
                                task_id=task.id,
                                status=TaskStatus.FAILED,
                                error="Task timed out after all retries",
                                execution_time=execution_time,
                                retry_count=retry_count,
                            )

                    except Exception as e:
                        retry_count += 1
                        self.retry_count += 1

                        if retry_count <= task.retries:
                            self.logger.warning(
                                f"Task {task.id} failed, retrying ({retry_count}/{task.retries}): {e}"
                            )
                            await asyncio.sleep(2**retry_count)  # Exponential backoff
                        else:
                            execution_time = time.time() - start_time
                            return TaskResult(
                                task_id=task.id,
                                status=TaskStatus.FAILED,
                                error=str(e),
                                execution_time=execution_time,
                                retry_count=retry_count,
                            )

            finally:
                self._active_tasks.discard(task.id)

    async def _run_task(self, task: ParallelTask) -> Any:
        """
        Run a single task.

        Args:
            task: Task to run

        Returns:
            Task result
        """
        # Check if function is async
        if asyncio.iscoroutinefunction(task.func):
            return await task.func(*task.args, **task.kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(
                    executor, task.func, *task.args, **task.kwargs
                )

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        avg_execution_time = (
            self.total_execution_time / self.total_tasks_executed
            if self.total_tasks_executed > 0
            else 0.0
        )

        success_rate = (
            (self.total_tasks_executed - self.failed_tasks) / self.total_tasks_executed
            if self.total_tasks_executed > 0
            else 0.0
        )

        return {
            "total_tasks_executed": self.total_tasks_executed,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_execution_time,
            "failed_tasks": self.failed_tasks,
            "success_rate": success_rate,
            "retry_count": self.retry_count,
            "active_tasks": len(self._active_tasks),
            "max_concurrent": self.max_concurrent,
        }


async def execute_parallel_tasks(
    tasks: List[ParallelTask], max_concurrent: int = 10, timeout: Optional[float] = None
) -> List[TaskResult]:
    """
    Execute tasks in parallel with a simple interface.

    Args:
        tasks: List of tasks to execute
        max_concurrent: Maximum number of concurrent tasks
        timeout: Timeout for all tasks

    Returns:
        List of task results
    """
    executor = ParallelTaskExecutor(max_concurrent=max_concurrent, timeout=timeout)
    return await executor.execute(tasks)


def create_task(
    task_id: str,
    func: Callable,
    *args,
    timeout: Optional[float] = None,
    retries: int = 0,
    priority: int = 0,
    **kwargs,
) -> ParallelTask:
    """
    Create a parallel task.

    Args:
        task_id: Unique identifier for the task
        func: Function to execute
        *args: Positional arguments for the function
        timeout: Task timeout
        retries: Number of retries
        priority: Task priority (higher = more important)
        **kwargs: Keyword arguments for the function

    Returns:
        ParallelTask: Configured task
    """
    return ParallelTask(
        id=task_id,
        func=func,
        args=args,
        kwargs=kwargs,
        timeout=timeout,
        retries=retries,
        priority=priority,
    )


class TaskCoordinator:
    """
    Coordinates complex parallel task workflows.

    Features:
    - Task dependencies and ordering
    - Conditional task execution
    - Result aggregation and transformation
    - Workflow monitoring and control
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize the task coordinator.

        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.executor = ParallelTaskExecutor(max_concurrent=max_concurrent)
        self.logger = get_workflow_logger("TaskCoordinator")
        self._task_dependencies = {}
        self._task_results = {}

    def add_task_dependency(self, task_id: str, depends_on: List[str]):
        """
        Add dependency for a task.

        Args:
            task_id: ID of the dependent task
            depends_on: List of task IDs this task depends on
        """
        self._task_dependencies[task_id] = depends_on

    async def execute_with_dependencies(
        self,
        tasks: List[ParallelTask],
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, TaskResult]:
        """
        Execute tasks respecting dependencies.

        Args:
            tasks: List of tasks to execute
            dependencies: Task dependencies

        Returns:
            Dictionary mapping task IDs to results
        """
        if dependencies:
            for task_id, deps in dependencies.items():
                self.add_task_dependency(task_id, deps)

        # Group tasks by execution phase
        execution_phases = self._create_execution_phases(tasks)

        all_results = {}

        for phase_num, phase_tasks in enumerate(execution_phases):
            self.logger.info(
                f"Executing phase {phase_num + 1} with {len(phase_tasks)} tasks"
            )

            # Execute tasks in this phase
            phase_results = await self.executor.execute(phase_tasks)

            # Store results
            for result in phase_results:
                all_results[result.task_id] = result
                self._task_results[result.task_id] = result

            # Check for failures
            failed_tasks = [r for r in phase_results if r.status == TaskStatus.FAILED]
            if failed_tasks:
                self.logger.error(
                    f"Phase {phase_num + 1} had {len(failed_tasks)} failed tasks"
                )
                # Could implement failure handling strategy here

        return all_results

    def _create_execution_phases(
        self, tasks: List[ParallelTask]
    ) -> List[List[ParallelTask]]:
        """
        Create execution phases based on dependencies.

        Args:
            tasks: List of all tasks

        Returns:
            List of task phases
        """
        task_dict = {task.id: task for task in tasks}
        phases = []
        completed_tasks = set()

        while task_dict:
            # Find tasks that can be executed (all dependencies satisfied)
            executable_tasks = []

            for task_id, task in task_dict.items():
                dependencies = self._task_dependencies.get(task_id, [])
                if all(dep in completed_tasks for dep in dependencies):
                    executable_tasks.append(task)

            if not executable_tasks:
                # Circular dependency or missing tasks
                remaining_tasks = list(task_dict.keys())
                self.logger.warning(
                    f"Unable to resolve dependencies for tasks: {remaining_tasks}"
                )
                # Execute remaining tasks in a single phase
                phases.append(list(task_dict.values()))
                break

            # Add phase and mark tasks as completed
            phases.append(executable_tasks)
            for task in executable_tasks:
                completed_tasks.add(task.id)
                del task_dict[task.id]

        return phases

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get result for a specific task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResult or None if not found
        """
        return self._task_results.get(task_id)

    def get_failed_tasks(self) -> List[TaskResult]:
        """
        Get list of failed tasks.

        Returns:
            List of failed task results
        """
        return [
            result
            for result in self._task_results.values()
            if result.status == TaskStatus.FAILED
        ]


# Utility functions for common parallel operations
async def execute_agent_tasks(
    agents: List[Any], input_data: Dict[str, Any], max_concurrent: int = 5
) -> Dict[str, Any]:
    """
    Execute multiple agents in parallel.

    Args:
        agents: List of agent instances
        input_data: Input data for agents
        max_concurrent: Maximum concurrent agents

    Returns:
        Dictionary mapping agent names to results
    """
    tasks = []

    for agent in agents:
        task = create_task(
            task_id=agent.name,
            func=agent.run,
            input_data=input_data,
            timeout=300.0,
            retries=1,
        )
        tasks.append(task)

    results = await execute_parallel_tasks(tasks, max_concurrent=max_concurrent)

    # Convert to dictionary
    return {
        result.task_id: result.result
        for result in results
        if result.status == TaskStatus.COMPLETED
    }


async def execute_data_fetching_tasks(
    fetchers: List[Any], queries: List[str], max_concurrent: int = 3
) -> Dict[str, List[Any]]:
    """
    Execute data fetching tasks in parallel.

    Args:
        fetchers: List of data fetcher instances
        queries: List of queries to execute
        max_concurrent: Maximum concurrent fetchers

    Returns:
        Dictionary mapping fetcher names to fetched data
    """
    tasks = []

    for fetcher in fetchers:
        task = create_task(
            task_id=fetcher.name,
            func=fetcher.fetch,
            queries=queries,
            timeout=600.0,  # Longer timeout for data fetching
            retries=2,
        )
        tasks.append(task)

    results = await execute_parallel_tasks(tasks, max_concurrent=max_concurrent)

    # Aggregate results
    fetched_data = {}
    for result in results:
        if result.status == TaskStatus.COMPLETED and result.result:
            fetched_data[result.task_id] = result.result

    return fetched_data
