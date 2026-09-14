import os
import re
import html
import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask
from FunPayAPI.account import Account
from FunPayAPI.updater.runner import Runner
from FunPayAPI.updater.events import NewOrderEvent

app = Flask(__name__)

@app.route('/')
def index():
    return "FunPay Auto-Delivery & Auto-Raise Bot is active 24/7!"

# -------------------------------------------------------------
# ДАННЫЕ АККАУНТА И ШАБЛОНЫ ВЫДАЧИ
# -------------------------------------------------------------
GOLDEN_KEY = "t1j669ik62280q9ubjuellcf7wzye7ca"
USER_ID    = "18024937"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

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

def fetch_valid_csrf(session):
    try:
        res = session.get("https://funpay.com/", headers={"User-Agent": USER_AGENT})
        m = re.search(r'data-app-data="([^"]+)"', res.text)
        if m:
            app_data = json.loads(html.unescape(m.group(1)))
            token = app_data.get("csrfToken") or app_data.get("csrf-token")
            if token:
                return token
        m2 = re.search(r'["\']csrfToken["\']\s*:\s*["\']([a-f0-9]+)["\']', res.text, re.IGNORECASE)
        if m2:
            return m2.group(1)
    except Exception as e:
        print(f"[x] Не удалось извлечь csrf-токен: {e}", flush=True)
    return None

# -------------------------------------------------------------
# АВТОПОДНЯТИЕ ЛОТОВ
# -------------------------------------------------------------
def start_auto_raise():
    time.sleep(10)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest"
    }

    while True:
        try:
            print("[↑] Проверка лотов для поднятия...", flush=True)
            prof_res = session.get(f"https://funpay.com/users/{USER_ID}/", headers={"User-Agent": USER_AGENT})
            categories = set(re.findall(r"/(lots|chips)/(\d+)/", prof_res.text))

            raised_games = set()

            for cat_type, node in categories:
                try:
                    cat_page = session.get(f"https://funpay.com/{cat_type}/{node}/", headers={"User-Agent": USER_AGENT}).text
                    game_m = re.search(r'data-game="(\d+)"', cat_page)
                    
                    payload = {"node_id": node}
                    if game_m:
                        game_id = game_m.group(1)
                        if game_id in raised_games:
                            continue
                        payload["game_id"] = game_id

                    r1 = session.post(f"https://funpay.com/{cat_type}/raise", data=payload, headers=headers)
                    res_json = r1.json()

                    if "modal" in res_json:
                        soup = BeautifulSoup(res_json["modal"], "html.parser")
                        raise_box = soup.find("div", class_="raise-box")
                        if raise_box:
                            g_id = raise_box.get("data-game", payload.get("game_id"))
                            main_node = raise_box.get("data-node", node)
                            checkboxes = [inp.get("value") for inp in soup.find_all("input", type="checkbox") if inp.get("value")]

                            post_data = {
                                "game_id": g_id,
                                "node_id": main_node,
                                "node_ids[]": checkboxes if checkboxes else [node]
                            }
                            r2 = session.post(f"https://funpay.com/{cat_type}/raise", data=post_data, headers=headers)
                            res_json = r2.json()
                            if g_id:
                                raised_games.add(g_id)

                    msg = res_json.get("msg", "Запрос обработан")
                    print(f"[↑] {cat_type} #{node}: {msg}", flush=True)

                except Exception as node_err:
                    print(f"[x] Ошибка категории #{node}: {node_err}", flush=True)

                time.sleep(3)

        except Exception as e:
            print(f"[x] Ошибка автоподнятия: {e}", flush=True)

        time.sleep(3600)

# -------------------------------------------------------------
# АВТОВЫДАЧА ТОВАРОВ
# -------------------------------------------------------------
def start_bot_loop():
    while True:
        try:
            print("[+] Подключение к FunPay (Автовыдача)...", flush=True)
            account = Account(GOLDEN_KEY, user_agent=USER_AGENT).get()
            
            # Принудительно передаем валидный csrfToken в сессию аккаунта
            csrf = fetch_valid_csrf(account.session)
            if csrf:
                account.csrf_token = csrf
                print(f"[✓] Актуальный CSRF-токен применен: {csrf[:6]}***", flush=True)

            print(f"[✓] Успешно! Бот слушает заказы на аккаунте: {account.username}", flush=True)

            runner = Runner(account)

            for event in runner.listen(requests_delay=4):
                if isinstance(event, NewOrderEvent):
                    order_shortcut = event.order
                    order_id = order_shortcut.id
                    order_desc = order_shortcut.description or ""

                    if order_id in processed_orders:
                        continue

                    print(f"[!] Новый заказ #{order_id}: {order_desc}", flush=True)
                    delivery_text = get_delivery_message(order_desc)

                    if delivery_text == "SKIP_BUILTIN":
                        print(f"[-] Заказ #{order_id} пропущен (встроенная автовыдача).", flush=True)
                        processed_orders.add(order_id)
                        continue

                    if not delivery_text:
                        print(f"[-] Для заказа #{order_id} нет триггера: {order_desc}", flush=True)
                        continue

                    try:
                        full_order = account.get_order(order_id)
                        account.send_message(full_order.chat_id, delivery_text)
                        processed_orders.add(order_id)
                        print(f"[✓] Успешно выдан товар по заказу #{order_id}!", flush=True)
                    except Exception as send_err:
                        print(f"[x] Ошибка отправки #{order_id}: {send_err}", flush=True)

        except Exception as err:
            print(f"[x] Сбой автовыдачи: {err}. Перезапуск через 15 сек...", flush=True)
            time.sleep(15)

if __name__ == '__main__':
    threading.Thread(target=start_bot_loop, daemon=True).start()
    threading.Thread(target=start_auto_raise, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
