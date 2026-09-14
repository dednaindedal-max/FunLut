import os
import re
import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "FunPay Smart Auto-Delivery & Auto-Raise Bot is active 24/7!"

# -------------------------------------------------------------
# НАСТРОЙКИ АККАУНТА И ТРИГГЕРЫ
# -------------------------------------------------------------
GOLDEN_KEY = "t1j669ik62280q9ubjuellcf7wzye7ca"
USER_ID    = "18024937"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

TRIGGER_OPTIMIZATION = "ОПТИМИЗАЦИЯ"
TRIGGER_SIGMA        = "СИГМЫ"
TRIGGER_ZIKO         = "RTxZIKO"
TRIGGER_HYZEN        = "ХАЙЗЕНА"
TRIGGER_GEMINI       = "GEMINI"

TEXT_OPTIMIZATION = """✴ Спасибо за покупку!
Ссылка на премиум оптимизацию: https://docs.google.com/document/d/1MG8WVM1rfODUX50DRVJd2wZ8jER7cfsxE6vS_aaomtM/edit?usp=sharing
✴ Настройте, перезагрузите ПК и оставьте отзыв 5★!"""

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
replied_check_messages = set()

def get_delivery_message(description: str):
    desc_upper = description.upper()

    opt_keywords = [TRIGGER_OPTIMIZATION, "OPTIMIZATION", "FPS", "ФПС", "ПРЕМИУМ", "PREMIUM"]
    if any(k in desc_upper for k in opt_keywords):
        return TEXT_OPTIMIZATION

    if TRIGGER_GEMINI in desc_upper:
        return TEXT_GEMINI

    if TRIGGER_SIGMA in description or "SIGMA" in desc_upper:
        return TEXT_SIGMA
    elif TRIGGER_ZIKO in description or "RTXZIKO" in desc_upper or "ЗИКО" in desc_upper:
        return TEXT_ZIKO
    elif TRIGGER_HYZEN in description or "HYZEN" in desc_upper or "ХАЙЗЕН" in desc_upper:
        return TEXT_HYZEN

    return None

# -------------------------------------------------------------
# НАДЕЖНАЯ ОТПРАВКА СООБЩЕНИЙ ЧЕРЕЗ RUNNER
# -------------------------------------------------------------
def send_chat_runner_message(session, page_url: str, message_text: str):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    resp = session.get(page_url, headers=headers, timeout=12)
    page_html = resp.text
    soup_order = BeautifulSoup(page_html, "html.parser")

    csrf_m = re.search(r'csrf-token&quot;:&quot;([^&]+)&quot;', page_html) or re.search(r'name="csrf_token"\s+value="([^"]+)"', page_html)
    if not csrf_m:
        return False
    csrf_token = csrf_m.group(1)

    chat_div = soup_order.find("div", attrs={"data-id": True, "data-tag": True})
    if chat_div:
        node_id = int(chat_div["data-id"])
        tag = chat_div.get("data-tag", "")
    else:
        node_m = re.search(r'data-id="(\d+)"', page_html)
        tag_m = re.search(r'data-tag="([^"]+)"', page_html)
        if not node_m:
            return False
        node_id = int(node_m.group(1))
        tag = tag_m.group(1) if tag_m else ""

    msg_ids = re.findall(r'id="message-(\d+)"', page_html)
    last_msg_id = int(msg_ids[-1]) if msg_ids else 0

    runner_payload = {
        "objects": json.dumps([{
            "type": "chat_node",
            "id": node_id,
            "tag": tag,
            "data": {
                "node": node_id,
                "last_message": last_msg_id,
                "content": ""
            }
        }]),
        "request": json.dumps({
            "action": "chat_message",
            "data": {
                "node": node_id,
                "last_message": last_msg_id,
                "content": message_text
            }
        }),
        "csrf_token": csrf_token
    }

    runner_headers = {
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": page_url
    }

    post_resp = session.post("https://funpay.com/runner/", data=runner_payload, headers=runner_headers, timeout=12)
    return post_resp.status_code == 200

