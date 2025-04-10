# external/task_executor.py
from typing import Any, Callable, Dict, Optional

from ..core.entities.task import Task
from ..core.interfaces.task_executor import TaskExecutor


class DefaultTaskExecutor(TaskExecutor):
    """Default implementation of TaskExecutor."""

    def __init__(self):
        self.handlers: Dict[str, Callable[[Task], Any]] = {}

    def execute(self, task: Task) -> Dict[str, Any]:
        handler = self.get_handler(task.name)

        if not handler:
            return {"success": False, "error": f"No handler registered for task type: {task.name}"}

        try:
            result = handler(task)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def register_handler(self, task_name: str, handler: Callable[[Task], Any]) -> None:
        self.handlers[task_name] = handler

    def get_handler(self, task_name: str) -> Optional[Callable[[Task], Any]]:
        return self.handlers.get(task_name)

