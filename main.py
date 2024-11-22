import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import threading
import asyncio
import random
# Импортируем настройки и функцию для запуска слушателя
from paylistener import app as pay_listener_app

service_host = "https://d234-77-246-99-197.ngrok-free.app"
bot_token = "7425895674:AAH7PJWE7PgCodh5fxEo3K_udthJdXp4j6g"
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

import telegram

# Отправка сообщение по userid
async def send_telegram_message(user_id, message):
    """Отправка сообщения в Telegram пользователю."""
    bot = telegram.Bot(token=bot_token)  # Замените на ваш токен
    await bot.send_message(chat_id=user_id, text=message)
    
    
# получения конфигов с прослойки
def get_vpn_config(user_id, tarif, invid):
    """Отправка запроса на сайт для получения настроек VPN и отправка ответа пользователю."""
    url = "https://site.ru/get_vpn_config"  # заменить на наш url
    secret = "1111"  # @todo сгенерировать новый

    # Данные, которые отправляем в запросе
    data = {
        "inv_id": invid,
        "secret": secret,
        "userId": user_id,
        "tarif": tarif
    }

    try:
        # Отправка POST запроса на сайт
        response = requests.post(url, data=data)
        
        # Проверка, что запрос прошел успешно
        if response.status_code == 200:
            # Проверяем, есть ли файлы в ответе
            files = response.files  # Предполагается, что файлы передаются в response.files
            if files:
                file_links = []  # Список для хранения имен файлов

                # Обрабатываем каждый файл
                for file_key, file_obj in files.items():
                    file_name = file_obj.filename  # Получаем имя файла
                    with open(file_name, 'wb') as f:
                        f.write(file_obj.read())  # Сохраняем файл на диск
                    file_links.append(file_name)

                # Формируем сообщение для пользователя
                success_message = (
                    "Поздравляем с покупкой! Вот ваши файлы:\n" +
                    "\n".join([f"• [{file}](/{file})" for file in file_links])  # Генерация ссылок
                )

                # Добавляем кнопку "Инструкция по установке"
                instructions_button = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Инструкция по установке", url="https://site.ru/instructions")]]
                )

                send_telegram_message(user_id, success_message, reply_markup=instructions_button)  # Отправка сообщения
                return "Файлы успешно отправлены пользователю."
            else:
                error_message = "Файлы не найдены, попробуйте позже."
                send_telegram_message(user_id, error_message)  # Сообщение об ошибке
                return error_message
        else:
            error_message = f"Ошибка при получении данных. Код ответа: {response.status_code}"
            send_telegram_message(user_id, error_message)  # Сообщение об ошибке
            return error_message

    except Exception as e:
        error_message = f"Произошла ошибка: {str(e)}"
        send_telegram_message(user_id, error_message)  # Сообщение об ошибке
        return error_message

    

async def test_vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = random.randint(1, 9999)
    tarif = 1
    invid = random.randint(1, 1000)

    # Выполняем синхронную функцию get_vpn_config в отдельном потоке
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, get_vpn_config, user_id, tarif, invid)

    # Отправляем результат в чат
    await update.message.reply_text(result)


    
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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    users = load_users()  # Загружаем список пользователей
    users.add(user_id)  # Добавляем пользователя
    save_users(users)  # Сохраняем обновленный список
    # await update.message.reply_text("Добро пожаловать!")  # Ответ пользователю
    
    await register_user(update, context)
    

