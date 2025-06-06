from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models import TaskType, TaskStatus, WishType

def get_main_keyboard() -> ReplyKeyboardMarkup:
    # Создаем основную клавиатуру для главного меню
    keyboard = [
        [KeyboardButton(text="🆕 Добавить задачу"), KeyboardButton(text="🎁 Добавить желание")],
        [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="🔄 Задачи партнера")],
        [KeyboardButton(text="👫 Общие задачи"), KeyboardButton(text="✅ Выполненные задачи")],
        [KeyboardButton(text="✨ Мои желания"), KeyboardButton(text="🎀 Желания партнёра")],
        [KeyboardButton(text="🎬 Фильмы")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_task_type_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для выбора типа задачи при создании
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки в билдер
    builder.button(text="🙋‍♂️ Для себя", callback_data=f"task_type:{TaskType.FOR_ME.value}")
    builder.button(text="👩‍❤️‍👨 Для партнера", callback_data=f"task_type:{TaskType.FOR_PARTNER.value}")
    builder.button(text="👫 Для обоих", callback_data=f"task_type:{TaskType.FOR_BOTH.value}")
    
    # Размещаем кнопки в один столбец
    builder.adjust(1)
    
    return builder.as_markup()

def get_task_action_keyboard(task_id: int, task_status: TaskStatus, context: str = "my_tasks") -> InlineKeyboardMarkup:
    # Клавиатура для действий с задачей (просмотр, редактирование, удаление)
    builder = InlineKeyboardBuilder()
    
    # Кнопка для изменения статуса
    status_text = "✅ Отметить выполненным" if task_status == TaskStatus.ACTIVE else "🔄 Вернуть в активные"
    status_value = TaskStatus.COMPLETED.value if task_status == TaskStatus.ACTIVE else TaskStatus.ACTIVE.value
    
    # Добавляем кнопки в билдер
    builder.button(text=status_text, callback_data=f"task_status:{task_id}:{status_value}")
    builder.button(text="✏️ Редактировать", callback_data=f"edit_task:{task_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"delete_task:{task_id}")
    builder.button(text="⬅️ Назад", callback_data=f"back_to_tasks:{context}")
    
    # Размещаем кнопки в один столбец
    builder.adjust(1)
    
    return builder.as_markup()

def get_tasks_list_keyboard(tasks, page=0, page_size=5, context="my_tasks") -> InlineKeyboardMarkup:
    # Пагинация для списка задач
    builder = InlineKeyboardBuilder()
    
    start = page * page_size
    end = min(start + page_size, len(tasks))
    
    # Добавляем кнопки для каждой задачи на текущей странице
    for i in range(start, end):
        task = tasks[i]
        status_emoji = "✅" if task.status == TaskStatus.COMPLETED else "🔄"
        # Обрезаем длинные названия задач
        title_display = task.title[:30] + "..." if len(task.title) > 30 else task.title
        builder.button(
            text=f"{status_emoji} {title_display}", 
            callback_data=f"view_task:{task.id}:{context}"
        )
    
    # Размещаем кнопки задач в один столбец
    builder.adjust(1)
    
    # Добавляем кнопки пагинации, если они нужны
    pagination_buttons = []
    
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"page:{page-1}")
    
    if end < len(tasks):
        builder.button(text="➡️ Вперед", callback_data=f"page:{page+1}")
    
    # Если есть кнопки пагинации, размещаем их в одну строку
    if page > 0 or end < len(tasks):
        # Здесь количество кнопок в последней добавленной строке - количество кнопок пагинации (1 или 2)
        builder.adjust(1, 2)  
    
    # Кнопка возврата в главное меню
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)  # Кнопка меню в отдельной строке
    
    return builder.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для отмены текущего действия
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()

def get_confirm_keyboard(action: str, task_id: int) -> InlineKeyboardMarkup:
    # Клавиатура для подтверждения действия
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"confirm_{action}:{task_id}")
    builder.button(text="❌ Нет", callback_data=f"view_task:{task_id}")
    
    # Размещаем кнопки в одну строку (2 кнопки)
    builder.adjust(2)
    
    return builder.as_markup()

def get_edit_menu_keyboard(task_id: int, context: str = "my_tasks") -> InlineKeyboardMarkup:
    # Клавиатура для меню редактирования задачи
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Название", callback_data="edit:title")
    builder.button(text="📝 Описание", callback_data="edit:description")
    builder.button(text="👥 Тип задачи", callback_data="edit:type")
    builder.button(text="🔙 Назад", callback_data=f"view_task:{task_id}:{context}")
    
    # Размещаем кнопки в один столбец
    builder.adjust(1)
    
    return builder.as_markup()

def get_wish_type_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для выбора типа желания при создании
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🎁 Моё желание", callback_data=f"wish_type:{WishType.MY_WISH.value}")
    builder.button(text="💝 Желание партнёра", callback_data=f"wish_type:{WishType.PARTNER_WISH.value}")
    
    builder.adjust(1)
    
    return builder.as_markup()

def get_wish_action_keyboard(wish_id: int, context: str = "my_wishes") -> InlineKeyboardMarkup:
    # Клавиатура для действий с желанием
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✏️ Редактировать", callback_data=f"edit_wish:{wish_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"delete_wish:{wish_id}")
    builder.button(text="⬅️ Назад", callback_data=f"back_to_wishes:{context}")
    
    builder.adjust(1)
    
    return builder.as_markup()

