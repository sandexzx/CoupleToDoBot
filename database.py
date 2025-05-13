import sqlite3
from typing import List, Optional
from models import Task, TaskType, TaskStatus, Wish, WishType
from datetime import datetime
import json
import logging

class Database:
    def __init__(self, db_file: str = "couple_tasks.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
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

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            image_id TEXT,
            wish_type TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            movie_type TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            rating INTEGER,
            created_at TIMESTAMP NOT NULL,
            watched BOOLEAN DEFAULT 0,
            watch_date TIMESTAMP,
            review TEXT,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
        """)
        self.conn.commit()
        
    def add_user(self, user_id: int, partner_id: int = None):
        self.cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, partner_id))
        self.conn.commit()
        
    def get_partner_id(self, user_id: int) -> Optional[int]:
        self.cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
        
    def add_task(self, task: Task) -> int:
        self.cursor.execute("""
        INSERT INTO tasks (title, description, task_type, status, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (task.title, task.description, task.task_type.value, task.status.value, task.created_by, task.created_at))
        self.conn.commit()
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
        WHERE ((created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?) OR
            (task_type = ? AND (created_by = ? OR created_by = ?)))
        AND status = ?
        ORDER BY created_at DESC
        """, (user_id, TaskType.FOR_ME.value, 
            partner_id, TaskType.FOR_PARTNER.value, 
            TaskType.FOR_BOTH.value, user_id, partner_id,
            TaskStatus.ACTIVE.value))

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
        WHERE ((created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?))
        AND status = ?
        ORDER BY created_at DESC
        """, (user_id, TaskType.FOR_PARTNER.value, 
            partner_id, TaskType.FOR_ME.value,
            TaskStatus.ACTIVE.value))
        
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
        AND status = ?
        ORDER BY created_at DESC
        """, (TaskType.FOR_BOTH.value, user_id, partner_id or -1,
            TaskStatus.ACTIVE.value))
        
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
        self.conn.commit()
        return self.cursor.rowcount > 0
        
    def delete_task(self, task_id: int) -> bool:
        self.cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def add_wish(self, wish: Wish) -> int:
        self.cursor.execute("""
        INSERT INTO wishes (title, description, image_id, wish_type, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (wish.title, wish.description, wish.image_id, wish.wish_type.value, wish.created_by, wish.created_at))
        self.conn.commit()
        return self.cursor.lastrowid
        
    def get_wishes(self, user_id: int) -> List[Wish]:
        partner_id = self.get_partner_id(user_id)
        
        self.cursor.execute("""
        SELECT id, title, description, image_id, wish_type, created_by, created_at
        FROM wishes
        WHERE created_by = ? OR created_by = ?
        ORDER BY created_at DESC
        """, (user_id, partner_id or -1))
        
        wishes = []
        for row in self.cursor.fetchall():
            wish = Wish(
                id=row[0],
                title=row[1],
                description=row[2],
                image_id=row[3],
                wish_type=WishType(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            wishes.append(wish)
        
        return wishes
        
    def get_my_wishes(self, user_id: int) -> List[Wish]:
        self.cursor.execute("""
        SELECT id, title, description, image_id, wish_type, created_by, created_at
        FROM wishes
        WHERE created_by = ? AND wish_type = ?
        ORDER BY created_at DESC
        """, (user_id, WishType.MY_WISH.value))
        
        wishes = []
        for row in self.cursor.fetchall():
            wish = Wish(
                id=row[0],
                title=row[1],
                description=row[2],
                image_id=row[3],
                wish_type=WishType(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            wishes.append(wish)
        
        return wishes
        
    def get_partner_wishes(self, user_id: int) -> List[Wish]:
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            return []
        
        self.cursor.execute("""
        SELECT id, title, description, image_id, wish_type, created_by, created_at
        FROM wishes
        WHERE created_by = ? AND wish_type = ?
        ORDER BY created_at DESC
        """, (partner_id, WishType.MY_WISH.value))
        
        wishes = []
        for row in self.cursor.fetchall():
            wish = Wish(
                id=row[0],
                title=row[1],
                description=row[2],
                image_id=row[3],
                wish_type=WishType(row[4]),
                created_by=row[5],
                created_at=datetime.fromisoformat(row[6])
            )
            wishes.append(wish)
        
        return wishes
        
    def get_wish(self, wish_id: int) -> Optional[Wish]:
        self.cursor.execute("""
        SELECT id, title, description, image_id, wish_type, created_by, created_at
        FROM wishes
        WHERE id = ?
        """, (wish_id,))
        
        row = self.cursor.fetchone()
        if not row:
            return None
            
        return Wish(
            id=row[0],
            title=row[1],
            description=row[2],
            image_id=row[3],
            wish_type=WishType(row[4]),
            created_by=row[5],
            created_at=datetime.fromisoformat(row[6])
        )
        
    def update_wish(self, wish: Wish) -> bool:
        self.cursor.execute("""
        UPDATE wishes
        SET title = ?, description = ?, image_id = ?, wish_type = ?
        WHERE id = ?
        """, (wish.title, wish.description, wish.image_id, wish.wish_type.value, wish.id))
        self.conn.commit()
        return self.cursor.rowcount > 0
        
    def delete_wish(self, wish_id: int) -> bool:
        self.cursor.execute("DELETE FROM wishes WHERE id = ?", (wish_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_completed_tasks(self, user_id: int) -> List[Task]:
        """Получает выполненные задачи пользователя"""
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            partner_id = -1  # Используем -1 если партнёра нет
        
        self.cursor.execute("""
        SELECT id, title, description, task_type, status, created_by, created_at
        FROM tasks
        WHERE ((created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?) OR
            (task_type = ? AND (created_by = ? OR created_by = ?)) OR
            (created_by = ? AND task_type = ?) OR
            (created_by = ? AND task_type = ?))
        AND status = ?
        ORDER BY created_at DESC
        """, (user_id, TaskType.FOR_ME.value, 
            partner_id, TaskType.FOR_PARTNER.value, 
            TaskType.FOR_BOTH.value, user_id, partner_id,
            user_id, TaskType.FOR_PARTNER.value,
            partner_id, TaskType.FOR_ME.value,
            TaskStatus.COMPLETED.value))
        
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

    def add_movie(self, title: str, description: str, movie_type: str, created_by: int) -> int:
        self.cursor.execute("""
        INSERT INTO movies (title, description, movie_type, created_by, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (title, description, movie_type, created_by, datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_my_movies(self, user_id: int) -> List[dict]:
        self.cursor.execute("""
        SELECT id, title, description, movie_type, rating, created_at, watched, watch_date, review
        FROM movies
        WHERE created_by = ? AND movie_type = 'my_movies'
        ORDER BY created_at DESC
        """, (user_id,))
        
        movies = []
        for row in self.cursor.fetchall():
            movies.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'movie_type': row[3],
                'rating': row[4],
                'created_at': datetime.fromisoformat(row[5]),
                'watched': bool(row[6]),
                'watch_date': datetime.fromisoformat(row[7]) if row[7] else None,
                'review': row[8]
            })
        return movies

    def get_partner_movies(self, user_id: int) -> List[dict]:
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            return []
            
        self.cursor.execute("""
        SELECT id, title, description, movie_type, rating, created_at, watched, watch_date, review
        FROM movies
        WHERE created_by = ?
        ORDER BY created_at DESC
        """, (partner_id,))
        
        movies = []
        for row in self.cursor.fetchall():
            movies.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'movie_type': row[3],
                'rating': row[4],
                'created_at': datetime.fromisoformat(row[5]),
                'watched': bool(row[6]),
                'watch_date': datetime.fromisoformat(row[7]) if row[7] else None,
                'review': row[8]
            })
        return movies

    def get_movie(self, movie_id: int) -> Optional[dict]:
        self.cursor.execute("""
        SELECT id, title, description, movie_type, created_by, rating, created_at
        FROM movies
        WHERE id = ?
        """, (movie_id,))
        
        row = self.cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'movie_type': row[3],
            'created_by': row[4],
            'rating': row[5],
            'created_at': datetime.fromisoformat(row[6])
        }

    def update_movie(self, movie_id: int, title: str, description: str) -> bool:
        try:
            self.cursor.execute("""
            UPDATE movies
            SET title = ?, description = ?
            WHERE id = ?
            """, (title, description, movie_id))
            self.conn.commit()
            return True
        except:
            return False

    def delete_movie(self, movie_id: int) -> bool:
        try:
            self.cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            self.conn.commit()
            return True
        except:
            return False

    def update_movie_rating(self, movie_id: int, rating: int) -> bool:
        try:
            self.cursor.execute("""
            UPDATE movies
            SET rating = ?
            WHERE id = ?
            """, (rating, movie_id))
            self.conn.commit()
            return True
        except:
            return False

    def update_movie_watch_status(self, movie_id: int, watched: bool, watch_date: datetime = None, review: str = None) -> bool:
        try:
            self.cursor.execute("""
            UPDATE movies
            SET watched = ?, watch_date = ?, review = ?
            WHERE id = ?
            """, (watched, watch_date.isoformat() if watch_date else None, review, movie_id))
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating movie watch status: {e}")
            return False

    def get_movie_stats(self, user_id: int) -> dict:
        self.cursor.execute("""
        SELECT 
            COUNT(*) as total_movies,
            SUM(CASE WHEN watched = 1 THEN 1 ELSE 0 END) as watched_movies,
            AVG(CASE WHEN rating IS NOT NULL THEN rating ELSE NULL END) as avg_rating
        FROM movies
        WHERE created_by = ?
        """, (user_id,))
        
        row = self.cursor.fetchone()
        return {
            'total_movies': row[0],
            'watched_movies': row[1],
            'avg_rating': round(row[2], 1) if row[2] is not None else None
        }

    def get_movie_recommendations(self, user_id: int, limit: int = 5) -> List[dict]:
        # Получаем средний рейтинг пользователя
        self.cursor.execute("""
        SELECT AVG(rating)
        FROM movies
        WHERE created_by = ? AND rating IS NOT NULL
        """, (user_id,))
        avg_rating = self.cursor.fetchone()[0] or 4  # По умолчанию 4, если нет оценок
        
        # Получаем рекомендации на основе оценок партнера
        partner_id = self.get_partner_id(user_id)
        if not partner_id:
            return []
            
        self.cursor.execute("""
        SELECT id, title, description, rating
        FROM movies
        WHERE created_by = ? 
        AND movie_type = 'partner_movies'
        AND watched = 0
        AND rating >= ?
        ORDER BY rating DESC, created_at DESC
        LIMIT ?
        """, (partner_id, avg_rating, limit))
        
        recommendations = []
        for row in self.cursor.fetchall():
            recommendations.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'rating': row[3]
            })
        return recommendations