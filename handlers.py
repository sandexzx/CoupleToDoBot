import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from models import Task, TaskType, TaskStatus
from database import Database
from keyboards import (
    get_edit_menu_keyboard, get_main_keyboard, get_task_type_keyboard, get_task_action_keyboard,
    get_tasks_list_keyboard, get_cancel_keyboard, get_confirm_keyboard
)

router = Router()
db = Database()

# Состояния для FSM (машины состояний)
class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_type = State()
    
    edit_title = State()
    edit_description = State()
    edit_type = State()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    # Проверка, является ли пользователь одним из админов
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("😿 Извините, но этот бот только для определенных пользователей")
        return
    
    # Добавляем пользователя в базу данных
    user_id = message.from_user.id
    partner_id = None
    
    # Если пользователь уже есть в базе, получаем его партнера
    existing_partner = db.get_partner_id(user_id)
    if existing_partner:
        partner_id = existing_partner
    else:
        # Если пользователь первый из пары, то для него партнер - это второй админ
        for admin_id in ADMIN_IDS:
            if admin_id != user_id:
                partner_id = admin_id
                break
    
    # Добавляем пользователя с партнером
    db.add_user(user_id, partner_id)
    
    # Важно! Также добавляем обратную связь - чтобы партнер тоже видел пользователя
    if partner_id:
        db.add_user(partner_id, user_id)
    
    # Отправляем приветственное сообщение
    await message.answer(
        f"👋 Привет! Это бот для управления задачами для пары."
        f"Вы можете создавать задачи для себя, для партнера или для обоих!",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "Добавить задачу"
@router.message(F.text == "🆕 Добавить задачу")
async def add_task(message: Message, state: FSMContext):
    await message.answer(
        "✏️ Введите название задачи:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TaskStates.waiting_for_title)

# Обработчик ввода названия задачи
@router.message(TaskStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    # Сохраняем название задачи
    await state.update_data(title=message.text)
    
    await message.answer(
        "📝 Введите описание задачи (или отправьте '-' для пропуска):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TaskStates.waiting_for_description)

# Обработчик ввода описания задачи
@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    description = message.text
    if description == "-":
        description = ""
    
    # Сохраняем описание задачи
    await state.update_data(description=description)
    
    await message.answer(
        "👥 Выберите тип задачи:",
        reply_markup=get_task_type_keyboard()
    )
    await state.set_state(TaskStates.waiting_for_type)

# Обработчик выбора типа задачи
@router.callback_query(TaskStates.waiting_for_type, F.data.startswith("task_type:"))
async def process_task_type(callback: CallbackQuery, state: FSMContext):
    task_type = callback.data.split(":")[1]
    
    # Получаем все данные из состояния
    data = await state.get_data()
    title = data.get("title")
    description = data.get("description", "")
    
    # Создаем новую задачу
    task = Task(
        title=title,
        description=description,
        task_type=TaskType(task_type),
        status=TaskStatus.ACTIVE,
        created_by=callback.from_user.id
    )
    
    # Добавляем задачу в базу данных
    task_id = db.add_task(task)
    task.id = task_id
    
    # Отправляем сообщение об успешном создании задачи
    await callback.message.edit_text(
        f"✅ Задача успешно создана!\n\n"
        f"📌 Название: {title}\n"
        f"📝 Описание: {description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(TaskType(task_type))}"
    )
    
    # Очищаем состояние
    await state.clear()

    # Отправляем уведомление партнеру, если задача для него или для обоих
    if task.task_type in [TaskType.FOR_PARTNER, TaskType.FOR_BOTH]:
        partner_id = db.get_partner_id(callback.from_user.id)
        if partner_id:
            try:
                # Отправляем уведомление партнеру
                await callback.bot.send_message(
                    partner_id,
                    f"🔔 У вас новая задача от партнера!\n\n"
                    f"📌 Название: {title}\n"
                    f"📝 Описание: {description or 'Нет описания'}\n"
                    f"👥 Тип: {get_task_type_text(TaskType(task_type))}"
                )
                await callback.answer("✅ Уведомление партнеру отправлено!")
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления партнеру: {e}")
                await callback.answer("⚠️ Не удалось отправить уведомление партнеру")
    
    # Отправляем клавиатуру главного меню
    await callback.message.answer(
        "Что бы вы хотели сделать дальше?",
        reply_markup=get_main_keyboard()
    )

# Вспомогательная функция для получения текстового представления типа задачи
def get_task_type_text(task_type: TaskType) -> str:
    if task_type == TaskType.FOR_ME:
        return "Для себя"
    elif task_type == TaskType.FOR_PARTNER:
        return "Для партнера"
    else:
        return "Для обоих"

# Обработчик кнопки "Мои задачи"
@router.message(F.text == "📋 Мои задачи")
async def show_my_tasks(message: Message):
    user_id = message.from_user.id
    
    my_tasks = db.get_user_tasks(user_id)
    
    if not my_tasks:
        await message.answer("У вас пока нет задач.")
        return
    
    await message.answer(
        "📋 Ваши задачи:",
        reply_markup=get_tasks_list_keyboard(my_tasks, context="my_tasks")
    )

# Обработчик кнопки "Задачи партнера"
@router.message(F.text == "🔄 Задачи партнера")
async def show_partner_tasks(message: Message):
    user_id = message.from_user.id
    
    # Напрямую получаем задачи партнёра:
    partner_tasks = db.get_partner_tasks(user_id)
    
    if not partner_tasks:
        await message.answer("У вашего партнера пока нет задач.")
        return
    
    await message.answer(
        "🔄 Задачи вашего партнера:",
        reply_markup=get_tasks_list_keyboard(partner_tasks, context="partner_tasks")
    )

# Обработчик кнопки "Общие задачи"
@router.message(F.text == "👫 Общие задачи")
async def show_common_tasks(message: Message):
    user_id = message.from_user.id
    
    # Напрямую получаем общие задачи:
    common_tasks = db.get_common_tasks(user_id)
    
    if not common_tasks:
        await message.answer("У вас пока нет общих задач.")
        return
    
    await message.answer(
        "👫 Общие задачи:",
        reply_markup=get_tasks_list_keyboard(common_tasks, context="common_tasks")
    )

# Обработчик просмотра задачи
@router.callback_query(F.data.startswith("view_task:"))
async def view_task(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    task_id = int(parts[1])
    context = parts[2] if len(parts) > 2 else "my_tasks"
    
    # Сохраняем контекст в стейт
    await state.update_data(task_context=context)
    
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        return
    
    # Формируем статус задачи
    status_text = "✅ Выполнена" if task.status == TaskStatus.COMPLETED else "🔄 Активна"
    
    # Определяем, кто создал задачу
    creator_text = "Вы" if task.created_by == callback.from_user.id else "Ваш партнер"
    
    # Формируем текст с информацией о задаче
    task_info = (
        f"📌 Название: {task.title}\n"
        f"📝 Описание: {task.description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(task.task_type)}\n"
        f"🚦 Статус: {status_text}\n"
        f"👤 Создатель: {creator_text}\n"
        f"📅 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        task_info,
        reply_markup=get_task_action_keyboard(task.id, task.status, context)
    )

# Обработчик изменения статуса задачи
@router.callback_query(F.data.startswith("task_status:"))
async def change_task_status(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    task_id = int(parts[1])
    new_status = TaskStatus(parts[2])
    
    # Получаем контекст из стейта
    data = await state.get_data()
    context = data.get("task_context", "my_tasks")
    
    task = db.get_task(task_id)
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        return
    
    # Обновляем статус задачи
    task.status = new_status
    db.update_task(task)

    # Уведомляем партнера об изменении статуса задачи, если она имеет отношение к нему
    if task.task_type in [TaskType.FOR_PARTNER, TaskType.FOR_BOTH] and task.created_by == callback.from_user.id:
        partner_id = db.get_partner_id(callback.from_user.id)
        if partner_id:
            try:
                status_text = "выполнена ✅" if task.status == TaskStatus.COMPLETED else "возвращена в активные 🔄"
                await callback.bot.send_message(
                    partner_id,
                    f"🔔 Обновление статуса задачи!"
                    f"📌 Задача \"{task.title}\" {status_text}"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления об изменении статуса: {e}")
    
    await callback.answer(f"Статус задачи изменен на: {new_status.value}")
    
    # Получаем обновленную задачу и показываем
    task = db.get_task(task_id)
    
    # Формируем статус задачи
    status_text = "✅ Выполнена" if task.status == TaskStatus.COMPLETED else "🔄 Активна"
    
    # Определяем, кто создал задачу
    creator_text = "Вы" if task.created_by == callback.from_user.id else "Ваш партнер"
    
    # Формируем текст с информацией о задаче
    task_info = (
        f"📌 Название: {task.title}\n"
        f"📝 Описание: {task.description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(task.task_type)}\n"
        f"🚦 Статус: {status_text}\n"
        f"👤 Создатель: {creator_text}\n"
        f"📅 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        task_info,
        reply_markup=get_task_action_keyboard(task.id, task.status, context)
    )

# Обработчик редактирования задачи
@router.callback_query(F.data.startswith("edit_task:"))
async def edit_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    
    # Получаем контекст из стейта
    data = await state.get_data()
    context = data.get("task_context", "my_tasks")
    
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        return
    
    # Сохраняем данные о задаче в состоянии
    await state.update_data(task_id=task_id)
    
    # Показываем меню редактирования с новой клавиатурой
    await callback.message.edit_text(
        "✏️ Что вы хотите изменить?",
        reply_markup=get_edit_menu_keyboard(task_id, context)
    )

# Обработчик выбора поля для редактирования
@router.callback_query(F.data.startswith("edit:"))
async def edit_task_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    
    # Получаем данные о задаче
    data = await state.get_data()
    task_id = data.get("task_id")
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        return
    
    if field == "title":
        await callback.message.edit_text(
            f"Текущее название: {task.title}\n\n"
            f"Введите новое название:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(TaskStates.edit_title)
    
    elif field == "description":
        await callback.message.edit_text(
            f"Текущее описание: {task.description or 'Нет описания'}\n\n"
            f"Введите новое описание (или отправьте '-' для удаления):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(TaskStates.edit_description)
    
    elif field == "type":
        await callback.message.edit_text(
            f"Текущий тип: {get_task_type_text(task.task_type)}\n\n"
            f"Выберите новый тип задачи:",
            reply_markup=get_task_type_keyboard()
        )
        await state.set_state(TaskStates.edit_type)

# Обработчик ввода нового названия
@router.message(TaskStates.edit_title)
async def process_edit_title(message: Message, state: FSMContext):
    new_title = message.text
    
    # Получаем данные о задаче
    data = await state.get_data()
    task_id = data.get("task_id")
    task = db.get_task(task_id)
    
    if not task:
        await message.answer("Задача не найдена. Возможно, она была удалена.")
        await state.clear()
        return
    
    # Обновляем название задачи
    task.title = new_title
    db.update_task(task)
    
    await message.answer(f"✅ Название задачи успешно обновлено!")
    
    # Очищаем состояние
    await state.clear()
    
    # Показываем обновленную информацию о задаче
    await message.answer(
        f"📌 Название: {task.title}\n"
        f"📝 Описание: {task.description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(task.task_type)}\n"
        f"🚦 Статус: {'✅ Выполнена' if task.status == TaskStatus.COMPLETED else '🔄 Активна'}",
        reply_markup=get_task_action_keyboard(task.id, task.status)
    )

# Обработчик ввода нового описания
@router.message(TaskStates.edit_description)
async def process_edit_description(message: Message, state: FSMContext):
    new_description = message.text
    if new_description == "-":
        new_description = ""
    
    # Получаем данные о задаче
    data = await state.get_data()
    task_id = data.get("task_id")
    task = db.get_task(task_id)
    
    if not task:
        await message.answer("Задача не найдена. Возможно, она была удалена.")
        await state.clear()
        return
    
    # Обновляем описание задачи
    task.description = new_description
    db.update_task(task)
    
    await message.answer(f"✅ Описание задачи успешно обновлено!")
    
    # Очищаем состояние
    await state.clear()
    
    # Показываем обновленную информацию о задаче
    await message.answer(
        f"📌 Название: {task.title}\n"
        f"📝 Описание: {task.description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(task.task_type)}\n"
        f"🚦 Статус: {'✅ Выполнена' if task.status == TaskStatus.COMPLETED else '🔄 Активна'}",
        reply_markup=get_task_action_keyboard(task.id, task.status)
    )

# Обработчик выбора нового типа задачи
@router.callback_query(TaskStates.edit_type, F.data.startswith("task_type:"))
async def process_edit_type(callback: CallbackQuery, state: FSMContext):
    new_type = TaskType(callback.data.split(":")[1])
    
    # Получаем данные о задаче
    data = await state.get_data()
    task_id = data.get("task_id")
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        await state.clear()
        return
    
    # Обновляем тип задачи
    task.task_type = new_type
    db.update_task(task)
    
    await callback.answer(f"✅ Тип задачи успешно обновлен!")
    
    # Очищаем состояние
    await state.clear()
    
    # Показываем обновленную информацию о задаче
    await callback.message.edit_text(
        f"📌 Название: {task.title}\n"
        f"📝 Описание: {task.description or 'Нет описания'}\n"
        f"👥 Тип: {get_task_type_text(task.task_type)}\n"
        f"🚦 Статус: {'✅ Выполнена' if task.status == TaskStatus.COMPLETED else '🔄 Активна'}",
        reply_markup=get_task_action_keyboard(task.id, task.status)
    )

# Обработчик удаления задачи
@router.callback_query(F.data.startswith("delete_task:"))
async def confirm_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("Задача не найдена. Возможно, она была удалена.")
        return
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить задачу?\n\n"
        f"📌 Название: {task.title}",
        reply_markup=get_confirm_keyboard("delete", task_id)
    )

# Обработчик подтверждения удаления задачи
@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    
    # Удаляем задачу
    success = db.delete_task(task_id)
    
    if success:
        await callback.answer("✅ Задача успешно удалена!")
        await callback.message.edit_text("Задача была удалена.")
        await callback.message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback.answer("❌ Ошибка при удалении задачи.")

# Обработчик переключения страниц в списке задач
@router.callback_query(F.data.startswith("page:"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    page = int(parts[1])
    
    # Получаем сохраненный контекст
    data = await state.get_data()
    context = data.get("task_context", "my_tasks")
    
    # Получаем задачи в зависимости от контекста
    user_id = callback.from_user.id
    
    if context == "my_tasks":
        filtered_tasks = db.get_user_tasks(user_id)
    elif context == "partner_tasks":
        filtered_tasks = db.get_partner_tasks(user_id)
    elif context == "common_tasks":
        filtered_tasks = db.get_common_tasks(user_id)
    else:
        filtered_tasks = db.get_tasks(user_id)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_tasks_list_keyboard(filtered_tasks, page, context=context)
    )

# Обработчик кнопки "Главное меню"
@router.callback_query(F.data == "main_menu")
async def return_to_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Вы вернулись в главное меню.",
        reply_markup=None
    )
    await callback.message.answer(
        "Что бы вы хотели сделать?",
        reply_markup=get_main_keyboard()
    )

# Обработчик кнопки "Назад к задачам"
@router.callback_query(F.data.startswith("back_to_tasks"))
async def back_to_tasks(callback: CallbackQuery, state: FSMContext):
    # Получаем контекст из колбэка или из стейта
    parts = callback.data.split(":")
    context = parts[1] if len(parts) > 1 else "my_tasks"
    
    # На всякий случай обновляем контекст в стейте
    await state.update_data(task_context=context)
    
    # Получаем задачи в зависимости от контекста
    user_id = callback.from_user.id
    
    if context == "my_tasks":
        filtered_tasks = db.get_user_tasks(user_id)
        title = "📋 Ваши задачи:"
    elif context == "partner_tasks":
        filtered_tasks = db.get_partner_tasks(user_id)
        title = "🔄 Задачи вашего партнера:"
    elif context == "common_tasks":
        filtered_tasks = db.get_common_tasks(user_id)
        title = "👫 Общие задачи:"
    else:
        filtered_tasks = db.get_tasks(user_id)
        title = "📋 Все задачи:"
    
    # Показываем отфильтрованный список задач
    await callback.message.edit_text(
        title,
        reply_markup=get_tasks_list_keyboard(filtered_tasks, context=context)
    )

# Обработчик кнопки "Отмена"
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=None
    )
    await callback.message.answer(
        "Что бы вы хотели сделать?",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Бот для задач для пары</b>\n\n"
        "Этот бот поможет вам и вашему партнеру создавать, отслеживать и выполнять совместные задачи.\n\n"
        "<b>Основные функции:</b>\n"
        "• Создание задач для себя, партнера или обоих\n"
        "• Просмотр всех задач по категориям\n"
        "• Изменение статуса задач (активные/выполненные)\n"
        "• Редактирование и удаление задач\n"
        "• Уведомления партнеру о новых задачах\n\n"
        "<b>Команды:</b>\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n\n"
        "Для начала работы, нажмите на кнопки в меню внизу экрана."
    )
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())