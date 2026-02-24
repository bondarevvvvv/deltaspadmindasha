import telebot
from telebot import types
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ========== НАСТРОЙКИ ==========
ADMIN_BOT_TOKEN = '8212103646:AAHbIr_A-OAfkMBCTwMcxdfHErC21JhOzeM'
MAIN_BOT_TOKEN = '8510845153:AAGUO5jg01h2NlL46VsD1f-7osYIBVTkxTQ'

# ← Вставьте ID вашей Google Таблицы (из ссылки: docs.google.com/spreadsheets/d/ВОТ_ЭТО/edit)
SPREADSHEET_ID = '12jDOiE_qD8JySOVgCdpvbPtO-O5RXUmxjSz-C9fS728'

# ← Путь к файлу credentials.json (должен лежать рядом с этим скриптом)
CREDENTIALS_FILE = 'credentials.json'

admin_bot = telebot.TeleBot(ADMIN_BOT_TOKEN)
main_bot = telebot.TeleBot(MAIN_BOT_TOKEN)

# ========== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ==========

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheets_client():
    """Создаёт и возвращает авторизованный клиент Google Sheets"""
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def get_spreadsheet():
    """Открывает таблицу по ID"""
    client = get_sheets_client()
    return client.open_by_key(SPREADSHEET_ID)

def init_sheets():
    """
    Создаёт нужные листы в таблице если их ещё нет.
    Лист 'Users'   — данные о пользователях
    Лист 'Actions' — история действий
    """
    try:
        spreadsheet = get_spreadsheet()
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]

        # --- Лист Users ---
        if 'Users' not in existing_sheets:
            ws = spreadsheet.add_worksheet(title='Users', rows=1000, cols=10)
            ws.append_row(['user_id', 'name', 'username', 'phone', 'email', 'question', 'feedback', 'created_at'])
            print("✅ Лист 'Users' создан")
        else:
            print("ℹ️ Лист 'Users' уже существует")

        # --- Лист Actions ---
        if 'Actions' not in existing_sheets:
            ws = spreadsheet.add_worksheet(title='Actions', rows=5000, cols=8)
            ws.append_row(['timestamp', 'user_id', 'first_name', 'username', 'action_type', 'action_details'])
            print("✅ Лист 'Actions' создан")
        else:
            print("ℹ️ Лист 'Actions' уже существует")

        print("✅ Google Sheets успешно инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации Google Sheets: {e}")
        raise

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ==========

def load_data():
    """Загружает всех пользователей из листа 'Users'. Возвращает dict {user_id: {...}}"""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet('Users')
        records = ws.get_all_records()  # список словарей, ключи = заголовки

        data = {}
        for row in records:
            uid = str(row.get('user_id', '')).strip()
            if uid:
                data[uid] = {
                    'name':     row.get('name', ''),
                    'username': row.get('username', ''),
                    'phone':    row.get('phone', ''),
                    'email':    row.get('email', ''),
                    'question': row.get('question', ''),
                    'feedback': row.get('feedback', ''),
                    'created_at': row.get('created_at', ''),
                }
        return data
    except Exception as e:
        print(f"❌ Ошибка загрузки пользователей: {e}")
        return {}

def save_user(user_id, user_data):
    """
    Сохраняет или обновляет пользователя в листе 'Users'.
    Если пользователь уже есть — обновляет строку, иначе добавляет новую.
    """
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet('Users')

        # Ищем существующую строку по user_id
        cell = ws.find(str(user_id), in_column=1)

        row_data = [
            str(user_id),
            user_data.get('name', ''),
            user_data.get('username', ''),
            user_data.get('phone', ''),
            user_data.get('email', ''),
            user_data.get('question', ''),
            user_data.get('feedback', ''),
            user_data.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ]

        if cell:
            # Обновляем существующую строку
            ws.update(f'A{cell.row}:H{cell.row}', [row_data])
        else:
            # Добавляем новую строку
            ws.append_row(row_data)

    except Exception as e:
        print(f"❌ Ошибка сохранения пользователя {user_id}: {e}")

