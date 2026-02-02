#!/usr/bin/env python3
"""
Progress Tracker Utility for CAM Application
Tracks upload progress for Snowflake operations
"""

import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Track progress of long-running operations"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure single instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize progress tracker"""
        if self._initialized:
            return

        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._initialized = True

    def create_task(self, task_id: str, total_steps: int = 100,
                    description: str = "Processing") -> Dict[str, Any]:
        """
        Create a new progress tracking task

        Args:
            task_id: Unique identifier for the task
            total_steps: Total number of steps (default 100 for percentage)
            description: Task description

        Returns:
            Task information dictionary
        """
        with self._lock:
            task = {
                'task_id': task_id,
                'description': description,
                'total_steps': total_steps,
                'current_step': 0,
                'percentage': 0,
                'status': 'pending',  # pending, running, completed, failed
                'start_time': None,
                'end_time': None,
                'error': None,
                'result': None,
                'substep': None,
                'substep_percentage': 0
            }

            self._tasks[task_id] = task
            logger.info(f"Created progress task: {task_id}")

            return task.copy()

    def update_progress(self, task_id: str, current_step: int,
                       substep: Optional[str] = None,
                       substep_percentage: Optional[int] = None):
        """
        Update progress for a task

        Args:
            task_id: Task identifier
            current_step: Current step number
            substep: Optional substep description
            substep_percentage: Optional substep progress percentage
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return

            task = self._tasks[task_id]

            task['current_step'] = min(current_step, task['total_steps'])
            task['percentage'] = int((task['current_step'] / task['total_steps']) * 100)

            if substep:
                task['substep'] = substep
            if substep_percentage is not None:
                task['substep_percentage'] = substep_percentage

            # Set status to running if not already
            if task['status'] == 'pending':
                task['status'] = 'running'
                task['start_time'] = datetime.now().isoformat()

            logger.debug(f"Task {task_id} progress: {task['percentage']}%")

    def set_substep(self, task_id: str, substep: str, substep_percentage: int = 0):
        """
        Set current substep for a task

        Args:
            task_id: Task identifier
            substep: Substep description
            substep_percentage: Substep progress (0-100)
        """
        with self._lock:
            if task_id not in self._tasks:
                return

            task = self._tasks[task_id]
            task['substep'] = substep
            task['substep_percentage'] = substep_percentage

    def complete_task(self, task_id: str, result: Optional[Any] = None):
        """
        Mark task as completed

        Args:
            task_id: Task identifier
            result: Optional result data
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return

            task = self._tasks[task_id]
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            task['current_step'] = task['total_steps']
            task['percentage'] = 100
            task['result'] = result

            logger.info(f"Task {task_id} completed successfully")

    def fail_task(self, task_id: str, error: str):
        """
        Mark task as failed

        Args:
            task_id: Task identifier
            error: Error message
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return

            task = self._tasks[task_id]
            task['status'] = 'failed'
            task['end_time'] = datetime.now().isoformat()
            task['error'] = error

            logger.error(f"Task {task_id} failed: {error}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a task

        Args:
            task_id: Task identifier

        Returns:
            Task status dictionary or None if not found
        """
        with self._lock:
            if task_id not in self._tasks:
                return None

            return self._tasks[task_id].copy()

    def delete_task(self, task_id: str):
        """
        Delete a task from tracker

        Args:
            task_id: Task identifier
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                logger.info(f"Deleted task: {task_id}")

    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """
        Clean up old completed/failed tasks

        Args:
            max_age_seconds: Maximum age of tasks to keep (default 1 hour)
        """
        with self._lock:
            current_time = time.time()
            tasks_to_delete = []

            for task_id, task in self._tasks.items():
                if task['status'] in ['completed', 'failed'] and task['end_time']:
                    end_time = datetime.fromisoformat(task['end_time']).timestamp()
                    age = current_time - end_time

                    if age > max_age_seconds:
                        tasks_to_delete.append(task_id)

            for task_id in tasks_to_delete:
                del self._tasks[task_id]

            if tasks_to_delete:
                logger.info(f"Cleaned up {len(tasks_to_delete)} old tasks")

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tasks

        Returns:
            Dictionary of all tasks
        """
        with self._lock:
            return {task_id: task.copy() for task_id, task in self._tasks.items()}


# Global progress tracker instance
_progress_tracker = ProgressTracker()


def get_progress_tracker() -> ProgressTracker:
    """
    Get global progress tracker instance

    Returns:
        ProgressTracker instance
    """
    return _progress_tracker
