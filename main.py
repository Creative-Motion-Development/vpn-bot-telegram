import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests

ALERTS_FILE = 'users/alerts.json'
USERS_FILE = 'users/users.json'
ADMIN_ID = 167176936

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)
def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            return set(json.load(file))  # Возвращаем множество пользователей
    except (FileNotFoundError, json.JSONDecodeError):
        return set()  # Если файл отсутствует или поврежден, возвращаем пустое множество

# Функция для сохранения списка пользователей в JSON-файл
def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(list(users), file)  # Преобразуем множество в список для записи


# Сохранение отправленных сообщений
def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as file:
        json.dump(alerts, file)

# Загрузка отправленных сообщений
def load_alerts():
    try:
        with open(ALERTS_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    

# Обработка команды /alert (рассылка сообщения)
async def send_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем, что пользователь — администратор
    if user_id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для отправки рассылок.")
        return

    # Проверяем, что указан текст сообщения
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите сообщение для рассылки. Пример: /alert Текст сообщения")
        return

    alert_message = " ".join(context.args)  # Формируем текст рассылки
    users = load_users()  # Загружаем список пользователей

    # Загружаем список всех сообщений
    alerts = load_alerts()
    alert_id = len(alerts) + 1  # Уникальный ID сообщения

    # Список для хранения ID отправленных сообщений
    message_ids = []

    # Отправляем сообщение всем активным пользователям
    for user in users:
        try:
            sent_message = await context.bot.send_message(chat_id=user, text=alert_message)
            message_ids.append({"chat_id": user, "message_id": sent_message.message_id})
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user}: {e}")

    # Сохраняем информацию о рассылке
    alerts[str(alert_id)] = {
        "message": alert_message,
        "messages": message_ids
    }
    save_alerts(alerts)

    # Сообщаем администратору об успешной публикации
    await update.message.reply_text(f"Сообщение с ID {alert_id} опубликовано!")


# Обработка команды /delete_alert <id> (удаление сообщения)
async def delete_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем, что пользователь — администратор
    if user_id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для удаления сообщений.")
        return

    # Проверяем, что указан ID сообщения
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Пожалуйста, укажите ID сообщения. Пример: /delete_alert 1")
        return

    alert_id = context.args[0]  # ID сообщения
    alerts = load_alerts()  # Загружаем список всех сообщений

    # Проверяем, существует ли сообщение с таким ID
    if alert_id not in alerts:
        await update.message.reply_text(f"Сообщение с ID {alert_id} не найдено.")
        return

    # Удаляем сообщения из чатов пользователей
    alert = alerts[alert_id]
    for msg in alert["messages"]:
        try:
            await context.bot.delete_message(chat_id=msg["chat_id"], message_id=msg["message_id"])
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {msg}: {e}")

    # Удаляем запись из файла
    del alerts[alert_id]
    save_alerts(alerts)

    await update.message.reply_text(f"Сообщение с ID {alert_id} успешно удалено!")

# начальное сообщение
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    users = load_users()  # Загружаем список пользователей
    users.add(user_id)  # Добавляем пользователя
    save_users(users)  # Сохраняем обновленный список
    await update.message.reply_text("Добро пожаловать!")  # Ответ пользователю
    await show_main_menu(update)
    