def load_actions():
    """Загружает все действия из листа 'Actions'. Возвращает список словарей."""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet('Actions')
        records = ws.get_all_records()
        return records
    except Exception as e:
        print(f"❌ Ошибка загрузки действий: {e}")
        return []

def save_action(action_data):
    """Добавляет одно действие в лист 'Actions'."""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet('Actions')

        row_data = [
            action_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            str(action_data.get('user_id', '')),
            action_data.get('first_name', ''),
            action_data.get('username', ''),
            action_data.get('action_type', ''),
            str(action_data.get('action_details', '')),
        ]
        ws.append_row(row_data)

    except Exception as e:
        print(f"❌ Ошибка сохранения действия: {e}")

# ========== КОМАНДЫ АДМИН-БОТА ==========

@admin_bot.message_handler(commands=['start'])
def admin_start(message):
    text = """
🎛 Админ-панель ДельтаСтройПроект

Доступные команды:

📊 Информация:
/users - список всех пользователей
/stats - статистика бота
/actions - последние 10 действий
/user USER_ID - полная информация о пользователе
/find имя - поиск пользователя

💬 Управление:
/send USER_ID текст - отправить сообщение пользователю
/broadcast текст - отправить всем пользователям

❓ Помощь:
/help - подробная помощь
"""
    admin_bot.send_message(message.chat.id, text)

@admin_bot.message_handler(commands=['help'])
def admin_help(message):
    text = """
📖 Подробная помощь

════════════════════════════════════
📋 ПРОСМОТР ИНФОРМАЦИИ:

/users - список всех пользователей
Показывает всех пользователей с контактами

/user USER_ID - детали о пользователе
Показывает полную информацию и историю действий
Пример: /user 123456789

/find Иван - поиск пользователя
Ищет по имени или username
Пример: /find Петров

/stats - общая статистика
Количество пользователей, действий и т.д.

/actions - последние действия
Показывает последние 10 действий всех пользователей

════════════════════════════════════
💬 ОТПРАВКА СООБЩЕНИЙ:

/send USER_ID текст - отправить одному
Пример: /send 123456789 Здравствуйте! Ваша заявка принята

/broadcast текст - рассылка всем
Пример: /broadcast Уважаемые клиенты! Завтра выходной

════════════════════════════════════
💡 СОВЕТЫ:

1. Используйте /users чтобы узнать ID пользователя
2. Кликайте на /user команды в списке пользователей
3. Используйте /find для быстрого поиска
4. Перед рассылкой проверьте текст - придёт подтверждение
"""
    admin_bot.send_message(message.chat.id, text)

# ===== ПРОСМОТР ПОЛЬЗОВАТЕЛЕЙ =====

@admin_bot.message_handler(commands=['users'])
def show_users(message):
    admin_bot.send_message(message.chat.id, "⏳ Загружаю данные из Google Sheets...")
    data = load_data()

    if not data:
        admin_bot.send_message(message.chat.id, "📭 База пользователей пуста")
        return

    text = f"👥 Всего пользователей: {len(data)}\n\n"
    text += "Для просмотра деталей нажмите на команду\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for user_id, user_data in data.items():
        name = user_data.get('name', '❓')
        username = user_data.get('username', 'нет')
        phone = user_data.get('phone', 'не указан')

        text += f"👤 {name}\n"
        text += f"🆔 ID: {user_id}\n"
        text += f"📱 @{username} | ☎️ {phone}\n"
        text += f"📊 Детали: /user {user_id}\n"
        text += "━━━━━━━━━━━━━━━━\n\n"

    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            admin_bot.send_message(message.chat.id, part)
    else:
        admin_bot.send_message(message.chat.id, text)

# ===== СТАТИСТИКА =====

