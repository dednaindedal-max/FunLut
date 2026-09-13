import os
import time
import threading
from flask import Flask
from FunPayAPI.account import Account
from FunPayAPI.updater.runner import Runner
from FunPayAPI.updater.events import NewOrderEvent

app = Flask(__name__)

@app.route('/')
def index():
    return "FunPay Auto-Delivery Bot is active 24/7!"

# -------------------------------------------------------------
# ДАННЫЕ АВТОРИЗАЦИИ И ШАБЛОНЫ
# -------------------------------------------------------------
GOLDEN_KEY = "u578vcurj5wxi4vc0fjhcaulqn0qqb4t"

# ТОЧНЫЕ СЛОВА-ТРИГГЕРЫ ИЗ ТВОИХ ЛОТОВ
TRIGGER_SIGMA = "СИГМЫ"
TRIGGER_ZIKO  = "RTxZIKO"
TRIGGER_HYZEN = "ХАЙЗЕНА"

TEXT_SIGMA = """Спасибо за покупку! 🎯 
Актуальный код чувствительности SIGMA:
[1-7592-1027-9533-6487-472]

Как активировать:
1. Зайди в настройки чувствительности в игре.
2. Нажми «Поиск метода / Ввести код.
3. Вставь полученный код и примени настройки.

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

TEXT_HYZEN = """Спасибо за покупку! 🎯 
Актуальный код чувствительности Хайзена:
[7368-3228-0493-8702-982]

Как активировать:
1. Зайди в настройки чувствительности в игре.
2. Нажми «Поиск метода / Ввести код.
3. Вставь полученный код и примени настройки.

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

TEXT_ZIKO = """Спасибо за покупку! 🎯 
Актуальный код чувствительности RTxZIKO:
[https://teletype.in/@dednain/CHPSDHnyEZG] 

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

processed_orders = set()

def get_delivery_message(description: str):
    # 1. Если лот с синей молнией (Чувствительность) — отдаем встроенной автовыдаче FunPay
    if "чувствительность" in description.lower():
        return "SKIP_BUILTIN"

    # 2. Проверка по точным именам лотов из раздела Metro Royale
    if TRIGGER_SIGMA in description:
        return TEXT_SIGMA
    elif TRIGGER_ZIKO in description:
        return TEXT_ZIKO
    elif TRIGGER_HYZEN in description:
        return TEXT_HYZEN

    # Страховка на случай смены регистра (например, если в заказе буквы стали строчными)
    desc_upper = description.upper()
    if "СИГМЫ" in desc_upper or "SIGMA" in desc_upper:
        return TEXT_SIGMA
    elif "RTXZIKO" in desc_upper or "ZIKO" in desc_upper or "ЗИКО" in desc_upper:
        return TEXT_ZIKO
    elif "ХАЙЗЕНА" in desc_upper or "HYZEN" in desc_upper or "ХАЙЗЕН" in desc_upper:
        return TEXT_HYZEN

    return None

def start_bot_loop():
    while True:
        try:
            print("[+] Подключение к FunPay...")
            account = Account(GOLDEN_KEY).get()
            print(f"[✓] Успешно! Бот слушает заказы на аккаунте: {account.username}")

            runner = Runner(account)

            @runner.listen(NewOrderEvent)
            def on_new_order(event: NewOrderEvent):
                order_shortcut = event.order
                order_id = order_shortcut.id
                order_desc = order_shortcut.description or ""

                if order_id in processed_orders:
                    return

                print(f"[!] Новый заказ #{order_id}: {order_desc}")

                delivery_text = get_delivery_message(order_desc)

                if delivery_text == "SKIP_BUILTIN":
                    print(f"[-] Заказ #{order_id} пропущен (встроенная автовыдача FunPay).")
                    processed_orders.add(order_id)
                    return

                if not delivery_text:
                    print(f"[-] Для заказа #{order_id} не подошел ни один триггер: {order_desc}")
                    return

                try:
                    full_order = account.get_order(order_id)
                    account.send_message(full_order.chat_id, delivery_text)
                    processed_orders.add(order_id)
                    print(f"[✓] Успешно выдан товар по заказу #{order_id}!")
                except Exception as send_err:
                    print(f"[x] Ошибка при отправке в чат #{order_id}: {send_err}")

            runner.run()

        except Exception as err:
            print(f"[x] Сбой: {err}. Переподключение через 15 секунд...")
            time.sleep(15)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=start_bot_loop, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