# Главное меню
async def show_main_menu(update: Update) -> None:
    keyboard = [
        [InlineKeyboardButton("Купить VPN", callback_data='buy_vpn')],
        [InlineKeyboardButton("Мой профиль", callback_data='my_profile')],
        [InlineKeyboardButton("Поддержка", callback_data='support')],
        [InlineKeyboardButton("Пробный период", callback_data='demo_version')],
        [InlineKeyboardButton("Инструкция к установке", callback_data='instruction')],
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

# Обработка выбора
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'buy_vpn':
        await show_vpn_options(query)
    elif query.data == 'back_to_main':
        await show_main_menu(update)
    elif query.data.startswith('buy_'):
        await process_purchase(query)
    elif query.data == 'my_profile':
        await show_profile_menu(query)
    elif query.data == 'support':
        await support_account(query)
    elif query.data == 'demo_version':
        await demo_version(query)
    elif query.data == 'instruction':
        await instruction(query)

# Обработка покупки VPN
from datetime import datetime
from payment import generate_payment_link
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

#генерация коротко invoice_id
def generate_order_id(user_id: int) -> str:
    current_date = datetime.now()
    date_part = current_date.strftime("%d%m")  # День и месяц 
    user_part = str(user_id)[:3]  # Первые три цифры user_id
    return f"{date_part}{user_part}"

# Обработка покупки VPN
async def process_purchase(query) -> None:
    user_id = query.from_user.id
    tariff_map = {
        'buy_1_month': (1, 250),   # 1 месяц, цена 250 рублей
        'buy_3_months': (3, 450),  # 3 месяца, цена 450 рублей
        'buy_6_months': (6, 2000)   # 6 месяцев, цена 2000 рублей
    }

    if query.data in tariff_map:
        months, price = tariff_map[query.data]
        description = f"Подписка на VPN на {months} месяц(ев)"
        order_id = generate_order_id(user_id)
        # Генерируем ссылку на оплату
        payment_url = generate_payment_link(order_id=order_id, amount=price, description=description)
        
        # Отправляем сообщение с кнопкой для перехода на оплату
        keyboard = [
            [InlineKeyboardButton("Перейти к оплате", url=payment_url)],
            [InlineKeyboardButton("Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Стоимость подписки на {months} месяц(ев): {price} рублей.", reply_markup=reply_markup)
    else:
        await query.edit_message_text("Неверный выбор. Попробуйте снова.")
    
# Меню выбора срока подписки VPN
async def show_vpn_options(query) -> None:
    keyboard = [
        [InlineKeyboardButton("1 месяц (250₽)", callback_data='buy_1_month')],
        [InlineKeyboardButton("3 месяца (450₽)", callback_data='buy_3_months')],
        [InlineKeyboardButton("6 месяцев (2000₽)", callback_data='buy_6_months')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите срок подписки:", reply_markup=reply_markup)


# Меню "Мой профиль"
async def show_profile_menu(query) -> None:
    keyboard = [
        [InlineKeyboardButton("Узнать баланс", callback_data='check_balance')],
        [InlineKeyboardButton("Список VPN", callback_data='list_vpn')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите действие:", reply_markup=reply_markup)

async def support_account(query) -> None:
    # Создаем кнопку с ссылкой на @kotashov_dev
    keyboard = [
        [InlineKeyboardButton("Связаться с поддержкой", url="https://t.me/kotashov_dev")],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение с кнопкой
    await query.edit_message_text(
        "Если у вас возникли вопросы или проблемы, свяжитесь с поддержкой.",
        reply_markup=reply_markup
    )    

# Функция для отправки ссылки на инструкцию
async def instruction(query) -> None:
    # url
    instruction_url = "https://payway.store/instrukcija-dlja-polzovatelej-po-ustanovke-i-ispolzovaniju-vpn-servisa-na-osnove-wireguard-s-vydachej-kljuchej-cherez-telegram-bota/"  # Замените на нужную вам ссылку

    # Создаем кнопку-ссылку
    keyboard = [
        [InlineKeyboardButton("Перейти к инструкции", url=instruction_url)],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')]
        
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Редактируем текущее сообщение, чтобы отобразить ссылку
    await query.edit_message_text(
        "Вот ссылка на инструкцию. Нажмите на кнопку ниже, чтобы открыть:",
        reply_markup=reply_markup
    )
    

async def demo_version(query) -> None:
    user_id = query.from_user.id
    
    # Отправляем запрос на сервер
    response = requests.post("https://site.ru/get_free", json={"user_id": user_id})
    
    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()
        message = data.get("message", "Вот ваши файлы:")
        files = data.get("files", [])  # Предполагается, что сервер вернет список файлов
        
        # Отправляем текстовое сообщение пользователю
        await query.edit_message_text(message)
        
        # Проверяем и отправляем файлы, если они есть
        if files:
            for file_url in files:
                await query.message.reply_document(document=file_url)
        else:
            await query.message.reply_text("Файлы не найдены.")
    else:
        # Сообщение об ошибке, если запрос на сервер не удался
        await query.edit_message_text("Недоступно. Возможно вы уже получали пробную версию, либо свяжитесь с поддержкой")
    
    # Кнопка "Назад"
    await query.message.reply_text(
        "Вернуться в главное меню",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main')]])
    )
    

# Обработка проверки баланса
async def check_balance(query) -> None:
    user_id = query.from_user.id
    
    # Отправляем POST запрос для получения баланса
    response = requests.post(
        "https://site.ru/get-balance",
        json={"user_id": user_id}
    )
    
    if response.status_code == 200:
        data = response.json()
        balance = data.get("balance", "Неизвестный баланс")
        await query.edit_message_text(f"Ваш баланс: {balance} рублей.")
    else:
        await query.edit_message_text("Не удалось получить баланс. Попробуйте позже.")

# Обработка списка VPN
async def list_vpn(query) -> None:
    user_id = query.from_user.id
    
    # Отправляем POST запрос для получения списка VPN
    response = requests.post(
        "https://site.ru/get-vpn-list",
        json={"user_id": user_id}
    )
    
    if response.status_code == 200:
        data = response.json()
        vpn_list = data.get("vpn_list", [])
        if vpn_list:
            vpn_message = "Ваши VPN:\n" + "\n".join(vpn_list)
        else:
            vpn_message = "У вас нет активных VPN."
        await query.edit_message_text(vpn_message)
    else:
        await query.edit_message_text("Не удалось получить список VPN. Попробуйте позже.")

def main() -> None:
    # Токен бота
    bot_token = "1170371697:AAFngUiR70Z5Q0Z-aP0DVtCFyhH5Xe8Kv-A"

    # Создаем объект Application
    application = Application.builder().token(bot_token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("alert", send_alert))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(check_balance, pattern="check_balance"))
    application.add_handler(CallbackQueryHandler(list_vpn, pattern="list_vpn"))
    application.add_handler(CommandHandler("delete_alert", delete_alert))  # Обработчик для удаления сообщения

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()