import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import MessageHandler, filters, CallbackContext, Application, CommandHandler, CallbackQueryHandler, ContextTypes, PreCheckoutQueryHandler
import requests
import threading
import string
import asyncio
import random
import telegram
# Импортируем настройки и функцию для запуска слушателя
from paylistener import app as pay_listener_app
from helpers import send_telegram_message as send_telegram_message

service_host = "https://wgconfigs.cm-wp.com"
PROMOS_FILE = "promos/promocodes.json"


# тестовый бот 
bot_token = "1170371697:AAFngUiR70Z5Q0Z-aP0DVtCFyhH5Xe8Kv-A"

# рабочий бот 
# bot_token = "8086987257:AAFRF4z5v2Kv2lE-ZVUC5NWHSSF34GuirkU"
ALERTS_FILE = 'users/alerts.json'
USERS_FILE = 'users/users.json'
ADMIN_ID = [167176936, 771163041]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            # Считываем файл и создаём множество только из ID пользователей
            users_data = json.load(file)
            return set(user["id"] for user in users_data)  # Извлекаем только id
    except (FileNotFoundError, json.JSONDecodeError):
        return set()  # Если файл отсутствует или повреждён, возвращаем пустое множество
    
def save_users(users):
    # Преобразуем множество пользователей в список объектов с id и registered
    user_list = [{"id": user_id, "registered": datetime.now().strftime("%Y-%m-%d %H:%M")} for user_id in users]
    
    # Записываем данные в файл
    with open(USERS_FILE, "w") as file:
        json.dump(user_list, file, ensure_ascii=False, indent=4)  # Красивый вывод в файл

# Сохранение отправленных сообщений
def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as file:
        json.dump(alerts, file)
        
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Чтение данных из файла
        with open(USERS_FILE, 'r') as file:
            users = json.load(file)

        # Проверяем, что users - это список
        if isinstance(users, list):
            # Общее количество пользователей
            total_users = len(users)
            
            # Текущая дата
            today = datetime.now().date()
            
            # Подсчёт новых пользователей за день
            new_users_today = sum(
                1 for user in users 
                if "registered" in user and datetime.strptime(user["registered"], "%Y-%m-%d %H:%M").date() == today
            )

            # Формируем сообщение
            message = (
                f"Общее количество пользователей: {total_users}\n"
                f"Количество новых пользователей за день: {new_users_today}"
            )

            # Отправляем ответ
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Ошибка: users.json должен содержать список.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при считывании данных: {e}")

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
    if user_id not in ADMIN_ID:
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
    if user_id not in ADMIN_ID:
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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users = load_users()  # Загружаем список пользователей
    # await update.message.reply_text("Добро пожаловать!")  # Ответ пользователю
    
    if user_id in users:
        # Если пользователь уже зарегистрирован, показываем главное меню
        await show_main_menu(update)
    else:
        # Если пользователя нет в списке, ведем его на регистрацию
        await register_user(update, context)
        users.add(user_id)  # Добавляем пользователя
        save_users(users)  # Сохраняем обновленный список
    

