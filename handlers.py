import logging
from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models import Task, TaskType, TaskStatus, Wish, WishType, Movie, MovieType
from datetime import datetime

from config import ADMIN_IDS
from database import Database
from keyboards import (
    get_edit_menu_keyboard, get_main_keyboard, get_task_type_keyboard, get_task_action_keyboard,
    get_tasks_list_keyboard, get_cancel_keyboard, get_confirm_keyboard, get_wish_type_keyboard, 
    get_wishes_list_keyboard, get_wishes_list_keyboard, get_wish_action_keyboard, get_edit_wish_menu_keyboard,
    get_movies_menu_keyboard, get_movies_list_keyboard, get_movie_type_keyboard, get_movie_action_keyboard,
    get_edit_movie_menu_keyboard, get_movie_rating_keyboard
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

class WishStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_image = State()
    waiting_for_type = State()
    
    edit_title = State()
    edit_description = State()
    edit_image = State()
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

    # Всегда отправляем уведомление партнеру
    partner_id = db.get_partner_id(callback.from_user.id)
    if partner_id:
        try:
            # Формируем сообщение в зависимости от типа задачи
            message_text = ""
            if task.task_type == TaskType.FOR_PARTNER:
                message_text = f"🔔 У вас новая задача от партнера!"
            elif task.task_type == TaskType.FOR_BOTH:
                message_text = f"🔔 Создана новая общая задача!"
            else:  # FOR_ME
                message_text = f"🔔 Партнер добавил(а) задачу для себя!"

            # Отправляем уведомление партнеру
            await callback.bot.send_message(
                partner_id,
                f"{message_text}"
                f"📌 Название: {title}"
                f"📝 Описание: {description or 'Нет описания'}"
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

    # Уведомляем партнера об изменении статуса задачи
    partner_id = db.get_partner_id(callback.from_user.id)
    if partner_id and task.created_by != partner_id:
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

    # Уведомляем партнера об изменении названия задачи
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id and task.created_by != partner_id:  # Уведомляем только если задача создана не партнером
        try:
            await message.bot.send_message(
                partner_id,
                f"🔔 Обновление задачи!\n"
                f"📌 Задача изменена: новое название \"{task.title}\""
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении названия: {e}")
    
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

    # Уведомляем партнера об изменении описания задачи
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id and task.created_by != partner_id:
        try:
            await message.bot.send_message(
                partner_id,
                f"🔔 Обновление задачи!\n"
                f"📌 У задачи \"{task.title}\" изменено описание"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении описания: {e}")
    
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

    # Уведомляем партнера об изменении типа задачи
    partner_id = db.get_partner_id(callback.from_user.id)
    if partner_id and task.created_by != partner_id:
        try:
            await callback.bot.send_message(
                partner_id,
                f"🔔 Обновление задачи!\n"
                f"📌 У задачи \"{task.title}\" изменен тип на {get_task_type_text(task.task_type)}"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении типа: {e}")
    
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

    # Получаем задачу перед удалением, чтобы знать детали
    task = db.get_task(task_id)
    # Уведомляем партнера об удалении задачи
    if task:
        partner_id = db.get_partner_id(callback.from_user.id)
        if partner_id and task.created_by != partner_id:
            try:
                await callback.bot.send_message(
                    partner_id,
                    f"🔔 Задача удалена!\n"
                    f"📌 Задача \"{task.title}\" была удалена"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления об удалении: {e}")
    
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

# Вспомогательная функция для получения текстового представления типа желания
def get_wish_type_text(wish_type: WishType) -> str:
    if wish_type == WishType.MY_WISH:
        return "Моё желание"
    else:
        return "Желание партнёра"

# Обработчик кнопки "Добавить желание"
@router.message(F.text == "🎁 Добавить желание")
async def add_wish(message: Message, state: FSMContext):
    await message.answer(
        "✏️ Введите название желания:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WishStates.waiting_for_title)

# Обработчик ввода названия желания
@router.message(WishStates.waiting_for_title)
async def process_wish_title(message: Message, state: FSMContext):
    # Сохраняем название желания
    await state.update_data(title=message.text)
    
    await message.answer(
        "📝 Введите описание желания (или отправьте '-' для пропуска):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WishStates.waiting_for_description)

# Обработчик ввода описания желания
@router.message(WishStates.waiting_for_description)
async def process_wish_description(message: Message, state: FSMContext):
    description = message.text
    if description == "-":
        description = ""
    
    # Сохраняем описание желания
    await state.update_data(description=description)
    
    await message.answer(
        "🖼️ Отправьте изображение, иллюстрирующее ваше желание (или отправьте '-' для пропуска):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WishStates.waiting_for_image)

# Обработчик получения изображения для желания
@router.message(WishStates.waiting_for_image, F.photo | (F.text == "-"))
async def process_wish_image(message: Message, state: FSMContext):
    image_id = None
    
    if message.photo:
        # Берем самый большой размер фото (последний в списке)
        image_id = message.photo[-1].file_id
    
    # Сохраняем ID изображения (или None, если изображение не было отправлено)
    await state.update_data(image_id=image_id)
    
    await message.answer(
        "👥 Выберите тип желания:",
        reply_markup=get_wish_type_keyboard()
    )
    await state.set_state(WishStates.waiting_for_type)

# Обработчик выбора типа желания
@router.callback_query(WishStates.waiting_for_type, F.data.startswith("wish_type:"))
async def process_wish_type(callback: CallbackQuery, state: FSMContext):
    wish_type = callback.data.split(":")[1]
    
    # Получаем все данные из состояния
    data = await state.get_data()
    title = data.get("title")
    description = data.get("description", "")
    image_id = data.get("image_id")
    
    # Создаем новое желание
    wish = Wish(
        title=title,
        description=description,
        image_id=image_id,
        wish_type=WishType(wish_type),
        created_by=callback.from_user.id
    )
    
    # Добавляем желание в базу данных
    wish_id = db.add_wish(wish)
    wish.id = wish_id
    
    # Отправляем сообщение об успешном создании желания
    success_message = f"✅ Желание успешно создано!\n\n"
    success_message += f"📌 Название: {title}\n"
    success_message += f"📝 Описание: {description or 'Нет описания'}\n"
    success_message += f"👥 Тип: {get_wish_type_text(WishType(wish_type))}"
    
    if image_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=image_id,
            caption=success_message
        )
    else:
        await callback.message.edit_text(success_message)
    
    # Очищаем состояние
    await state.clear()
    
    # Всегда отправляем уведомление партнеру
    partner_id = db.get_partner_id(callback.from_user.id)
    if partner_id:
        try:
            # Формируем сообщение в зависимости от типа желания
            if wish.wish_type == WishType.PARTNER_WISH:
                notification = f"🎁 {callback.from_user.first_name} добавил(а) новое желание для вас!"
            else:  # MY_WISH
                notification = f"✨ {callback.from_user.first_name} добавил(а) своё новое желание!"

            notification += f"📌 Название: {title}"
            notification += f"📝 Описание: {description or 'Нет описания'}"
            
            if image_id:
                await callback.bot.send_photo(
                    partner_id,
                    photo=image_id,
                    caption=notification
                )
            else:
                await callback.bot.send_message(
                    partner_id,
                    notification
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

# Обработчик кнопки "Мои желания"
@router.message(F.text == "✨ Мои желания")
async def show_my_wishes(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Получаем желания пользователя
    my_wishes = db.get_my_wishes(user_id)
    
    if not my_wishes:
        await message.answer("У вас пока нет добавленных желаний.")
        return
    
    # Сохраняем контекст
    await state.update_data(wish_context="my_wishes")
    
    await message.answer(
        "✨ Ваши желания:",
        reply_markup=get_wishes_list_keyboard(my_wishes, context="my_wishes")
    )

# Обработчик кнопки "Желания партнёра"
@router.message(F.text == "🎀 Желания партнёра")
async def show_partner_wishes(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Получаем желания партнёра
    partner_wishes = db.get_partner_wishes(user_id)
    
    if not partner_wishes:
        await message.answer("У вашего партнёра пока нет добавленных желаний.")
        return
    
    # Сохраняем контекст
    await state.update_data(wish_context="partner_wishes")
    
    await message.answer(
        "🎀 Желания вашего партнёра:",
        reply_markup=get_wishes_list_keyboard(partner_wishes, context="partner_wishes")
    )

# Обработчик просмотра желания
@router.callback_query(F.data.startswith("view_wish:"))
async def view_wish(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    wish_id = int(parts[1])
    context = parts[2] if len(parts) > 2 else "my_wishes"
    
    # Сохраняем контекст в стейт
    await state.update_data(wish_context=context)
    
    wish = db.get_wish(wish_id)
    
    if not wish:
        await callback.answer("Желание не найдено. Возможно, оно было удалено.")
        return
    
    # Определяем, кто создал желание
    creator_text = "Вы" if wish.created_by == callback.from_user.id else "Ваш партнер"
    
    # Формируем текст с информацией о желании
    wish_info = (
        f"📌 Название: {wish.title}\n"
        f"📝 Описание: {wish.description or 'Нет описания'}\n"
        f"👥 Тип: {get_wish_type_text(wish.wish_type)}\n"
        f"👤 Создатель: {creator_text}\n"
        f"📅 Создано: {wish.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    # Если есть изображение, отправляем его с информацией о желании
    if wish.image_id:
        # Удаляем предыдущее сообщение, если оно было
        await callback.message.delete()
        
        # Отправляем фото с информацией
        message = await callback.message.answer_photo(
            photo=wish.image_id,
            caption=wish_info,
            reply_markup=get_wish_action_keyboard(wish.id, context)
        )
    else:
        # Если изображения нет, просто редактируем текущее сообщение
        await callback.message.edit_text(
            wish_info,
            reply_markup=get_wish_action_keyboard(wish.id, context)
        )

@router.callback_query(F.data.startswith("edit_wish:"))
async def edit_wish(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    
    if len(parts) == 2:
        # Проверяем, можно ли преобразовать второй элемент в число
        try:
            # Если edit_wish:{wish_id}, то показываем меню редактирования
            wish_id = int(parts[1])
            
            # Получаем контекст из стейта
            data = await state.get_data()
            context = data.get("wish_context", "my_wishes")
            
            wish = db.get_wish(wish_id)
            
            if not wish:
                await callback.answer("Желание не найдено. Возможно, оно было удалено.")
                return
            
            # Сохраняем данные о желании в состоянии
            await state.update_data(wish_id=wish_id)
            
            # Проверяем, есть ли фото в сообщении
            if callback.message.photo:
                # Если есть фото, удаляем сообщение и отправляем новое текстовое
                await callback.message.delete()
                await callback.message.answer(
                    "✏️ Что вы хотите изменить?",
                    reply_markup=get_edit_wish_menu_keyboard(wish_id, context)
                )
            else:
                # Если нет фото, можем просто редактировать текст
                await callback.message.edit_text(
                    "✏️ Что вы хотите изменить?",
                    reply_markup=get_edit_wish_menu_keyboard(wish_id, context)
                )
        except ValueError:
            # Если второй элемент не число, значит это редактирование поля
            field = parts[1]
            
            # Получаем данные о желании
            data = await state.get_data()
            wish_id = data.get("wish_id")
            wish = db.get_wish(wish_id)
            
            if not wish:
                await callback.answer("Желание не найдено. Возможно, оно было удалено.")
                return
            
            if field == "title":
                await callback.message.edit_text(
                    f"Текущее название: {wish.title}\n\n"
                    f"Введите новое название:",
                    reply_markup=get_cancel_keyboard()
                )
                await state.set_state(WishStates.edit_title)
            
            elif field == "description":
                await callback.message.edit_text(
                    f"Текущее описание: {wish.description or 'Нет описания'}\n\n"
                    f"Введите новое описание (или отправьте '-' для удаления):",
                    reply_markup=get_cancel_keyboard()
                )
                await state.set_state(WishStates.edit_description)
            
            elif field == "image":
                await callback.message.edit_text(
                    f"Отправьте новое изображение (или отправьте '-' для удаления текущего):",
                    reply_markup=get_cancel_keyboard()
                )
                await state.set_state(WishStates.edit_image)
            
            elif field == "type":
                await callback.message.edit_text(
                    f"Текущий тип: {get_wish_type_text(wish.wish_type)}\n\n"
                    f"Выберите новый тип желания:",
                    reply_markup=get_wish_type_keyboard()
                )
                await state.set_state(WishStates.edit_type)
    else:
        # Если edit_wish:{field}, то начинаем редактирование поля
        field = parts[1]
        
        # Получаем данные о желании
        data = await state.get_data()
        wish_id = data.get("wish_id")
        wish = db.get_wish(wish_id)
        
        if not wish:
            await callback.answer("Желание не найдено. Возможно, оно было удалено.")
            return
        
        if field == "title":
            await callback.message.edit_text(
                f"Текущее название: {wish.title}\n\n"
                f"Введите новое название:",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(WishStates.edit_title)
        
        elif field == "description":
            await callback.message.edit_text(
                f"Текущее описание: {wish.description or 'Нет описания'}\n\n"
                f"Введите новое описание (или отправьте '-' для удаления):",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(WishStates.edit_description)
        
        elif field == "image":
            await callback.message.edit_text(
                f"Отправьте новое изображение (или отправьте '-' для удаления текущего):",
                reply_markup=get_cancel_keyboard()
            )
            await state.set_state(WishStates.edit_image)
        
        elif field == "type":
            await callback.message.edit_text(
                f"Текущий тип: {get_wish_type_text(wish.wish_type)}\n\n"
                f"Выберите новый тип желания:",
                reply_markup=get_wish_type_keyboard()
            )
            await state.set_state(WishStates.edit_type)

# Обработчик ввода нового названия желания
@router.message(WishStates.edit_title)
async def process_edit_wish_title(message: Message, state: FSMContext):
    new_title = message.text
    
    # Получаем данные о желании
    data = await state.get_data()
    wish_id = data.get("wish_id")
    wish = db.get_wish(wish_id)
    
    if not wish:
        await message.answer("Желание не найдено. Возможно, оно было удалено.")
        await state.clear()
        return
    
    # Обновляем название желания
    wish.title = new_title
    db.update_wish(wish)
    
    await message.answer(f"✅ Название желания успешно обновлено!")

    # Уведомляем партнера об изменении названия желания
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id and wish.created_by != partner_id:
        try:
            await message.bot.send_message(
                partner_id,
                f"🎁 Обновление желания!\n"
                f"📌 Желание изменено: новое название \"{wish.title}\""
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении названия желания: {e}")
    
    # Очищаем состояние редактирования
    await state.set_data({})
    
    # Показываем обновленную информацию о желании
    wish_info = (
        f"📌 Название: {wish.title}\n"
        f"📝 Описание: {wish.description or 'Нет описания'}\n"
        f"👥 Тип: {get_wish_type_text(wish.wish_type)}\n"
        f"📅 Создано: {wish.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    if wish.image_id:
        await message.answer_photo(
            photo=wish.image_id,
            caption=wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )
    else:
        await message.answer(
            wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )

# Обработчик ввода нового описания желания
@router.message(WishStates.edit_description)
async def process_edit_wish_description(message: Message, state: FSMContext):
    new_description = message.text
    if new_description == "-":
        new_description = ""
    
    # Получаем данные о желании
    data = await state.get_data()
    wish_id = data.get("wish_id")
    wish = db.get_wish(wish_id)
    
    if not wish:
        await message.answer("Желание не найдено. Возможно, оно было удалено.")
        await state.clear()
        return
    
    # Обновляем описание желания
    wish.description = new_description
    db.update_wish(wish)
    
    await message.answer(f"✅ Описание желания успешно обновлено!")

    # Уведомляем партнера об изменении описания желания
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id and wish.created_by != partner_id:
        try:
            await message.bot.send_message(
                partner_id,
                f"🎁 Обновление желания!\n"
                f"📌 У желания \"{wish.title}\" изменено описание"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении описания желания: {e}")
    
    # Очищаем состояние редактирования
    await state.set_data({})
    
    # Показываем обновленную информацию о желании
    wish_info = (
        f"📌 Название: {wish.title}\n"
        f"📝 Описание: {wish.description or 'Нет описания'}\n"
        f"👥 Тип: {get_wish_type_text(wish.wish_type)}\n"
        f"📅 Создано: {wish.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    if wish.image_id:
        await message.answer_photo(
            photo=wish.image_id,
            caption=wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )
    else:
        await message.answer(
            wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )

# Обработчик получения нового изображения для желания
@router.message(WishStates.edit_image, F.photo | (F.text == "-"))
async def process_edit_wish_image(message: Message, state: FSMContext):
    # Получаем данные о желании
    data = await state.get_data()
    wish_id = data.get("wish_id")
    wish = db.get_wish(wish_id)
    
    if not wish:
        await message.answer("Желание не найдено. Возможно, оно было удалено.")
        await state.clear()
        return
    
    if message.text == "-":
        # Если пользователь отправил "-", удаляем изображение
        wish.image_id = None
    else:
        # Иначе обновляем изображение
        wish.image_id = message.photo[-1].file_id
    
    db.update_wish(wish)
    
    await message.answer(f"✅ Изображение желания успешно обновлено!")

    # Уведомляем партнера об изменении изображения желания
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id and wish.created_by != partner_id:
        try:
            if wish.image_id:
                await message.bot.send_photo(
                    partner_id,
                    photo=wish.image_id,
                    caption=f"🎁 Обновление желания!\n"
                    f"📌 У желания \"{wish.title}\" обновлено изображение"
                )
            else:
                await message.bot.send_message(
                    partner_id,
                    f"🎁 Обновление желания!\n"
                    f"📌 У желания \"{wish.title}\" удалено изображение"
                )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении изображения: {e}")
    
    # Очищаем состояние редактирования
    await state.set_data({})
    
    # Показываем обновленную информацию о желании
    wish_info = (
        f"📌 Название: {wish.title}\n"
        f"📝 Описание: {wish.description or 'Нет описания'}\n"
        f"👥 Тип: {get_wish_type_text(wish.wish_type)}\n"
        f"📅 Создано: {wish.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    if wish.image_id:
        await message.answer_photo(
            photo=wish.image_id,
            caption=wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )
    else:
        await message.answer(
            wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )

# Обработчик выбора нового типа желания
@router.callback_query(WishStates.edit_type, F.data.startswith("wish_type:"))
async def process_edit_wish_type(callback: CallbackQuery, state: FSMContext):
    new_type = WishType(callback.data.split(":")[1])
    
    # Получаем данные о желании
    data = await state.get_data()
    wish_id = data.get("wish_id")
    wish = db.get_wish(wish_id)
    
    if not wish:
        await callback.answer("Желание не найдено. Возможно, оно было удалено.")
        await state.clear()
        return
    
    # Обновляем тип желания
    wish.wish_type = new_type
    db.update_wish(wish)
    
    await callback.answer(f"✅ Тип желания успешно обновлен!")

    # Уведомляем партнера об изменении типа желания
    partner_id = db.get_partner_id(callback.from_user.id)
    if partner_id and wish.created_by != partner_id:
        try:
            msg = f"🎁 Обновление желания!\n📌 У желания \"{wish.title}\" изменен тип на {get_wish_type_text(wish.wish_type)}"
            
            if wish.image_id:
                await callback.bot.send_photo(
                    partner_id,
                    photo=wish.image_id,
                    caption=msg
                )
            else:
                await callback.bot.send_message(
                    partner_id,
                    msg
                )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления об изменении типа желания: {e}")
    
    # Очищаем состояние
    await state.clear()
    
    # Показываем обновленную информацию о желании
    wish_info = (
        f"📌 Название: {wish.title}\n"
        f"📝 Описание: {wish.description or 'Нет описания'}\n"
        f"👥 Тип: {get_wish_type_text(wish.wish_type)}\n"
        f"📅 Создано: {wish.created_at.strftime('%d.%m.%Y %H:%M')}"
    )
    
    if wish.image_id:
        # Нужно удалить старое сообщение и отправить новое с фото
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=wish.image_id,
            caption=wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )
    else:
        await callback.message.edit_text(
            wish_info,
            reply_markup=get_wish_action_keyboard(wish.id)
        )

# Обработчик удаления желания
@router.callback_query(F.data.startswith("delete_wish:"))
async def confirm_delete_wish(callback: CallbackQuery):
    wish_id = int(callback.data.split(":")[1])
    wish = db.get_wish(wish_id)
    
    if not wish:
        await callback.answer("Желание не найдено. Возможно, оно было удалено.")
        return
    
    confirmation_text = f"⚠️ Вы уверены, что хотите удалить желание?\n\n📌 Название: {wish.title}"
    
    # Проверяем, содержит ли сообщение фото
    if callback.message.photo:
        # Если сообщение содержит фото, удаляем его и отправляем новое текстовое
        await callback.message.delete()
        await callback.message.answer(
            confirmation_text,
            reply_markup=get_confirm_keyboard("delete_wish", wish_id)
        )
    else:
        # Если сообщение текстовое, просто редактируем текст
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=get_confirm_keyboard("delete_wish", wish_id)
        )

# Обработчик подтверждения удаления желания
@router.callback_query(F.data.startswith("confirm_delete_wish:"))
async def delete_wish(callback: CallbackQuery):
    wish_id = int(callback.data.split(":")[1])

    # Получаем желание перед удалением, чтобы знать детали
    wish = db.get_wish(wish_id)
    # Уведомляем партнера об удалении желания
    if wish:
        partner_id = db.get_partner_id(callback.from_user.id)
        if partner_id and wish.created_by != partner_id:
            try:
                if wish.image_id:
                    await callback.bot.send_photo(
                        partner_id,
                        photo=wish.image_id,
                        caption=f"🎁 Желание удалено!\n"
                        f"📌 Желание \"{wish.title}\" было удалено"
                    )
                else:
                    await callback.bot.send_message(
                        partner_id,
                        f"🎁 Желание удалено!\n"
                        f"📌 Желание \"{wish.title}\" было удалено"
                    )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления об удалении желания: {e}")
    
    # Удаляем желание
    success = db.delete_wish(wish_id)
    
    if success:
        await callback.answer("✅ Желание успешно удалено!")
        
        # Здесь нет необходимости проверять наличие фото, 
        # т.к. на этапе подтверждения мы уже отправляем текстовое сообщение
        await callback.message.edit_text("Желание было удалено.")
        await callback.message.answer(
            "Что бы вы хотели сделать дальше?",
            reply_markup=get_main_keyboard()
        )
    else:
        await callback.answer("❌ Ошибка при удалении желания.")

# Обработчик переключения страниц в списке желаний
@router.callback_query(F.data.startswith("wish_page:"))
async def handle_wish_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    
    # Получаем контекст из состояния
    data = await state.get_data()
    context = data.get("wish_context", "my_wishes")
    
    filtered_wishes = db.get_my_wishes(callback.from_user.id) if context == "my_wishes" else db.get_partner_wishes(callback.from_user.id)
    
    title = "✨ Ваши желания:" if context == "my_wishes" else "🎀 Желания вашего партнёра:"
    
    await callback.message.edit_text(
        title,
        reply_markup=get_wishes_list_keyboard(filtered_wishes, page=page, context=context)
    )

# Обработчик кнопки "Назад к желаниям"
@router.callback_query(F.data.startswith("back_to_wishes"))
async def back_to_wishes(callback: CallbackQuery, state: FSMContext):
    # Получаем контекст из колбэка или из стейта
    parts = callback.data.split(":")
    context = parts[1] if len(parts) > 1 else "my_wishes"
    
    # На всякий случай обновляем контекст в стейте
    await state.update_data(wish_context=context)
    
    # Получаем желания в зависимости от контекста
    user_id = callback.from_user.id
    
    if context == "my_wishes":
        filtered_wishes = db.get_my_wishes(user_id)
        title = "✨ Ваши желания:"
    elif context == "partner_wishes":
        filtered_wishes = db.get_partner_wishes(user_id)
        title = "🎀 Желания вашего партнёра:"
    else:
        filtered_wishes = db.get_wishes(user_id)
        title = "🎁 Все желания:"
    
    # Проверяем, содержит ли сообщение фото
    if callback.message.photo:
        # Если сообщение содержит фото, удаляем его и отправляем новое
        await callback.message.delete()
        await callback.message.answer(
            title,
            reply_markup=get_wishes_list_keyboard(filtered_wishes, context=context)
        )
    else:
        # Если сообщение текстовое, просто редактируем текст
        await callback.message.edit_text(
            title,
            reply_markup=get_wishes_list_keyboard(filtered_wishes, context=context)
        )

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🤖 <b>Бот для задач и желаний пары</b>\n\n"
        "Этот бот поможет вам и вашему партнеру создавать, отслеживать и выполнять совместные задачи, "
        "а также вести список желаний для подарков.\n\n"
        "<b>Основные функции:</b>\n"
        "• Создание задач для себя, партнера или обоих\n"
        "• Просмотр всех задач по категориям\n"
        "• Изменение статуса задач (активные/выполненные)\n"
        "• Редактирование и удаление задач\n"
        "• Уведомления партнеру о новых задачах\n"
        "• Добавление желаний с возможностью прикрепить фото\n"
        "• Просмотр своих желаний и желаний партнера\n\n"
        "<b>Команды:</b>\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n\n"
        "Для начала работы, нажмите на кнопки в меню внизу экрана."
    )
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())

# Обработчик кнопки "Выполненные задачи"
@router.message(F.text == "✅ Выполненные задачи")
async def show_completed_tasks(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Получаем выполненные задачи
    completed_tasks = db.get_completed_tasks(user_id)
    
    if not completed_tasks:
        await message.answer("У вас пока нет выполненных задач.")
        return
    
    await state.update_data(task_context="completed_tasks")
    
    await message.answer(
        "✅ Выполненные задачи:",
        reply_markup=get_tasks_list_keyboard(completed_tasks, context="completed_tasks")
    )

# Movie handlers
@router.message(F.text == "🎬 Фильмы")
async def show_movies_menu(message: Message, state: FSMContext):
    await message.answer(
        "Выберите действие:",
        reply_markup=get_movies_menu_keyboard()
    )

@router.callback_query(F.data.startswith("movies:"))
async def handle_movies_menu(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    
    if action == "my":
        movies = db.get_my_movies(callback.from_user.id)
        if not movies:
            await callback.message.edit_text(
                "У вас пока нет фильмов в списке.",
                reply_markup=get_movies_menu_keyboard()
            )
            return
            
        await callback.message.edit_text(
            "Ваши фильмы:",
            reply_markup=get_movies_list_keyboard(movies, context="my_movies")
        )
        
    elif action == "partner":
        movies = db.get_partner_movies(callback.from_user.id)
        if not movies:
            await callback.message.edit_text(
                "У партнёра пока нет фильмов в списке.",
                reply_markup=get_movies_menu_keyboard()
            )
            return
            
        await callback.message.edit_text(
            "Фильмы партнёра:",
            reply_markup=get_movies_list_keyboard(movies, context="partner_movies")
        )
        
    elif action == "add":
        await callback.message.edit_text(
            "Выберите, в какой список добавить фильм:",
            reply_markup=get_movie_type_keyboard()
        )
        
    elif action == "stats":
        stats = db.get_movie_stats(callback.from_user.id)
        text = "📊 Статистика фильмов:\n\n"
        text += f"Всего фильмов: {stats['total_movies']}\n"
        text += f"Просмотрено: {stats['watched_movies']}\n"
        if stats['avg_rating']:
            text += f"Средняя оценка: {'⭐' * round(stats['avg_rating'])}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_movies_menu_keyboard()
        )
        
    elif action == "recommendations":
        recommendations = db.get_movie_recommendations(callback.from_user.id)
        if not recommendations:
            await callback.message.edit_text(
                "К сожалению, сейчас нет рекомендаций для вас.",
                reply_markup=get_movies_menu_keyboard()
            )
            return
            
        text = "🎯 Рекомендуемые фильмы:\n\n"
        for movie in recommendations:
            text += f"🎬 {movie['title']}\n"
            if movie['description'] and movie['description'] != "-":
                text += f"📝 {movie['description']}\n"
            text += f"⭐ Оценка партнёра: {'⭐' * movie['rating']}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_movies_menu_keyboard()
        )

@router.callback_query(F.data.startswith("view_movie:"))
async def handle_view_movie(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    context = callback.data.split(":")[2]
    
    movie = db.get_movie(movie_id)
    if not movie:
        await callback.message.edit_text(
            "Фильм не найден.",
            reply_markup=get_movies_menu_keyboard()
        )
        return
    
    text = f"🎬 {movie['title']}\n\n"
    if movie['description'] and movie['description'] != "-":
        text += f"📝 {movie['description']}\n\n"
    text += f"📅 Добавлен: {movie['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
    
    if movie.get('watched', False):
        text += f"✅ Просмотрен: {movie['watch_date'].strftime('%d.%m.%Y')}\n"
        if movie.get('review'):
            text += f"\n📝 Отзыв:\n{movie['review']}\n"
    
    if movie.get('rating'):
        text += f"\n⭐ Оценка: {'⭐' * movie['rating']}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_movie_action_keyboard(movie_id, context, movie.get('watched', False))
    )

@router.callback_query(F.data.startswith("mark_watched:"))
async def handle_mark_watched(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    await state.update_data(marking_movie_id=movie_id)
    
    await callback.message.edit_text(
        "Хотите оставить отзыв о фильме? (Отправьте '-' если не хотите):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_for_movie_review")

@router.message(StateFilter("waiting_for_movie_review"))
async def handle_movie_review(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_id = data["marking_movie_id"]
    review = "-" if message.text == "-" else message.text
    
    movie = db.get_movie(movie_id)
    if db.update_movie_watch_status(movie_id, True, datetime.now(), review):
        # Уведомляем партнера о просмотре фильма
        if movie:
            partner_id = db.get_partner_id(message.from_user.id)
            if partner_id:
                try:
                    notification = f"🎬 Фильм просмотрен!\n📌 {message.from_user.first_name} посмотрел(а) фильм \"{movie['title']}\""
                    if review != "-":
                        notification += f"\n\n📝 Отзыв:\n{review}"
                    await message.bot.send_message(partner_id, notification)
                except Exception as e:
                    logging.error(f"Ошибка при отправке уведомления о просмотре фильма: {e}")
        
        await message.answer(
            "Фильм отмечен как просмотренный!",
            reply_markup=get_movies_menu_keyboard()
        )
    else:
        await message.answer(
            "Произошла ошибка при обновлении статуса фильма.",
            reply_markup=get_movies_menu_keyboard()
        )
    await state.clear()

@router.callback_query(F.data.startswith("add_review:"))
async def handle_add_review(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    await state.update_data(reviewing_movie_id=movie_id)
    
    await callback.message.edit_text(
        "Введите ваш отзыв о фильме:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_for_movie_review_edit")

@router.message(StateFilter("waiting_for_movie_review_edit"))
async def handle_movie_review_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_id = data["reviewing_movie_id"]
    
    movie = db.get_movie(movie_id)
    if not movie:
        await message.answer(
            "Фильм не найден.",
            reply_markup=get_movies_menu_keyboard()
        )
        await state.clear()
        return
    
    if db.update_movie_watch_status(movie_id, movie['watched'], movie['watch_date'], message.text):
        # Уведомляем партнера о новом отзыве
        partner_id = db.get_partner_id(message.from_user.id)
        if partner_id:
            try:
                await message.bot.send_message(
                    partner_id,
                    f"🎬 Новый отзыв!\n"
                    f"📌 {message.from_user.first_name} оставил(а) отзыв о фильме \"{movie['title']}\":\n\n"
                    f"{message.text}"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления о новом отзыве: {e}")
        
        await message.answer(
            "Отзыв успешно добавлен!",
            reply_markup=get_movies_menu_keyboard()
        )
    else:
        await message.answer(
            "Произошла ошибка при добавлении отзыва.",
            reply_markup=get_movies_menu_keyboard()
        )
    await state.clear()

@router.callback_query(F.data.startswith("movie_type:"))
async def handle_movie_type(callback: CallbackQuery, state: FSMContext):
    movie_type = callback.data.split(":")[1]
    await state.update_data(movie_type=movie_type)
    
    await callback.message.edit_text(
        "Введите название фильма:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_for_movie_title")

@router.message(StateFilter("waiting_for_movie_title"))
async def handle_movie_title(message: Message, state: FSMContext):
    await state.update_data(movie_title=message.text)
    
    await message.answer(
        "Введите описание фильма (или отправьте '-' если описание не нужно):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state("waiting_for_movie_description")

@router.message(StateFilter("waiting_for_movie_description"))
async def handle_movie_description(message: Message, state: FSMContext):
    data = await state.get_data()
    description = "-" if message.text == "-" else message.text
    
    movie_id = db.add_movie(
        title=data["movie_title"],
        description=description,
        movie_type=data["movie_type"],
        created_by=message.from_user.id
    )
    
    # Уведомляем партнера о новом фильме
    partner_id = db.get_partner_id(message.from_user.id)
    if partner_id:
        try:
            movie_type_text = "свой список" if data["movie_type"] == "my_movies" else "ваш список"
            await message.bot.send_message(
                partner_id,
                f"🎬 Новый фильм!\n"
                f"📌 {message.from_user.first_name} добавил(а) фильм \"{data['movie_title']}\" в {movie_type_text}"
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления о новом фильме: {e}")
    
    await message.answer(
        "Фильм успешно добавлен!",
        reply_markup=get_movies_menu_keyboard()
    )
    await state.clear()

@router.callback_query(F.data.startswith("edit_movie:"))
async def handle_edit_movie(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    
    if action == "title":
        await callback.message.edit_text(
            "Введите новое название фильма:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state("waiting_for_movie_title_edit")
        
    elif action == "description":
        await callback.message.edit_text(
            "Введите новое описание фильма (или отправьте '-' если описание не нужно):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state("waiting_for_movie_description_edit")
        
    else:
        movie_id = int(action)
        await state.update_data(editing_movie_id=movie_id)
        await callback.message.edit_text(
            "Выберите, что хотите изменить:",
            reply_markup=get_edit_movie_menu_keyboard(movie_id)
        )

@router.message(StateFilter("waiting_for_movie_title_edit"))
async def handle_movie_title_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_id = data["editing_movie_id"]
    
    movie = db.get_movie(movie_id)
    if not movie:
        await message.answer(
            "Фильм не найден.",
            reply_markup=get_movies_menu_keyboard()
        )
        await state.clear()
        return
    
    if db.update_movie(movie_id, message.text, movie["description"]):
        # Уведомляем партнера об изменении названия фильма
        partner_id = db.get_partner_id(message.from_user.id)
        if partner_id:
            try:
                await message.bot.send_message(
                    partner_id,
                    f"🎬 Обновление фильма!\n"
                    f"📌 {message.from_user.first_name} изменил(а) название фильма на \"{message.text}\""
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления об изменении названия фильма: {e}")
        
        await message.answer(
            "Название фильма успешно обновлено!",
            reply_markup=get_movies_menu_keyboard()
        )
    else:
        await message.answer(
            "Произошла ошибка при обновлении названия фильма.",
            reply_markup=get_movies_menu_keyboard()
        )
    await state.clear()

@router.message(StateFilter("waiting_for_movie_description_edit"))
async def handle_movie_description_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    movie_id = data["editing_movie_id"]
    
    movie = db.get_movie(movie_id)
    if not movie:
        await message.answer(
            "Фильм не найден.",
            reply_markup=get_movies_menu_keyboard()
        )
        await state.clear()
        return
    
    description = "-" if message.text == "-" else message.text
    if db.update_movie(movie_id, movie["title"], description):
        await message.answer(
            "Описание фильма успешно обновлено!",
            reply_markup=get_movies_menu_keyboard()
        )
    else:
        await message.answer(
            "Произошла ошибка при обновлении описания фильма.",
            reply_markup=get_movies_menu_keyboard()
        )
    await state.clear()

@router.callback_query(F.data.startswith("delete_movie:"))
async def handle_delete_movie(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот фильм?",
        reply_markup=get_confirm_keyboard("delete_movie", movie_id)
    )

@router.callback_query(F.data.startswith("confirm_delete_movie:"))
async def handle_confirm_delete_movie(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split(":")[1])
    
    if db.delete_movie(movie_id):
        await callback.message.edit_text(
            "Фильм успешно удалён!",
            reply_markup=get_movies_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "Произошла ошибка при удалении фильма.",
            reply_markup=get_movies_menu_keyboard()
        )

@router.callback_query(F.data.startswith("back_to_movies:"))
async def handle_back_to_movies(callback: CallbackQuery, state: FSMContext):
    context = callback.data.split(":")[1]
    
    if context == "my_movies":
        movies = db.get_my_movies(callback.from_user.id)
        if not movies:
            await callback.message.edit_text(
                "У вас пока нет фильмов в списке.",
                reply_markup=get_movies_menu_keyboard()
            )
            return
            
        await callback.message.edit_text(
            "Ваши фильмы:",
            reply_markup=get_movies_list_keyboard(movies, context="my_movies")
        )
    else:
        movies = db.get_partner_movies(callback.from_user.id)
        if not movies:
            await callback.message.edit_text(
                "У партнёра пока нет фильмов в списке.",
                reply_markup=get_movies_menu_keyboard()
            )
            return
            
        await callback.message.edit_text(
            "Фильмы партнёра:",
            reply_markup=get_movies_list_keyboard(movies, context="partner_movies")
        )

@router.callback_query(F.data.startswith("movie_page:"))
async def handle_movie_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    context = "my_movies" if "my_movies" in callback.message.text else "partner_movies"
    
    movies = db.get_my_movies(callback.from_user.id) if context == "my_movies" else db.get_partner_movies(callback.from_user.id)
    
    await callback.message.edit_text(
        callback.message.text,
        reply_markup=get_movies_list_keyboard(movies, page=page, context=context)
    )

@router.callback_query(lambda c: c.data.startswith('rate_movie:'))
async def process_rate_movie(callback_query: types.CallbackQuery, state: FSMContext):
    movie_id = int(callback_query.data.split(':')[1])
    await callback_query.message.edit_text(
        "Выберите, насколько вы хотите посмотреть этот фильм:",
        reply_markup=get_movie_rating_keyboard(movie_id)
    )

@router.callback_query(lambda c: c.data.startswith('set_rating:'))
async def process_set_rating(callback_query: types.CallbackQuery, state: FSMContext):
    _, movie_id, rating = callback_query.data.split(':')
    movie_id = int(movie_id)
    rating = int(rating)
    
    if db.update_movie_rating(movie_id, rating):
        movie = db.get_movie(movie_id)
        # Отправляем уведомление партнеру
        partner_id = db.get_partner_id(callback_query.from_user.id)
        if partner_id:
            try:
                await callback_query.bot.send_message(
                    partner_id,
                    f"⭐ Оценка фильма!\n"
                    f"📌 {callback_query.from_user.first_name} оценил(а) фильм \"{movie['title']}\" на {rating} звезд"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке уведомления об оценке фильма: {e}")
        
        await callback_query.message.edit_text(
            f"Фильм: {movie['title']}\n"
            f"Описание: {movie['description']}\n"
            f"Ваша оценка: {'⭐' * rating}",
            reply_markup=get_movie_action_keyboard(movie_id, "partner_movies", movie.get('watched', False))
        )
    else:
        await callback_query.message.edit_text(
            "Произошла ошибка при сохранении оценки. Попробуйте позже.",
            reply_markup=get_movie_action_keyboard(movie_id, "partner_movies", movie.get('watched', False))
        )