@admin_bot.message_handler(commands=['stats'])
def show_stats(message):
    admin_bot.send_message(message.chat.id, "⏳ Собираю статистику из Google Sheets...")
    data = load_data()
    actions = load_actions()

    total_users = len(data)
    users_with_phone = sum(1 for u in data.values() if u.get('phone'))
    users_with_email = sum(1 for u in data.values() if u.get('email'))
    total_actions = len(actions)

    today = datetime.now().strftime('%Y-%m-%d')
    today_actions = sum(1 for a in actions if str(a.get('timestamp', '')).startswith(today))

    action_types = {}
    for action in actions:
        action_type = action.get('action_type', 'unknown')
        action_types[action_type] = action_types.get(action_type, 0) + 1

    text = f"""
📊 Статистика бота

👥 Пользователи:
• Всего: {total_users}
• С телефоном: {users_with_phone}
• С email: {users_with_email}

📝 Действия:
• Всего: {total_actions}
• Сегодня: {today_actions}

📈 По типам:
"""

    type_names = {
        'command': '⌨️ Команды',
        'button_click': '🔘 Нажатия кнопок',
        'inline_button_click': '🔵 Inline-кнопки',
        'phone_provided': '📱 Телефоны',
        'email_provided': '📧 Email',
        'question_asked': '❓ Вопросы',
        'feedback_provided': '💬 Обратная связь',
        'phone_for_feedback': '📱 Телефон (обратная связь)',
        'email_for_feedback': '📧 Email (обратная связь)'
    }

    for action_type, count in action_types.items():
        type_name = type_names.get(action_type, action_type)
        text += f"• {type_name}: {count}\n"

    admin_bot.send_message(message.chat.id, text)

# ===== ПОСЛЕДНИЕ ДЕЙСТВИЯ =====

@admin_bot.message_handler(commands=['actions'])
def show_actions(message):
    admin_bot.send_message(message.chat.id, "⏳ Загружаю действия из Google Sheets...")
    actions = load_actions()

    if not actions:
        admin_bot.send_message(message.chat.id, "📭 Нет записанных действий")
        return

    recent = actions[-10:]
    recent.reverse()

    text = "📝 Последние 10 действий:\n\n"

    for action in recent:
        timestamp = action.get('timestamp', '?')
        name = action.get('first_name', '?')
        user_id = action.get('user_id', '?')
        action_type = action.get('action_type', '?')
        details = action.get('action_details', '?')

        if len(str(details)) > 50:
            details = str(details)[:50] + "..."

        text += f"⏰ {timestamp}\n"
        text += f"👤 {name} (ID: {user_id})\n"
        text += f"📌 {action_type}: {details}\n"
        text += "━━━━━━━━━━━━━━━━\n"

    admin_bot.send_message(message.chat.id, text)

# ===== ПРОСМОТР КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ =====

