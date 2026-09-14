import os
import re
import time
import json
import html
import threading
import requests
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
GOLDEN_KEY = "t1j669ik62280q9ubjuellcf7wzye7ca"

TRIGGER_SIGMA  = "СИГМЫ"
TRIGGER_ZIKO   = "RTxZIKO"
TRIGGER_HYZEN  = "ХАЙЗЕНА"
TRIGGER_GEMINI = "GEMINI"

TEXT_SIGMA = """Спасибо за покупку! 🎯 
Актуальный код чувствительности SIGMA:
[1-7592-1027-9533-6487-472]

Как активировать:
1. Зайди в настройки чувствительности в игре.
2. Нажми «Поиск метода / Ввести код».
3. Вставь полученный код и примени настройки.

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

TEXT_HYZEN = """Спасибо за покупку! 🎯 
Актуальный код чувствительности Хайзена:
[7368-3228-0493-8702-982]

Как активировать:
1. Зайди в настройки чувствительности в игре.
2. Нажми «Поиск метода / Ввести код».
3. Вставь полученный код и примени настройки.

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

TEXT_ZIKO = """Спасибо за покупку! 🎯 
Актуальный код чувствительности RTxZIKO:
[https://teletype.in/@dednain/CHPSDHnyEZG] 

После проверки подтвердите заказ и оставьте отзыв! Приятной игры! 🔥"""

TEXT_GEMINI = """Спасибо за покупку! 🎯 
Инструкция по настройке доступа к Google Gemini БЕЗ VPN:

1. Зайдите в «Настройки» телефона -> «Подключения» (или «Сеть и интернет»).
2. Откройте пункт «Другие настройки» -> «Персональный DNS-сервер» (Частный DNS).
3. Выберите «Имя хоста провайдера DNS» и впишите:
   xbox-dns.ru
4. Нажмите «Сохранить».

Готово! Теперь открывайте gemini.google.com напрямую без всяких VPN.

После проверки подтвердите заказ и оставьте отзыв! Приятного пользования! 🔥"""

processed_orders = set()

def get_delivery_message(description: str):
    if "чувствительность" in description.lower():
        return "SKIP_BUILTIN"

    desc_upper = description.upper()

    if TRIGGER_GEMINI in desc_upper:
        return TEXT_GEMINI
    elif TRIGGER_SIGMA in description or "SIGMA" in desc_upper:
        return TEXT_SIGMA
    elif TRIGGER_ZIKO in description or "RTXZIKO" in desc_upper or "ЗИКО" in desc_upper:
        return TEXT_ZIKO
    elif TRIGGER_HYZEN in description or "HYZEN" in desc_upper or "ХАЙЗЕН" in desc_upper:
        return TEXT_HYZEN

    return None

def start_auto_raise():
    time.sleep(20) # Даем время основному боту запуститься
    
    while True:
        try:
            print("[↑] Запуск проверки лотов для поднятия...")
            session = requests.Session()
            session.cookies.set("golden_key", GOLDEN_KEY)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            session.headers.update(headers)

            # 1. Загружаем главную страницу
            res = session.get("https://funpay.com/")
            
            # 2. Ищем скрытый csrf_token (защита FunPay от ботов)
            csrf_token = None
            app_data_m = re.search(r'data-app-data="([^"]+)"', res.text)
            if app_data_m:
                try:
                    app_data = json.loads(html.unescape(app_data_m.group(1)))
                    csrf_token = app_data.get("csrfToken")
                except:
                    pass
                    
            if not csrf_token:
                fallback_m = re.search(r'name="csrf_token"\s+value="([^"]+)"', res.text)
                if fallback_m:
                    csrf_token = fallback_m.group(1)

            # 3. Ищем ссылку на свой профиль
            user_m = re.search(r'href="(/users/\d+/)"', res.text)

            if not user_m or not csrf_token:
                print("[x] Не удалось найти профиль или csrf_token. Пробуем позже...")
                time.sleep(300)
                continue

            # 4. Идем в профиль, собираем категории
            prof_res = session.get("https://funpay.com" + user_m.group(1))
            categories = set(re.findall(r'/(lots|chips)/(\d+)/', prof_res.text))

            if not categories:
                print("[-] Категории для поднятия не найдены.")

            # 5. Поднимаем категории
            raise_headers = headers.copy()
            raise_headers["X-Requested-With"] = "XMLHttpRequest"

            for cat_type, node in categories:
                try:
                    page = session.get(f"https://funpay.com/{cat_type}/{node}/").text
                    game_m = re.search(r'data-game="(\d+)"', page)

                    payload = {
                        "node_id": node,
                        "csrf_token": csrf_token
                    }
                    if game_m:
                        payload["game_id"] = game_m.group(1)

                    r = session.post(f"https://funpay.com/{cat_type}/raise", data=payload, headers=raise_headers)
                    
                    try:
                        msg = r.json().get("msg", "Ок")
                        print(f"[↑] Категория {cat_type} #{node}: {msg}")
                    except:
                        print(f"[↑] Категория {cat_type} #{node}: Ответ сервера {r.status_code}")
                        
                except Exception as e:
                    print(f"[x] Ошибка при поднятии категории #{node}: {e}")
                
                time.sleep(3) # Пауза между поднятиями, чтобы не получить бан за спам

        except Exception as e:
            print(f"[x] Критическая ошибка автоподнятия: {e}")

        # FunPay разрешает поднимать не чаще раза в час/несколько часов. Ждем 1 час.
        print("[↑] Ждем 1 час до следующей попытки...")
        time.sleep(3600)

def start_bot_loop():
    while True:
        try:
            print("[+] Подключение к FunPay (Автовыдача)...")
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
                    print(f"[-] Заказ #{order_id} пропущен (работает сайт).")
                    processed_orders.add(order_id)
                    return

                if not delivery_text:
                    print(f"[-] Для заказа #{order_id} нет триггера.")
                    return

                try:
                    full_order = account.get_order(order_id)
                    account.send_message(full_order.chat_id, delivery_text)
                    processed_orders.add(order_id)
                    print(f"[✓] Успешно выдан товар #{order_id}!")
                except Exception as send_err:
                    print(f"[x] Ошибка отправки #{order_id}: {send_err}")

            runner.run()

        except Exception as err:
            print(f"[x] Сбой автовыдачи: {err}. Перезапуск через 15 сек...")
            time.sleep(15)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=start_bot_loop, daemon=True)
    bot_thread.start()

    raise_thread = threading.Thread(target=start_auto_raise, daemon=True)
    raise_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
