import hashlib
from urllib.parse import urlencode
import os
from datetime import datetime
import json
import logging
import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


#получаем id в соответствии с 
def get_next_order_number():
    filepath = "users/payhistory.json"

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)
            return len(data) + 1  # Порядковый номер = количество записей + 1
    else:
        return 1  # Если файл отсутствует, это будет первая запись


def save_payment_to_json(user_id, amount, description, tarif):
    filepath = "users/payhistory.json"

    # Получаем порядковый номер
    order_id = get_next_order_number()

    # Создаём структуру записи
    payment_data = {
        "order_id": order_id,           # Порядковый номер
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "status": 0,
        "tarif": tarif,
        "timestamp": datetime.now().isoformat()  # Время создания записи
    }

    # Если файл существует, загружаем данные, иначе создаём новый
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)  # Загружаем текущие записи
    else:
        data = []

    # Добавляем новую запись
    data.append(payment_data)

    # Сохраняем обновленные данные обратно в файл
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"Данные сохранены: {payment_data}")
    return order_id  # Возвращаем order_id для использования в InvId

# Генерируем ссылку на оплату
def generate_payment_link(order_id, amount, description):
    # Отправляем запрос на сервер
    response = requests.post(f"https://nicepay.io/public/api/payment", 
        json={
            "merchant_id": "674482886a8b3096fab446f2",
            "secret": "rmYsa-AbFLX-IS38w-m8a99-YGX1n",
            "order_id": order_id,
            "amount": amount*100,
            "customer": "alex.kovalevv@gmail.com",
            "currency": "RUB",
            "description": "Top up balance on website"
        }
    )

     # Проверяем успешность запроса
    if response.status_code == 200:
        data = response.json()

        result = data.get("data") 

        logger.info(f"Ответ: {data}")
    else:
        logger.info(f"Ошибка: {response.status_code}")    

    return result.get('link')