@admin_bot.message_handler(commands=['user'])
def show_user_info(message):
    try:
        parts = message.text.split()

        if len(parts) < 2:
            admin_bot.send_message(message.chat.id,
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "/user USER_ID\n\n"
                "Пример:\n"
                "/user 123456789\n\n"
                "Чтобы узнать ID используйте /users")
            return

        user_id = parts[1]
        admin_bot.send_message(message.chat.id, f"⏳ Загружаю данные пользователя {user_id}...")

        data = load_data()
        actions = load_actions()

        if user_id not in data:
            admin_bot.send_message(message.chat.id,
                f"❌ Пользователь {user_id} не найден в базе\n\n"
                f"Используйте /users для просмотра всех пользователей")
            return

        user_data = data[user_id]

        name = user_data.get('name', '❓')
        username = user_data.get('username', 'не указан')
        phone = user_data.get('phone', 'не указан')
        email = user_data.get('email', 'не указан')
        question = user_data.get('question', 'не задавал')
        feedback = user_data.get('feedback', 'не оставлял')

        if len(str(question)) > 100:
            question = str(question)[:100] + '...'
        if len(str(feedback)) > 100:
            feedback = str(feedback)[:100] + '...'

        user_actions = [a for a in actions if str(a.get('user_id', '')).strip() == str(user_id).strip()]

        text = f"""
👤 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Основные данные:
• Имя: {name}
• Username: @{username}
• ID: {user_id}

📞 Контакты:
• Телефон: {phone}
• Email: {email}

💬 Обращения:
• Вопрос: {question}
• Обратная связь: {feedback}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Статистика активности:
• Всего действий: {len(user_actions)}

"""
        admin_bot.send_message(message.chat.id, text)

        if user_actions:
            user_actions.sort(key=lambda x: str(x.get('timestamp', '')))

            history_text = f"📜 ИСТОРИЯ ДЕЙСТВИЙ ({name}):\n\n"

            type_icons = {
                'command': '⌨️',
                'button_click': '🔘',
                'inline_button_click': '🔵',
                'phone_provided': '📱',
                'email_provided': '📧',
                'question_asked': '❓',
                'feedback_provided': '💬',
                'phone_for_feedback': '📱',
                'email_for_feedback': '📧'
            }

            for i, action in enumerate(user_actions, 1):
                timestamp = action.get('timestamp', '?')
                action_type = action.get('action_type', '?')
                details = action.get('action_details', '?')

                if len(str(details)) > 50:
                    details = str(details)[:50] + "..."

                icon = type_icons.get(action_type, '📌')

                history_text += f"{i}. {icon} {timestamp}\n"
                history_text += f"   Тип: {action_type}\n"
                history_text += f"   Детали: {details}\n"
                history_text += "   ━━━━━━━━━━━━━━━━\n"

            if len(history_text) > 4000:
                parts_list = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
                for part in parts_list:
                    admin_bot.send_message(message.chat.id, part)
            else:
                admin_bot.send_message(message.chat.id, history_text)
        else:
            admin_bot.send_message(message.chat.id, "📭 У этого пользователя пока нет записанных действий")

    except Exception as e:
        admin_bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

# ===== ПОИСК ПОЛЬЗОВАТЕЛЯ =====

@admin_bot.message_handler(commands=['find'])
def find_user(message):
    try:
        parts = message.text.split(' ', 1)

        if len(parts) < 2:
            admin_bot.send_message(message.chat.id,
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "/find имя_или_username\n\n"
                "Примеры:\n"
                "/find Иван\n"
                "/find Петров\n"
                "/find ivan123")
            return

        search_query = parts[1].lower()
        admin_bot.send_message(message.chat.id, f"⏳ Ищу '{parts[1]}' в Google Sheets...")
        data = load_data()

        found = []
        for user_id, user_data in data.items():
            name = user_data.get('name', '').lower()
            username = user_data.get('username', '').lower()

            if search_query in name or search_query in username:
                found.append((user_id, user_data))

        if not found:
            admin_bot.send_message(message.chat.id,
                f"🔍 Пользователи с '{parts[1]}' не найдены\n\n"
                f"Попробуйте:\n"
                f"• Другое написание\n"
                f"• Часть имени\n"
                f"• Username без @")
            return

        text = f"🔍 Найдено пользователей: {len(found)}\n"
        text += f"Поиск по: '{parts[1]}'\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for user_id, user_data in found:
            name = user_data.get('name', '❓')
            username = user_data.get('username', 'нет')
            phone = user_data.get('phone', 'не указан')

            text += f"👤 {name}\n"
            text += f"🆔 ID: {user_id}\n"
            text += f"📱 @{username} | ☎️ {phone}\n"
            text += f"📊 Детали: /user {user_id}\n"
            text += "━━━━━━━━━━━━━━━━\n\n"

        admin_bot.send_message(message.chat.id, text)

    except Exception as e:
        admin_bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

# ===== ОТПРАВКА СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ =====

