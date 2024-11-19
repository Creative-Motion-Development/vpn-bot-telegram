import hashlib
import json
from flask import Flask, request

app = Flask(__name__)

# Конфигурация
MERCHANT_PASS2 = "oJWAM9DB26UaUnTG4g3T"  # Второй пароль Робокассы для проверки (Result URL)

def check_signature_result(order_id, cost, signature, merchant_password_2):
    """Проверка подписи"""
    sign_string = f"{cost}:{order_id}:{merchant_password_2}"
    expected_signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
    return signature == expected_signature

@app.route('/result', methods=['POST'])
def result_payment():
    """Обработка уведомления о платеже от Робокассы"""
    # Получаем параметры запроса от Робокассы
    param_request = request.form
    cost = param_request.get('OutSum')  # Сумма платежа
    order_id = param_request.get('InvId')  # Идентификатор заказа
    signature = param_request.get('SignatureValue')  # Подпись

    # Проверка подписи
    if check_signature_result(order_id, cost, signature, MERCHANT_PASS2):
        # Если подпись верная
        return f"OK{order_id}"
    else:
        # Если подпись неверная
        return "bad sign"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


def check_success_payment(merchant_password_1, request):
    """Проверка параметров успешной оплаты (для Success URL)"""
    param_request = request.form
    cost = param_request.get('OutSum')  # Сумма платежа
    order_id = param_request.get('InvId')  # Идентификатор заказа
    signature = param_request.get('SignatureValue')  # Подпись

    # Проверяем подпись
    if check_signature_result(order_id, cost, signature, merchant_password_1):
        return "Спасибо за использование нашего сервиса"
    else:
        return "bad sign"

@app.route('/success', methods=['GET'])
def success_payment():
    """Обработка успешного завершения операции"""
    param_request = request.args
    cost = param_request.get('OutSum')  # Сумма платежа
    order_id = param_request.get('InvId')  # Идентификатор заказа
    signature = param_request.get('SignatureValue')  # Подпись

    # Проверка подписи
    response = check_success_payment(MERCHANT_PASS2, param_request)
    return response
