import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import payment
import requests


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# начальное сообщение
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
from payment import generate_payment_link
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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
        
        # Генерируем ссылку на оплату
        payment_url = generate_payment_link(order_id=f"{user_id}{months}", amount=price, description=description)
        
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
    application = Application.builder().token("1170371697:AAFngUiR70Z5Q0Z-aP0DVtCFyhH5Xe8Kv-A").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(check_balance, pattern='check_balance'))
    application.add_handler(CallbackQueryHandler(list_vpn, pattern='list_vpn'))

    application.run_polling()

if __name__ == "__main__":
    main()