# Главное меню
async def show_main_menu(update: Update) -> None:
    keyboard = [
        [InlineKeyboardButton("Купить VPN 🔥", callback_data='buy_vpn')],
        [InlineKeyboardButton("Мои VPN 📚", callback_data='list_vpn')],
        [InlineKeyboardButton("Поддержка ❓", callback_data='support')],
        [InlineKeyboardButton("Пробный период 🎁", callback_data='demo_version')],
        [InlineKeyboardButton("Инструкция к установке 📃", callback_data='instruction')],
        [InlineKeyboardButton("Ввести промокод ⚡", callback_data='check_promocode')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

# Регистрируем пользователя
async def register_user(update, context) -> None:
    user_id = update.effective_user.id

    # Формируем данные для отправки
    payload = {
        "id": user_id,
        "name": update.effective_user.first_name,
        "language": update.effective_user.language_code,
        "username": update.effective_user.username
    }
    
    # Выводим данные в терминал
    print("Отправляем на сервер следующие данные:", payload)

    # Отправляем запрос на сервер
    response = requests.post(
        f"{service_host}/wp-json/wireguard-service/register-user", 
        json=payload
    )

    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()
        
        if data.get("status") == "success":
           await show_main_menu(update)
           await context.bot.send_message(chat_id=update.message.chat_id, text=data.get("message"))
        else: 
           await context.bot.send_message(chat_id=update.message.chat_id, text=data.get("message"))
    else:
        # Сообщение об ошибке, если запрос на сервер не удался
        await context.bot.send_message(chat_id=update.message.chat_id, text="Неизвестная ошибка при регистрации пользователя! Обратитесь к администратору бота.")


async def buy(chat_id: int, context: CallbackContext, months: int, price: int):
    title = "Подписка StartVPN"
    description = f"Безлимитный доступ на {months} месяц(ев). Локация: Европа"
    payload = f"vpn_subscription_{months}"  # Уникальный payload для идентификации платежа
    currency = "XTR"  # Звёзды
    prices = [LabeledPrice(f"StartVPN ({months} мес.)", price)]  # Цена указывается в звёздах

    try:
        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token='',  # Для XTR токен не нужен
            currency=currency,
            prices=prices,
            start_parameter="start_vpn_subscription",
        )
        logging.info(f"Счёт отправлен: {title}, {price} XTR.")
    except Exception as e:
        logging.error(f"Ошибка при отправке счёта: {e}")
        raise e  # Генерируем исключение, чтобы оно обрабатывалось выше



async def precheckout_callback(update: Update, context: CallbackContext):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("vpn_subscription_"):
        await query.answer(ok=True)  # Успешно подтверждаем предоплату
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так...")


async def successful_payment_callback(update: Update, context: CallbackContext):
    # Получаем информацию о платеже
    payment = update.message.successful_payment
    telegram_payment_charge_id = payment.telegram_payment_charge_id
    user_id = update.message.from_user.id  # Получаем ID пользователя
    months = payment.invoice_payload.split("_")[2]  # Извлекаем количество месяцев из payload (если это часть уникального payload)

    # Ответ пользователю
    await update.message.reply_text(
    f"🎉 Поздравляем! 🎉\n"
    f"Ваш платёж успешно подтверждён! \n\n"
    f"🔑 Мы уже обрабатываем заказ и создаём для вас личные настройки.\n"
    f"👉 **ID платежа:** {telegram_payment_charge_id}\n\n"
    f"🕒 Создание QR занимает не более 1 минуты.\n\n"
    f"Большое спасибо за ваш заказ! 🚀"
)


    # Вызываем функцию для генерации конфигурации VPN
    try:
        await generate_vpn_config(user_id, months, update, context)
        logging.info(f"VPN конфигурация сгенерирована для пользователя {user_id} на {months} месяцев.")
    except Exception as e:
        logging.error(f"Ошибка при генерации конфигурации VPN для пользователя {user_id}: {e}")
        await update.message.reply_text("Произошла ошибка при создании конфигурации VPN. Пожалуйста, попробуйте позже.")




# Обработка выбора
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    
    await query.answer()
    
    if query.data == 'buy_vpn':
        await show_vpn_options(query)
    elif query.data == 'list_vpn':
      await list_vpn(query)
    elif query.data == 'back_to_main':
      await show_main_menu(update)
    elif query.data.startswith('buy_'):
        await process_purchase(query, context)
    elif query.data == 'support':
        await support_account(query)
    elif query.data == 'demo_version':
        await demo_version(query, context)
    elif query.data == 'instruction':
        await instruction(query)
    elif query.data == 'check_promocode':
        await promocode_button(update, context)

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

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import logging

async def process_purchase(query, context: CallbackContext) -> None:
    user_id = query.from_user.id

    # Карта тарифов
    tariff_map = {
        'buy_1_month': (1, 150, 150),
        'buy_2_month': (2, 300, 300),
        'buy_3_months': (3, 490, 490),
        'buy_6_months': (6, 880, 880),
    }

    # Проверяем, что выбранный тариф существует
    if query.data not in tariff_map:
        await query.edit_message_text("Выбранный тариф не найден. Пожалуйста, попробуйте снова.")
        return

    # Получаем параметры тарифа
    months, price, stars = tariff_map[query.data]
    description = f"Подписка на VPN на {months} месяц(ев)"

    logging.info(f"Пользователь {user_id} выбрал тариф: {query.data} на {months} месяц(ев) за {price} рублей или {stars} звёзд.")

    # Вызов функции `buy` для отправки счёта
    try:
        chat_id = query.message.chat_id  # Получаем ID чата из объекта CallbackQuery
        await buy(
            chat_id=chat_id,
            context=context,
            months=months,
            price=price,
        )
        await query.answer()  # Закрываем callback-запрос
    except Exception as e:
        logging.exception("Ошибка при вызове функции buy")
        await query.edit_message_text("Произошла системная ошибка! Пожалуйста, попробуйте позже.")



# Меню выбора срока подписки VPN
async def show_vpn_options(query) -> None:
    keyboard = [
        [InlineKeyboardButton("1 месяц (150⭐)", callback_data='buy_1_month')],
        [InlineKeyboardButton("2 месяца (300⭐)", callback_data='buy_2_month')],
        [InlineKeyboardButton("3 месяца (450⭐)", callback_data='buy_3_months')],
        [InlineKeyboardButton("6 месяцев (880⭐)", callback_data='buy_6_months')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите срок подписки:", reply_markup=reply_markup)


# Меню "Мой профиль"
# async def show_profile_menu(query) -> None:
#     keyboard = [
#         [InlineKeyboardButton("Узнать баланс", callback_data='check_balance')],
#         [InlineKeyboardButton("Список VPN", callback_data='list_vpn')],
#         [InlineKeyboardButton("Назад", callback_data='back_to_main')],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await query.edit_message_text("Выберите действие:", reply_markup=reply_markup)

async def support_account(query) -> None:
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
    instruction_url = "https://payway.store/vpn/"  # Замените на нужную вам ссылку

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
    

async def demo_version(query, context) -> None:
    
    user_id = query.from_user.id
    
    # Отправляем запрос на сервер
    response = requests.post(f"{service_host}/wp-json/wireguard-service/trial", 
        json={"id": user_id}
    )
    
    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()

        if data.get("status") == "success":
           instruction_url = "https://payway.store/vpn/"  # Замените на нужную вам ссылку

           await query.edit_message_text("Ваш триал успешно активирован!")
           await context.bot.sendPhoto(chat_id=query.message.chat_id, photo=data.get('qr_code_url'), caption=f"Инструкция, как использовать QR код. Читайте тут: {instruction_url}")
        else: 
           await context.bot.send_message(chat_id=query.message.chat_id, text=data.get("message"))
    else:
        # Сообщение об ошибке, если запрос на сервер не удался
        await context.bot.send_message(chat_id=query.message.chat_id, text="Неизвестная ошибка при активации триала! Обратитесь к администратору бота.")

    # Кнопка "Назад"
    await query.message.reply_text(
        "Вернуться в главное меню",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main')]])
    )
    

# Обработка проверки баланса
# async def check_balance(query) -> None:
#     user_id = query.from_user.id
    
#     # Отправляем POST запрос для получения баланса
#     response = requests.post(
#         "https://site.ru/get-balance",
#         json={"user_id": user_id}
#     )
    
#     if response.status_code == 200:
#         data = response.json()
#         balance = data.get("balance", "Неизвестный баланс")
#         await query.edit_message_text(f"Ваш баланс: {balance} рублей.")
#     else:
#         await query.edit_message_text("Не удалось получить баланс. Попробуйте позже.")


# async def handle_generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """
#     Обработчик команды /generate для генерации VPN-конфигурации.
#     """
#     user_id = update.effective_user.id
#     months = 1  # По умолчанию задаем 1 месяц

#     try:
#         # Логируем запрос
#         logging.info(f"Пользователь {user_id} запросил генерацию VPN на {months} месяц.")

#         # Вызываем функцию генерации конфигурации
#         await generate_vpn_config(user_id, months, update, context)

#     except Exception as e:
#         logging.error(f"Ошибка в обработчике команды /generate: {e}")
#         await context.bot.send_message(
#             chat_id=update.effective_chat.id,
#             text="Произошла ошибка при обработке вашего запроса. Попробуйте позже."
#         )


async def generate_vpn_config(user_id: int, months: int, update, context):
    """
    Генерация VPN-конфигурации для пользователя на указанное количество месяцев.
    """
    # Логирование информации
    logging.info(f"Генерация VPN-конфигурации для пользователя {user_id} на {months} месяцев.")

    # Отправляем POST-запрос на сервер
    response = requests.post(
        f"{service_host}/wp-json/wireguard-service/generate-config",
        json={"id": user_id, "months": months}
    )

    logging.info(f"Ответ от API: {response.json()}")

    # Проверяем успешность ответа
    if response.status_code == 200:
        data = response.json()

        if data.get("status") == "success":
            # Получаем URL QR-кода и инструкцию
            qr_code_url = data.get("qr_code_url")
            instruction_url = "https://payway.store/vpn/"  # Ссылка на инструкцию

            if qr_code_url:
                # Отправляем сообщение об успешной генерации
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Конфигурация VPN успешно создана!"
                )
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=qr_code_url,
                    caption=f"Инструкция, как использовать QR-код. Читайте тут: {instruction_url}"
                )
            else:
                logging.error("Не удалось получить URL QR-кода.")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Произошла ошибка при создании конфигурации VPN. Попробуйте позже."
                )
        else:
            # Обработка ошибок от сервера
            error_message = data.get("message", "Неизвестная ошибка.")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Ошибка: {error_message}"
            )
    else:
        # Обработка сетевых ошибок
        logging.error("Не удалось отправить запрос на создание конфигурации VPN.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Не удалось создать конфигурацию VPN. Попробуйте позже."
        )

    # Кнопка "Назад" в главное меню
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Вернуться в главное меню",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main')]])
    )