def get_wishes_list_keyboard(wishes, page=0, page_size=5, context="my_wishes") -> InlineKeyboardMarkup:
    # Пагинация для списка желаний
    builder = InlineKeyboardBuilder()
    
    start = page * page_size
    end = min(start + page_size, len(wishes))
    
    for i in range(start, end):
        wish = wishes[i]
        title_display = wish.title[:30] + "..." if len(wish.title) > 30 else wish.title
        builder.button(
            text=f"🎁 {title_display}", 
            callback_data=f"view_wish:{wish.id}:{context}"
        )
    
    builder.adjust(1)
    
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"wish_page:{page-1}")
    
    if end < len(wishes):
        builder.button(text="➡️ Вперед", callback_data=f"wish_page:{page+1}")
    
    if page > 0 or end < len(wishes):
        builder.adjust(1, 2)
    
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()

def get_edit_wish_menu_keyboard(wish_id: int, context: str = "my_wishes") -> InlineKeyboardMarkup:
    # Клавиатура для меню редактирования желания
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Название", callback_data="edit_wish:title")
    builder.button(text="📝 Описание", callback_data="edit_wish:description")
    builder.button(text="🖼️ Изображение", callback_data="edit_wish:image")
    builder.button(text="👥 Тип желания", callback_data="edit_wish:type")
    builder.button(text="🔙 Назад", callback_data=f"view_wish:{wish_id}:{context}")
    
    builder.adjust(1)
    
    return builder.as_markup()

def get_movies_menu_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для меню фильмов
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🎥 Мои фильмы", callback_data="movies:my")
    builder.button(text="🎬 Фильмы партнёра", callback_data="movies:partner")
    builder.button(text="➕ Добавить фильм", callback_data="movies:add")
    builder.button(text="📊 Статистика", callback_data="movies:stats")
    builder.button(text="🎯 Рекомендации", callback_data="movies:recommendations")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    builder.adjust(1)
    return builder.as_markup()

def get_movie_type_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для выбора типа фильма при создании
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🎥 Мои фильмы", callback_data="movie_type:my_movies")
    builder.button(text="🎬 Фильмы партнёра", callback_data="movie_type:partner_movies")
    
    builder.adjust(1)
    return builder.as_markup()

def get_movie_action_keyboard(movie_id: int, context: str = "my_movies", watched: bool = False) -> InlineKeyboardMarkup:
    # Клавиатура для действий с фильмом
    builder = InlineKeyboardBuilder()
    
    if context == "partner_movies":
        if not watched:
            builder.button(text="⭐ Оценить", callback_data=f"rate_movie:{movie_id}")
            builder.button(text="✅ Отметить как просмотренный", callback_data=f"mark_watched:{movie_id}")
        else:
            builder.button(text="📝 Оставить отзыв", callback_data=f"add_review:{movie_id}")
    else:
        if not watched:
            builder.button(text="✅ Отметить как просмотренный", callback_data=f"mark_watched:{movie_id}")
        builder.button(text="✏️ Редактировать", callback_data=f"edit_movie:{movie_id}")
        builder.button(text="🗑️ Удалить", callback_data=f"delete_movie:{movie_id}")
    
    builder.button(text="⬅️ Назад", callback_data=f"back_to_movies:{context}")
    
    builder.adjust(1)
    return builder.as_markup()

def get_movie_rating_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    # Клавиатура для оценки фильма
    builder = InlineKeyboardBuilder()
    
    for i in range(1, 6):
        builder.button(text=f"{'⭐' * i}", callback_data=f"set_rating:{movie_id}:{i}")
    
    builder.button(text="⬅️ Назад", callback_data=f"view_movie:{movie_id}:partner_movies")
    
    builder.adjust(5, 1)
    return builder.as_markup()

def get_movies_list_keyboard(movies, page=0, page_size=5, context="my_movies") -> InlineKeyboardMarkup:
    # Пагинация для списка фильмов
    builder = InlineKeyboardBuilder()
    
    start = page * page_size
    end = min(start + page_size, len(movies))
    
    for i in range(start, end):
        movie = movies[i]
        title_display = movie['title'][:30] + "..." if len(movie['title']) > 30 else movie['title']
        watched_status = "✅ " if movie.get('watched', False) else ""
        builder.button(
            text=f"{watched_status}🎬 {title_display}", 
            callback_data=f"view_movie:{movie['id']}:{context}"
        )
    
    builder.adjust(1)
    
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"movie_page:{page-1}")
    
    if end < len(movies):
        builder.button(text="➡️ Вперед", callback_data=f"movie_page:{page+1}")
    
    if page > 0 or end < len(movies):
        builder.adjust(1, 2)
    
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    
    return builder.as_markup()

def get_edit_movie_menu_keyboard(movie_id: int, context: str = "my_movies") -> InlineKeyboardMarkup:
    # Клавиатура для меню редактирования фильма
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Название", callback_data="edit_movie:title")
    builder.button(text="📝 Описание", callback_data="edit_movie:description")
    builder.button(text="🔙 Назад", callback_data=f"view_movie:{movie_id}:{context}")
    
    builder.adjust(1)
    return builder.as_markup()