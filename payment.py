import hashlib
from urllib.parse import urlencode
import os
from datetime import datetime
import json


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


def generate_payment_link(user_id, amount, description, tarif):
    login = "Easyvpnbot"  # логин в Robokassa
    pass1 = "I93n6SoueLuvYr02dPVl"  # Первый пароль в Robokassa

    order_id = save_payment_to_json(user_id, amount, description, tarif)
    # Параметры запроса
    params = {
        "MerchantLogin": login,
        "OutSum": f"{amount:.2f}",  # Сумма платежа
        "InvId": order_id,      # Идентификатор заказа (InvId вместо InvId)
        "Description": description, # Описание заказа
        "IsTest": 1,                # Тестовый режим
    }
    
    # Формируем строку для подписи
    sign_string = f"{login}:{params['OutSum']}:{params['InvId']}:{pass1}"
    signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()  # Подпись в верхнем регистре

    # Добавляем подпись к параметрам
    params["SignatureValue"] = signature

    # Генерация URL на оплату
    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    payment_url = f"{base_url}?{urlencode(params)}"
    return payment_url
