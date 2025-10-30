# file: apps/drone-control/services/task_queue.py

import asyncio
from collections import deque
from typing import Dict, Any, Deque

class DroneTaskQueue:
    def __init__(self):
        self._tasks: Dict[str, Deque[Dict[str, Any]]] = {}

    def add_task(self, drone_id: str, task: Dict[str, Any]):
        if drone_id not in self._tasks:
            self._tasks[drone_id] = deque()
        self._tasks[drone_id].append(task)
        print(f"Task {task['command']} added for drone {drone_id}")

    def get_next_task(self, drone_id: str) -> Dict[str, Any] | None:
        if drone_id in self._tasks and self._tasks[drone_id]:
            return self._tasks[drone_id].popleft()
        return None

task_queue = DroneTaskQueue()
