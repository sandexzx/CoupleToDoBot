from enum import Enum
from datetime import datetime

class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class TaskType(Enum):
    FOR_ME = "for_me"
    FOR_PARTNER = "for_partner"
    FOR_BOTH = "for_both"

class WishType(Enum):
    MY_WISH = "my_wish"
    PARTNER_WISH = "partner_wish" 

class MovieType(Enum):
    MY_MOVIES = "my_movies"
    PARTNER_MOVIES = "partner_movies"

class Movie:
    def __init__(self, 
                 id: int = None,
                 title: str = "",
                 description: str = "",
                 movie_type: MovieType = MovieType.MY_MOVIES,
                 created_by: int = None,
                 rating: int = None,
                 created_at: datetime = None,
                 watched: bool = False,
                 watch_date: datetime = None,
                 review: str = None):
        self.id = id
        self.title = title
        self.description = description
        self.movie_type = movie_type
        self.created_by = created_by
        self.rating = rating
        self.created_at = created_at or datetime.now()
        self.watched = watched
        self.watch_date = watch_date
        self.review = review

class Wish:
    def __init__(self, 
                 id: int = None,
                 title: str = "",
                 description: str = "",
                 image_id: str = None,
                 wish_type: WishType = WishType.MY_WISH,
                 created_by: int = None,
                 created_at: datetime = None):
        self.id = id
        self.title = title
        self.description = description
        self.image_id = image_id
        self.wish_type = wish_type
        self.created_by = created_by
        self.created_at = created_at or datetime.now()

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