@admin_bot.message_handler(commands=['send'])
def send_to_user(message):
    try:
        parts = message.text.split(' ', 2)

        if len(parts) < 3:
            admin_bot.send_message(message.chat.id,
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "/send USER_ID текст сообщения\n\n"
                "Пример:\n"
                "/send 123456789 Здравствуйте! Ваша заявка принята в работу")
            return

        user_id = parts[1]
        text = parts[2]

        main_bot.send_message(user_id, text)

        admin_bot.send_message(message.chat.id,
            f"✅ Сообщение отправлено пользователю {user_id}\n\n"
            f"Текст:\n{text}")

    except Exception as e:
        admin_bot.send_message(message.chat.id,
            f"❌ Ошибка отправки: {str(e)}\n\n"
            f"Возможные причины:\n"
            f"• Неверный USER_ID\n"
            f"• Пользователь заблокировал бота\n"
            f"• Пользователь не запускал бота")

# ===== РАССЫЛКА ВСЕМ =====

@admin_bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    try:
        parts = message.text.split(' ', 1)

        if len(parts) < 2:
            admin_bot.send_message(message.chat.id,
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "/broadcast текст сообщения\n\n"
                "Пример:\n"
                "/broadcast Уважаемые клиенты! Завтра 23 февраля работаем до 18:00")
            return

        text = parts[1]
        admin_bot.send_message(message.chat.id, "⏳ Загружаю список пользователей...")
        data = load_data()

        if not data:
            admin_bot.send_message(message.chat.id, "📭 Нет пользователей для рассылки")
            return

        confirm_text = f"📢 РАССЫЛКА\n\n"
        confirm_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        confirm_text += f"Текст сообщения:\n{text}\n\n"
        confirm_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        confirm_text += f"Получателей: {len(data)}\n\n"
        confirm_text += f"⚠️ ВНИМАНИЕ!\n"
        confirm_text += f"Сообщение будет отправлено ВСЕМ пользователям!\n\n"
        confirm_text += f"Для подтверждения напишите: да\n"
        confirm_text += f"Для отмены напишите: нет"

        admin_bot.send_message(message.chat.id, confirm_text)
        admin_bot.register_next_step_handler(message,
            lambda m: confirm_broadcast(m, text, data))

    except Exception as e:
        admin_bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

def confirm_broadcast(message, text, data):
    if message.text.lower() not in ['да', 'yes', 'y']:
        admin_bot.send_message(message.chat.id, "❌ Рассылка отменена")
        return

    admin_bot.send_message(message.chat.id, "📤 Начинаю рассылку...\nЭто может занять некоторое время.")

    success = 0
    failed = 0
    failed_users = []

    for user_id in data.keys():
        try:
            main_bot.send_message(user_id, text)
            success += 1
        except Exception as e:
            failed += 1
            failed_users.append(user_id)
            print(f"Ошибка отправки {user_id}: {e}")

    result = f"✅ Рассылка завершена!\n\n"
    result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += f"📊 Результаты:\n"
    result += f"• Успешно: {success}\n"
    result += f"• Ошибок: {failed}\n\n"

    if failed > 0:
        result += f"⚠️ Не удалось отправить пользователям:\n"
        for uid in failed_users[:5]:
            result += f"• {uid}\n"
        if len(failed_users) > 5:
            result += f"• ... и ещё {len(failed_users) - 5}\n"

    admin_bot.send_message(message.chat.id, result)

# ===== ЗАПУСК =====

if __name__ == '__main__':
    print("🔗 Подключаюсь к Google Sheets...")
    init_sheets()  # Проверяем/создаём листы при старте
    print("🎛 Админ-бот запущен...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Доступные команды:")
    print("  /start - главное меню")
    print("  /users - список пользователей")
    print("  /user ID - информация о пользователе")
    print("  /find имя - поиск пользователя")
    print("  /stats - статистика")
    print("  /actions - последние действия")
    print("  /send ID текст - отправить сообщение")
    print("  /broadcast текст - рассылка")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    admin_bot.infinity_polling()