# Обработка списка VPN
async def list_vpn(query) -> None:
    user_id = query.from_user.id

    logging.info(f"тест")
    
    # Отправляем POST запрос для получения списка VPN
    response = requests.post(
        f"{service_host}/wp-json/wireguard-service/vpn-list",
        json={"id": user_id}
    )
    
    if response.status_code == 200:
        data = response.json()

        if data.get("status") == "success":
            orders = data.get("orders", [])

            keyboard = []
            
            for order in orders:
                logging.info(f"Order {order}")
                qr_code_url = order.get('qr_code_url')

                # Проверяем, что URL существует
                if qr_code_url:
                    keyboard.append([InlineKeyboardButton("VPN " + order.get('plan'), url=qr_code_url)])
                else:
                    logging.error(f"Invalid QR code URL for order {order}")
            
            # Добавляем кнопку "Назад"
            keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_main')])

            if keyboard:
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("Ваш список VPN: ", reply_markup=reply_markup)    
            else:
                await query.edit_message_text("Список VPN пуст или содержит некорректные URL.")   
        else: 
           await query.edit_message_text(data.get("message")) 
    else:
        await query.edit_message_text("Не удалось получить список VPN. Попробуйте позже.")
        

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

async def get_vpn_from_promo(months: int, user_id: int, update, context) -> None:
    try:
        # Отправляем запрос к сервису
        response = requests.post(
            f"{service_host}/wp-json/wireguard-service/promo-vpn",
            json={"id": user_id, "months": months}
        )

        # Проверяем успешность запроса
        if response.status_code == 200:
            response_data = response.json()  # Парсим JSON-ответ
            status = response_data.get("status")  # Получаем статус
            
            if status == "success":  # Успешный статус
                # Проверяем, содержит ли ответ изображение
                image_url = response_data.get("qr_code")  # Ожидаем URL изображения QR-кода
                if not image_url:
                    raise Exception("Похоже возникли проблему, напишите в поддежку для помощи.")

                # Скачиваем изображение QR-кода
                qr_image_response = requests.get(image_url)
                if qr_image_response.status_code != 200:
                    raise Exception("Не удалось загрузить изображение QR-кода.")

                # Отправляем сообщение с изображением и кнопками
                keyboard = [
                    [
                        InlineKeyboardButton("Инструкция", url='https://wgconfigs.cm-wp.com/'),
                        InlineKeyboardButton("Главное меню", callback_data="back_to_main")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Загружаем изображение в виде InputMediaPhoto
                qr_image = qr_image_response.content
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=qr_image,
                    caption=f"Поздравляем, ваш промокод активирован! Вот ваш QR-код на {months} месяц(а).",
                    reply_markup=reply_markup
                )
            else:
                raise Exception(f"Ошибка активации VPN: статус ответа - {status}")
        else:
            raise Exception(f"Ошибка запроса: код ответа {response.status_code}, сообщение: {response.text}")

    except requests.RequestException as e:
        # Обрабатываем ошибки сети или запроса
        await update.message.reply_text(f"Ошибка сети или запроса: {e}")
    except Exception as e:
        # Обрабатываем общие ошибки
        await update.message.reply_text(f"Произошла ошибка: {e}")


def generate_random_promo(length=8):
    """Генерирует случайный промокод длиной length, состоящий из букв и цифр."""
    characters = string.ascii_letters + string.digits  # Буквы и цифры
    return ''.join(random.choice(characters) for _ in range(length))

# Функция для генерации промокодов
async def generate_promo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверка прав администратора
    if update.message.from_user.id not in ADMIN_ID:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    try:
        # Получаем аргументы из команды
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Неверный формат команды. Используйте: /generate_promo <количество> <длительность>")
            return
        
        num_promos = int(args[0])  # Количество промокодов
        months = int(args[1])  # Длительность в месяцах
        
        # Генерация промокодов
        promos = {}
        for _ in range(num_promos):
            promo_code = generate_random_promo()  # Генерируем новый промокод
            promos[promo_code] = months  # Добавляем промокод в словарь
        
        # Чтение текущих промокодов из файла
        try:
            with open(PROMOS_FILE, "r") as file:
                existing_promos = json.load(file)
        except FileNotFoundError:
            existing_promos = {}
        
        # Добавляем новые промокоды в существующий файл
        existing_promos.update(promos)
        with open(PROMOS_FILE, "w") as file:
            json.dump(existing_promos, file, indent=4)

        # Формируем сообщение с успешными промокодами
        promo_list = "\n".join([f"{promo}: {months} месяц(а)" for promo in promos])
        await update.message.reply_text(f"Успешно! Вот ваши промокоды:\n{promo_list}")
    
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")


async def promocode_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашиваем у пользователя ввод промокода."""
    # Отправляем сообщение с просьбой ввести промокод
    keyboard = [
        [InlineKeyboardButton("Вернуться назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("Введите ваш промокод:", reply_markup=reply_markup)


async def handle_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текста с промокодом."""
    promocode = update.message.text.strip()
    user_id = update.effective_user.id  # Получаем ID пользователя

    try:
        # Чтение промокодов из файла
        with open(PROMOS_FILE, "r") as file:
            promos = json.load(file)

        # Проверяем наличие промокода
        if promocode in promos:
            months = promos[promocode]  # Количество месяцев для активации

            # Удаляем промокод (если он одноразовый)
            del promos[promocode]
            with open(PROMOS_FILE, "w") as file:
                json.dump(promos, file)

            # Вызываем функцию для активации VPN
            get_vpn_from_promo(months, user_id)  # Передаём количество месяцев и ID пользователя

            # Уведомляем пользователя об успешной активации
            await update.message.reply_text(f"Промокод успешно активирован! Вам предоставлен VPN на {months} месяц(а).")
        else:
            # Если промокод не найден
            await update.message.reply_text("Неверный промокод. Пожалуйста, попробуйте ещё раз.")

    except FileNotFoundError:
        # Если файл с промокодами не найден
        await update.message.reply_text("Файл с промокодами не найден. Обратитесь к администратору.")
    except json.JSONDecodeError:
        # Если файл повреждён
        await update.message.reply_text("Ошибка в файле с промокодами. Обратитесь к администратору.")
    except Exception as e:
        # Прочие ошибки
        await update.message.reply_text(f"Ошибка при обработке промокода: {e}")


promocode_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promocode)

def run_flask():
    app.run(host='0.0.0.0', port=5000) 

def main() -> None:

    # Создаем объект Application
    application = Application.builder().token(bot_token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("alert", send_alert))
    application.add_handler(CallbackQueryHandler(button))
    # application.add_handler(CallbackQueryHandler(check_balance, pattern="check_balance"))
    application.add_handler(CallbackQueryHandler(list_vpn, pattern="list_vpn"))
    application.add_handler(CommandHandler("delete_alert", delete_alert))  # Обработчик для удаления сообщения
    application.add_handler(CommandHandler('show_users', show_users))
    application.add_handler(CommandHandler("generate_promo", generate_promo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_promocode))  # Обработчик промокодов
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    # application.add_handler(CommandHandler("generate", handle_generate_command))

    # application.add_handler(CommandHandler("test_vpn", test_vpn_command))

    threading.Thread(target=pay_listener_app.run, kwargs={'host': '0.0.0.0', 'port': 5000}).start()

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':

    # Запускаем Telegram-бота
    main()