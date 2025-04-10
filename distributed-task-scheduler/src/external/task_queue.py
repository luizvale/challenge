import threading
from typing import List, Tuple, Dict, Optional

from ..core.entities.task import Task
from ..core.interfaces.task_queue import TaskQueue


class PriorityTaskQueue(TaskQueue):
    """Priority queue implementation with O(1) task removal."""

    def __init__(self):
        self.queue: List[Tuple[int, int, str, Task]] = []
        self.task_map: Dict[str, Task] = {}
        self.position_map: Dict[str, int] = {}
        self._counter = 0  # For tie-breaking tasks with same priority
        self._lock = threading.Lock()

    def enqueue(self, task: Task) -> None:
        """Add a task to the queue. O(log n)"""
        with self._lock:
            # Lower value = higher priority
            priority_value = -task.priority.value
            self._counter += 1

            # Add to queue
            entry = (priority_value, self._counter, task.id, task)
            self.queue.append(entry)
            position = len(self.queue) - 1
            self.position_map[task.id] = position

            # Maintain heap property
            self._sift_up(position)

            # Store the task in the map
            self.task_map[task.id] = task

    def dequeue(self) -> Optional[Task]:
        """Get the next task with highest priority. O(log n)"""
        with self._lock:
            if not self.queue:
                return None

            # Get the highest-priority task
            _, _, task_id, task = self.queue[0]

            # Remove from queue
            self._remove_at(0)

            # Remove from task map
            if task_id in self.task_map:
                del self.task_map[task_id]

            return task

    def remove(self, task_id: str) -> bool:
        """Remove a task from the queue. O(log n)"""
        with self._lock:
            if task_id not in self.position_map:
                return False

            # Find the task's position in the queue
            position = self.position_map[task_id]

            # Remove from queue
            self._remove_at(position)

            # Remove from task map
            if task_id in self.task_map:
                del self.task_map[task_id]

            return True

    def is_empty(self) -> bool:
        """Check if the queue is empty. O(1)"""
        with self._lock:
            return len(self.queue) == 0

    def _remove_at(self, index: int) -> None:
        """Remove item at the given index and maintain heap property. O(log n)"""
        # If it's the last item, just remove it
        if index == len(self.queue) - 1:
            task_id = self.queue[index][2]
            self.queue.pop()
            if task_id in self.position_map:
                del self.position_map[task_id]
            return

        # Replace with the last item
        last_item = self.queue.pop()
        last_task_id = last_item[2]

        # If the index was already the last, nothing else to do
        if index >= len(self.queue):
            if last_task_id in self.position_map:
                del self.position_map[last_task_id]
            return

        # Replace the item at index with the last item
        removed_task_id = self.queue[index][2]
        self.queue[index] = last_item

        # Update position map
        self.position_map[last_task_id] = index
        if removed_task_id in self.position_map:
            del self.position_map[removed_task_id]

        # Restore heap property — item may need to move up or down
        parent = (index - 1) // 2
        if index > 0 and self.queue[index][0] < self.queue[parent][0]:
            self._sift_up(index)
        else:
            self._sift_down(index)

    def _sift_up(self, index: int) -> None:
        """Move item up to maintain heap property. O(log n)"""
        item = self.queue[index]
        task_id = item[2]

        # Move item up while smaller than its parent
        while index > 0:
            parent = (index - 1) // 2
            if self.queue[parent][0] <= item[0]:
                break

            # Swap with parent
            self.queue[index] = self.queue[parent]
            self.position_map[self.queue[index][2]] = index
            index = parent

        # Place the item at the correct position
        self.queue[index] = item
        self.position_map[task_id] = index

    def _sift_down(self, index: int) -> None:
        """Move item down to maintain heap property. O(log n)"""
        item = self.queue[index]
        task_id = item[2]
        n = len(self.queue)

        # Move item down while it's larger than any of its children
        while index < n:
            smallest = index
            left = 2 * index + 1
            right = 2 * index + 2

            if left < n and self.queue[left][0] < self.queue[smallest][0]:
                smallest = left

            if right < n and self.queue[right][0] < self.queue[smallest][0]:
                smallest = right

            if smallest == index:
                break

            # Swap with smallest child
            self.queue[index] = self.queue[smallest]
            self.position_map[self.queue[index][2]] = index
            index = smallest

        # Place the item at the correct position
        self.queue[index] = item
        self.position_map[task_id] = index
