import sqlite3
from typing import List, Optional
from models import Task, TaskType, TaskStatus
from datetime import datetime
import json

class Database:
    def __init__(self, db_file: str = "couple_tasks.db"):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()
        
    def create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER
        )
        """)
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)
        self.connection.commit()
        
    def add_user(self, user_id: int, partner_id: int = None):
        self.cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, partner_id))
        self.connection.commit()
        
    def get_partner_id(self, user_id: int) -> Optional[int]:
        self.cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
        
    def add_task(self, task: Task) -> int:
        self.cursor.execute("""
        INSERT INTO tasks (title, description, task_type, status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (task.title, task.description, task.task_type.value, task.status.value, task.created_by, task.created_at))
        self.connection.commit()
        return self.cursor.lastrowid
        
    def get_tasks(self, user_id: int) -> List[Task]:
        partner_id = self.get_partner_id(user_id)
        
        # Получаем ВСЕ задачи, связанные с пользователем и партнёром
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE created_by = ? OR created_by = ?
        ORDER BY created_at DESC
        """, (user_id, partner_id or -1))  # Используем -1 если партнёра нет
        
        tasks = []
        for row in self.cursor.fetchall():
            task = Task(
                id=row[0],
                title=row[1],
                description=row[2],
                task_type=TaskType(row[3]),
                status=TaskStatus(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            tasks.append(task)
        
        return tasks
    
    def get_user_tasks(self, user_id: int) -> List[Task]:
        """Получает задачи, которые предназначены для пользователя"""
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            partner_id = -1  # Используем -1 если партнёра нет
        
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE (created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?) OR
            (task_type = ?)
        ORDER BY created_at DESC
        """, (user_id, TaskType.FOR_ME.value, 
            partner_id, TaskType.FOR_PARTNER.value, 
            TaskType.FOR_BOTH.value))
        
        tasks = []
        for row in self.cursor.fetchall():
            task = Task(
                id=row[0],
                title=row[1],
                description=row[2],
                task_type=TaskType(row[3]),
                status=TaskStatus(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            tasks.append(task)
        
        return tasks
    
    def get_partner_tasks(self, user_id: int) -> List[Task]:
        """Получает задачи, которые предназначены для партнёра"""
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            return []  # Если партнёра нет, то и задач для него нет
        
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE (created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?) 
        ORDER BY created_at DESC
        """, (user_id, TaskType.FOR_PARTNER.value, 
            partner_id, TaskType.FOR_ME.value))
        
        tasks = []
        for row in self.cursor.fetchall():
            task = Task(
                id=row[0],
                title=row[1],
                description=row[2],
                task_type=TaskType(row[3]),
                status=TaskStatus(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            tasks.append(task)
        
        return tasks
    
    def get_common_tasks(self, user_id: int) -> List[Task]:
        """Получает общие задачи"""
        partner_id = self.get_partner_id(user_id)
        
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE task_type = ? AND (created_by = ? OR created_by = ?)
        ORDER BY created_at DESC
        """, (TaskType.FOR_BOTH.value, user_id, partner_id or -1))
        
        tasks = []
        for row in self.cursor.fetchall():
            task = Task(
                id=row[0],
                title=row[1],
                description=row[2],
                task_type=TaskType(row[3]),
                status=TaskStatus(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            tasks.append(task)
        
        return tasks
        
    def get_task(self, task_id: int) -> Optional[Task]:
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE id = ?
        """, (task_id,))
        
        row = self.cursor.fetchone()
        if not row:
            return None
            
        return Task(
            id=row[0],
            title=row[1],
            description=row[2],
            task_type=TaskType(row[3]),
            status=TaskStatus(row[4]),
            created_by=row[5],
            created_at=datetime.fromisoformat(row[6])
        )
        
    def update_task(self, task: Task) -> bool:
        self.cursor.execute("""
        UPDATE tasks
        SET title = ?, description = ?, task_type = ?, status = ?
        WHERE id = ?
        """, (task.title, task.description, task.task_type.value, task.status.value, task.id))
        self.connection.commit()
        return self.cursor.rowcount > 0
        
    def delete_task(self, task_id: int) -> bool:
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()
        return self.cursor.rowcount > 0