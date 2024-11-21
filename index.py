import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
import io

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
        await process_purchase(query, context)
    elif query.data == 'my_profile':
        await show_profile_menu(query)

# Меню выбора срока подписки VPN
async def show_vpn_options(query) -> None:
    keyboard = [
        [InlineKeyboardButton("1 месяц", callback_data='buy_1_month')],
        [InlineKeyboardButton("3 месяца", callback_data='buy_3_months')],
        [InlineKeyboardButton("6 месяцев", callback_data='buy_6_months')],
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

# Обработка покупки VPN
async def process_purchase(query, context) -> None:
    user_id = query.from_user.id
    tariff_map = {
        'buy_1_month': 1,
        'buy_3_months': 2,
        'buy_6_months': 3
    }
    tariff_id = tariff_map[query.data]

    #logging.info(f"user_id: {user_id}, chat_id: {query.message.chat_id}")
    
    # Отправляем POST запрос
    response = requests.post(
        "http://wgconfgs.astraholod.ru/wp-json/wg-control/conf-buy",
        json={"user_id": user_id, "tariff_id": tariff_id}
    )

    logging.info(f"Ответ {response}")
    
    # Обрабатываем ответ от сервера
    if response.status_code == 200:
        #data = response.json()
        #message = data.get("message", "Спасибо за покупку!")

        logging.info(f"Отправка фото")

        qr_code = io.BytesIO(response.content)

        await context.bot.sendPhoto(chat_id=query.message.chat_id, photo=qr_code, caption="Инструкция, как использовать QR код.")
        
        # Отправляем сообщение
        await query.edit_message_text("Спасибо за покупку!")
    
    else:
        await query.edit_message_text("Произошла ошибка, попробуйте позже.")
    
    # Добавляем кнопку "Назад" к сообщению после завершения покупки
    await query.message.reply_text(
        "Вернуться в главное меню",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_main')]])
    )

def main() -> None:
    application = Application.builder().token("7425895674:AAH7PJWE7PgCodh5fxEo3K_udthJdXp4j6g").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(check_balance, pattern='check_balance'))
    application.add_handler(CallbackQueryHandler(list_vpn, pattern='list_vpn'))

    application.run_polling()

if __name__ == "__main__":
    main()
