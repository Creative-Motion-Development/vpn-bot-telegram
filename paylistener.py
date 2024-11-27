import hashlib
from urllib.parse import parse_qs
from flask import Flask, request, redirect
import requests
import json

# Flask сервер
app = Flask(__name__)

# Ваш секретный пароль #2 из Robokassa
merchant_password_2 = "oJWAM9DB26UaUnTG4g3T"

# Файл, где хранятся записи о статусах платежей
PAYHISTORY_PATH = "users/payhistory.json"

# страница удачи
SUCCESS_URL = "https://your-success-page.com" 


def update_status(order_id: int, status: int):
    """Обновление статуса заказа в payhistory.json"""
    try:
        with open("users/payhistory.json", "r", encoding="utf-8") as f:
            payhistory = json.load(f)

        # Найти заказ по order_id
        order_found = False
        for order in payhistory:
            if order["order_id"] == order_id:
                order["status"] = status  # Обновляем статус
                order_found = True
                break

        if not order_found:
            raise ValueError(f"Заказ с order_id {order_id} не найден.")

        # Если статус отсутствует, добавляем его
        for order in payhistory:
            if "status" not in order:
                order["status"] = 0  # Можно добавить статус с дефолтным значением

        # Сохранить обновления в файл
        with open("users/payhistory.json", "w", encoding="utf-8") as f:
            json.dump(payhistory, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при обновлении статуса: {e}")

def load_payhistory():
    """Загружает историю оплат."""
    try:
        with open(PAYHISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_payhistory(data):
    """Сохраняет историю оплат."""
    with open(PAYHISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def parse_response(response: str) -> dict:
    """
    Парсит строку запроса в словарь параметров.
    :param response: строка запроса (например: OutSum=100.00&InvId=12345&SignatureValue=ABCDEF).
    :return: словарь параметров.
    """
    return {k: v[0] for k, v in parse_qs(response).items()}


def check_signature_result(inv_id: str, out_sum: str, signature: str, password_2: str) -> bool:
    """
    Проверяет подпись для ResultURL.
    :param inv_id: ID заказа.
    :param out_sum: Сумма заказа.
    :param signature: Подпись от Robokassa.
    :param password_2: Секретный пароль #2.
    :return: True, если подпись корректна.
    """
    sign_string = f"{out_sum}:{inv_id}:{password_2}"
    expected_signature = hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()
    return signature == expected_signature

from helpers import send_telegram_message as send_telegram_message
import asyncio
@app.route("/result", methods=["POST"])
def result_payment():
    param_request = request.form
    cost = param_request['OutSum']
    order_id = int(param_request['InvId'])
    signature = param_request['SignatureValue']

    # Проверка подписи
    if check_signature_result(order_id, cost, signature, merchant_password_2):
        # Если подпись верна, обновляем статус на 1 (успех)
        update_status(order_id, 1)
        print(f"Статус заказа {order_id} успешно обновлён на 1.")

        # Получаем user_id из payhistory.json
        try:
            with open("users/payhistory.json", "r", encoding="utf-8") as f:
                payhistory = json.load(f)

            user_id = None
            for order in payhistory:
                if order["order_id"] == order_id:
                    user_id = order["user_id"]
                    break

            if user_id:
                # Формируем сообщение
                message = f"Спасибо за оплату! Ваш заказ №{order_id} успешно обработан."

                # Вызываем асинхронную функцию для отправки сообщения
                asyncio.run(send_telegram_message(user_id, message))
                print(f"Сообщение отправлено пользователю {user_id}.")

        except Exception as e:
            print(f"Ошибка при обработке user_id или отправке сообщения: {e}")

        # Возвращаем ответ кассе
        return "OK", 200

    else:
        # проверяем подпись, меняем статус на 0 в случае неудачи
        update_status(order_id, 0)
        print(f"Ошибка оплаты: подпись неверна для заказа {order_id}.")
        return "bad sign", 400

@app.route("/success")
def success_payment():
    """Страница успешного платежа"""
    order_id = request.args.get('order_id')
    status = request.args.get('status')
    
    print(f"Заголовки: {dict(request.headers)}")  # Заголовки запроса
    print(f"Тело запроса: {request.data.decode('utf-8')}")  # Сырой текст тела запроса

    # Проверяем наличие параметров
    if not order_id or not status:
        return '{"error": "Некорректные параметры запроса"}', 400, {'Content-Type': 'application/json'}

    # Формируем JSON-ответ вручную
    response = f'{{"message": "Платеж по заказу {order_id} завершён успешно.", "status": "{status}"}}'
    return response, 200, {'Content-Type': 'application/json'}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
