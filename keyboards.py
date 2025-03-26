from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models import TaskType, TaskStatus

def get_main_keyboard() -> ReplyKeyboardMarkup:
    # Создаем основную клавиатуру для главного меню
    keyboard = [
        [KeyboardButton(text="🆕 Добавить задачу")],
        [KeyboardButton(text="📋 Мои задачи"), KeyboardButton(text="🔄 Задачи партнера")],
        [KeyboardButton(text="👫 Общие задачи")]
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

def get_task_action_keyboard(task_id: int, task_status: TaskStatus) -> InlineKeyboardMarkup:
    # Клавиатура для действий с задачей (просмотр, редактирование, удаление)
    builder = InlineKeyboardBuilder()
    
    # Кнопка для изменения статуса
    status_text = "✅ Отметить выполненным" if task_status == TaskStatus.ACTIVE else "🔄 Вернуть в активные"
    status_value = TaskStatus.COMPLETED.value if task_status == TaskStatus.ACTIVE else TaskStatus.ACTIVE.value
    
    # Добавляем кнопки в билдер
    builder.button(text=status_text, callback_data=f"task_status:{task_id}:{status_value}")
    builder.button(text="✏️ Редактировать", callback_data=f"edit_task:{task_id}")
    builder.button(text="🗑️ Удалить", callback_data=f"delete_task:{task_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_tasks")
    
    # Размещаем кнопки в один столбец
    builder.adjust(1)
    
    return builder.as_markup()

def get_tasks_list_keyboard(tasks, page=0, page_size=5) -> InlineKeyboardMarkup:
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
            callback_data=f"view_task:{task.id}"
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

def get_edit_menu_keyboard(task_id: int) -> InlineKeyboardMarkup:
    # Клавиатура для меню редактирования задачи
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 Название", callback_data="edit:title")
    builder.button(text="📝 Описание", callback_data="edit:description")
    builder.button(text="👥 Тип задачи", callback_data="edit:type")
    builder.button(text="🔙 Назад", callback_data=f"view_task:{task_id}")
    
    # Размещаем кнопки в один столбец
    builder.adjust(1)
    
    return builder.as_markup()