from enum import Enum
from datetime import datetime

class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class TaskType(Enum):
    FOR_ME = "for_me"
    FOR_PARTNER = "for_partner"
    FOR_BOTH = "for_both"

class Task:
    def __init__(self, 
                 id: int = None,
                 title: str = "",
                 description: str = "",
                 task_type: TaskType = TaskType.FOR_ME,
                 status: TaskStatus = TaskStatus.ACTIVE,
                 created_by: int = None,
                 created_at: datetime = None):
        self.id = id
        self.title = title
        self.description = description
        self.task_type = task_type
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now()