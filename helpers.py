# Отправка сообщение по userid
async def send_telegram_message(user_id, message):
    """Отправка сообщения в Telegram пользователю."""
    bot = telegram.Bot(token=bot_token)  # Замените на ваш токен
    await bot.send_message(chat_id=user_id, text=message)