# Главное меню
async def show_main_menu(update: Update) -> None:
    keyboard = [
        [InlineKeyboardButton("Купить VPN 🔥", callback_data='buy_vpn')],
        [InlineKeyboardButton("Мои VPN 📚", callback_data='list_vpn')],
        [InlineKeyboardButton("Поддержка ❓", callback_data='support')],
        [InlineKeyboardButton("Пробный период 🎁", callback_data='demo_version')],
        [InlineKeyboardButton("Инструкция к установке 📃", callback_data='instruction')],
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

# Регистрируем пользователя
async def register_user(update, context) -> None:

    #logging.info(update)
    #logging.info(context)
    
    user_id = update.effective_user.id
    
    # Отправляем запрос на сервер
    response = requests.post(
        f"{service_host}/wp-json/wireguard-service/register-user", 
        json={
            "id": update.effective_user.id, 
            "name": update.effective_user.first_name, 
            "language": update.effective_user.language_code,
            "username": update.effective_user.username
        })

    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()
        
        logging.info(f"Ответ {data.get("status")}")

        if data.get("status") == "success":
           await show_main_menu(update)
        else: 
           await context.bot.send_message(chat_id=update.message.chat_id, text=data.get("message"))
    else:
        # Сообщение об ошибке, если запрос на сервер не удался
        await context.bot.send_message(chat_id=update.message.chat_id, text="Неизвестная ошибка при регистрации пользователя! Обратитесь к администратору бота.")


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
        await process_purchase(query)
    elif query.data == 'support':
        await support_account(query)
    elif query.data == 'demo_version':
        await demo_version(query, context)
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
        'buy_1_month': (1, 290),   # 1 месяц, цена 250 рублей
        'buy_2_month': (2, 520),   # 2 месяц, цена 250 рублей
        'buy_3_months': (3, 780),  # 3 месяца, цена 450 рублей
        'buy_6_months': (6, 1500)   # 6 месяцев, цена 2000 рублей
    }

    if query.data in tariff_map:
        months, price = tariff_map[query.data]
        description = f"Подписка на VPN на {months} месяц(ев)"
        #order_id = generate_order_id(user_id)

    logging.info(f"DATA {query.data}")

    # Отправляем запрос на сервер
    response = requests.post(f"{service_host}/wp-json/wireguard-service/create_order", 
        json={"id": user_id, 'plan': query.data}
    )
    
    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()
    
        logging.info(f"Ответ {data.get("status")}")

        if data.get("status") == "success":
            order_id=data.get("order_id")

            # Генерируем ссылку на оплату
            payment_url = generate_payment_link(
                order_id, # ID заказа
                user_id,  # ID пользователь в телеграм
                price,    # Стоимость тарифного плана
                description, # Описание
                months, # Количестов месяцев (тариф)
                query.message.chat_id # Chat ID, нужен для отправки ответа с прослойки
            )
            
            # Отправляем сообщение с кнопкой для перехода на оплату
            keyboard = [
                [InlineKeyboardButton("Перейти к оплате", url=payment_url)],
                [InlineKeyboardButton("Назад", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Стоимость подписки на {months} месяц(ев): {price} рублей.", reply_markup=reply_markup)
        else: 
           await query.edit_message_text({data.get("message")})
    
    else:
        await query.edit_message_text("Произошла неизвестная ошибка при создании заказа! Обратитесь к администратору бота.")
    
    
# Меню выбора срока подписки VPN
async def show_vpn_options(query) -> None:
    keyboard = [
        [InlineKeyboardButton("1 месяц (290₽)", callback_data='buy_1_month')],
        [InlineKeyboardButton("2 месяца (520₽)", callback_data='buy_2_month')],
        [InlineKeyboardButton("3 месяца (780₽)", callback_data='buy_3_months')],
        [InlineKeyboardButton("6 месяцев (1500₽)", callback_data='buy_6_months')],
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
    

async def demo_version(query, context) -> None:
    
    user_id = query.from_user.id
    
    # Отправляем запрос на сервер
    response = requests.post(f"{service_host}/wp-json/wireguard-service/trial", 
        json={"id": user_id}
    )
    
    # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()
    
        logging.info(f"Ответ {data.get("status")}")

        if data.get("status") == "success":
           instruction_url = "https://payway.store/instrukcija-dlja-polzovatelej-po-ustanovke-i-ispolzovaniju-vpn-servisa-na-osnove-wireguard-s-vydachej-kljuchej-cherez-telegram-bota/"  # Замените на нужную вам ссылку

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

        logging.info(f"Ответ {data.get("status")}")

        if data.get("status") == "success":
            orders = data.get("orders", [])

            keyboard = []
            
            for order in orders:
                logging.info(f"Order {order}")
                keyboard.append([InlineKeyboardButton("VPN " + order.get('plan'), url=order.get('qr_code_url'))])
                
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Ваш список VPN: ", reply_markup=reply_markup)    
        else: 
           await query.edit_message_text(data.get("message")) 
    else:
        await query.edit_message_text("Не удалось получить список VPN. Попробуйте позже.")

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
    application.add_handler(CommandHandler("test_vpn", test_vpn_command))

    threading.Thread(target=pay_listener_app.run, kwargs={'host': '0.0.0.0', 'port': 5000}).start()

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':

    # Запускаем Telegram-бота
    main()