# -------------------------------------------------------------
# ЦИКЛ АВТОВЫДАЧИ И ТЕСТОВОЙ КОМАНДЫ %1
# -------------------------------------------------------------
def start_bot_loop():
    time.sleep(5)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    print("[+] Синхронизация заказов...", flush=True)
    try:
        res = session.get("https://funpay.com/orders/trade", headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        for item in soup.find_all("a", class_=re.compile(r"tc-item")):
            status_div = item.find("div", class_=re.compile(r"tc-status"))
            st = status_div.get_text(strip=True).lower() if status_div else ""
            if any(s in st for s in ["закрыт", "отменен", "возврат"]):
                m = re.search(r"/orders/([A-Z0-9]+)/", item.get("href", ""))
                if m:
                    processed_orders.add(m.group(1))
        print(f"[✓] Загружено {len(processed_orders)} прошлых завершенных заказов. Мониторинг запущен!", flush=True)
    except Exception as e:
        print(f"[x] Ошибка при старте: {e}", flush=True)

    while True:
        # 1. Проверка команды %1 в сообщениях
        try:
            r_chat = session.get("https://funpay.com/chat/", headers=headers, timeout=10)
            s_chat = BeautifulSoup(r_chat.text, "html.parser")
            for c_item in s_chat.find_all("a", class_=re.compile(r"chat-item"))[:5]:
                preview = c_item.find(class_=re.compile(r"chat-item-text"))
                if preview and "%1" in preview.get_text():
                    node_id = c_item.get("data-id")
                    if not node_id:
                        m_node = re.search(r'node=(\d+)', c_item.get("href", ""))
                        node_id = m_node.group(1) if m_node else None

                    if node_id:
                        chat_url = f"https://funpay.com/chat/?node={node_id}"
                        chat_page = session.get(chat_url, headers=headers, timeout=10).text
                        soup_cp = BeautifulSoup(chat_page, "html.parser")
                        messages = soup_cp.find_all("div", class_=re.compile(r"chat-msg-item"))
                        if messages:
                            last_msg = messages[-1]
                            last_id = last_msg.get("id", "")
                            last_text = last_msg.find(class_=re.compile(r"chat-msg-text"))
                            if last_text and "%1" in last_text.get_text() and last_id not in replied_check_messages:
                                print(f"[!] Получена команда %1 в диалоге {node_id}! Отправка ответа...", flush=True)
                                if send_chat_runner_message(session, chat_url, "На связи 🤖 Все системы работают штатно!"):
                                    replied_check_messages.add(last_id)
                                    print(f"[✓] Ответ 'На связи 🤖' успешно отправлен!", flush=True)
        except Exception:
            pass

        # 2. Мониторинг новых оплаченных заказов
        try:
            res = session.get("https://funpay.com/orders/trade", headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            order_items = soup.find_all("a", class_=re.compile(r"tc-item"))

            for item in order_items:
                href = item.get("href", "")
                m = re.search(r"/orders/([A-Z0-9]+)/", href)
                if not m:
                    continue
                order_id = m.group(1)

                if order_id in processed_orders:
                    continue

                status_div = item.find("div", class_=re.compile(r"tc-status"))
                status_text = status_div.get_text(strip=True).lower() if status_div else ""

                if "оплачен" in status_text:
                    desc_div = item.find("div", class_=re.compile(r"tc-desc"))
                    order_desc = desc_div.get_text(strip=True) if desc_div else ""

                    print(f"\n[!] ОПЛАЧЕН НОВЫЙ ЗАКАЗ #{order_id}: {order_desc}", flush=True)

                    if "чувствительность" in order_desc.lower():
                        print(f"[-] #{order_id}: PUBG Mobile сенса (молния ⚡). Пропуск.", flush=True)
                        processed_orders.add(order_id)
                        continue

                    order_url = f"https://funpay.com/orders/{order_id}/"
                    order_check = session.get(order_url, headers=headers, timeout=10).text.lower()
                    if any(x in order_check for x in ["товар передан покупателю", "выданный товар", "order-secrets"]):
                        print(f"[⚡] #{order_id}: уже выдан встроенной молнией FunPay. Пропуск.", flush=True)
                        processed_orders.add(order_id)
                        continue

                    delivery_text = get_delivery_message(order_desc)
                    if not delivery_text:
                        print(f"[-] #{order_id}: не найден шаблон под товар.", flush=True)
                        processed_orders.add(order_id)
                        continue

                    if send_chat_runner_message(session, order_url, delivery_text):
                        processed_orders.add(order_id)
                        print(f"[✓] УСПЕШНО ВЫДАН ТОВАР В ЗАКАЗ #{order_id}!", flush=True)
                    else:
                        print(f"[x] Ошибка доставки сообщения в #{order_id}", flush=True)

                elif any(s in status_text for s in ["закрыт", "отменен", "возврат"]):
                    processed_orders.add(order_id)

        except Exception as loop_err:
            print(f"[x] Ошибка цикла: {loop_err}", flush=True)

        time.sleep(5)

# -------------------------------------------------------------
# АВТОПОДНЯТИЕ ЛОТОВ (КАЖДЫЕ 30 МИНУТ)
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
            print("[↑] Проверка категорий профиля для поднятия...", flush=True)
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

                    msg = res_json.get("msg", "Обработано")
                    print(f"[↑] {cat_type} #{node}: {msg}", flush=True)

                except Exception as node_err:
                    print(f"[x] Ошибка категории #{node}: {node_err}", flush=True)

                time.sleep(3)

        except Exception as e:
            print(f"[x] Ошибка поднятия: {e}", flush=True)

        time.sleep(1800)

if __name__ == '__main__':
    threading.Thread(target=start_bot_loop, daemon=True).start()
    threading.Thread(target=start_auto_raise, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
