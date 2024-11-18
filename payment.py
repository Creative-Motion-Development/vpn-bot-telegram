import hashlib
from urllib.parse import urlencode

def generate_payment_link(order_id, amount, description):
    login = "Easyvpnbot"  # логин в Robokassa
    pass1 = "I93n6SoueLuvYr02dPVl"  # Первый пароль в Robokassa

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
