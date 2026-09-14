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
replied_msg_ids = set()

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

def send_chat_message(session, node_id, message_text: str):
    try:
        url = f"https://funpay.com/chat/?node={node_id}"
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        html = resp.text

        csrf_m = re.search(r'csrf-token&quot;:&quot;([^&]+)&quot;', html) or re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        if not csrf_m:
            return False
        csrf = csrf_m.group(1)

        tag_m = re.search(r'data-tag="([^"]+)"', html)
        tag = tag_m.group(1) if tag_m else ""

        msg_ids = re.findall(r'id="message-(\d+)"', html)
        last_id = int(msg_ids[-1]) if msg_ids else 0

        payload = {
            "objects": json.dumps([{
                "type": "chat_node",
                "id": int(node_id),
                "tag": tag,
                "data": {"node": int(node_id), "last_message": last_id, "content": ""}
            }]),
            "request": json.dumps({
                "action": "chat_message",
                "data": {"node": int(node_id), "last_message": last_id, "content": message_text}
            }),
            "csrf_token": csrf
        }
        res = session.post("https://funpay.com/runner/", data=payload, headers={
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": url
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[x] Ошибка send_chat_message ({node_id}): {e}", flush=True)
        return False

# -------------------------------------------------------------
# ЦИКЛ ОБРАБОТКИ СООБЩЕНИЙ И ЗАКАЗОВ
# -------------------------------------------------------------
def start_bot_loop():
    time.sleep(3)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    # Синхронизация истории заказов
    try:
        r = session.get("https://funpay.com/orders/trade", headers=headers, timeout=12)
        s = BeautifulSoup(r.text, "html.parser")
        for it in s.find_all("a", class_=re.compile(r"tc-item")):
            st = it.find("div", class_=re.compile(r"tc-status"))
            txt = st.get_text(strip=True).lower() if st else ""
            if any(x in txt for x in ["закрыт", "отменен", "возврат"]):
                m = re.search(r"/orders/([A-Z0-9]+)/", it.get("href", ""))
                if m:
                    processed_orders.add(m.group(1))
        print(f"[✓] Заказов в архиве: {len(processed_orders)}. Запуск листенера...", flush=True)
    except Exception as e:
        print(f"[x] Старт: {e}", flush=True)

    while True:
        # 1. ЧТЕНИЕ ВХОДЯЩИХ ЧАТОВ
        try:
            r_chats = session.get("https://funpay.com/chat/", headers=headers, timeout=8)
            s_chats = BeautifulSoup(r_chats.text, "html.parser")
            
            # Проверяем первые 5 активных диалогов
            for item in s_chats.find_all("a", class_=re.compile(r"chat-item"))[:5]:
                href = item.get("href", "")
                m_node = re.search(r"node=([a-zA-Z0-9_-]+)", href) or re.search(r"node=(\d+)", href)
                node_id = item.get("data-id") or (m_node.group(1) if m_node else None)
                if not node_id:
                    continue

                preview = item.find(class_=re.compile(r"chat-item-text"))
                preview_text = preview.get_text(strip=True) if preview else ""

                if "%1" in preview_text:
                    # Заходим в диалог
                    diag_url = f"https://funpay.com/chat/?node={node_id}"
                    diag_page = session.get(diag_url, headers=headers, timeout=8).text
                    diag_soup = BeautifulSoup(diag_page, "html.parser")
                    
                    messages = diag_soup.find_all("div", class_=re.compile(r"chat-msg-item"))
                    if messages:
                        last_m = messages[-1]
                        mid = last_m.get("id", "")
                        body = last_m.find(class_=re.compile(r"chat-msg-text"))
                        author = last_m.find(class_=re.compile(r"chat-msg-author"))
                        author_name = author.get_text(strip=True) if author else ""

                        if body and "%1" in body.get_text() and mid not in replied_msg_ids:
                            # Пропускаем, если последнее сообщение написал сам бот
                            if "Dednain" not in author_name:
                                print(f"[!] Получена команда %1 от {author_name} (чат {node_id})", flush=True)
                                if send_chat_message(session, node_id, "На связи 🤖 Все системы работают штатно!"):
                                    replied_msg_ids.add(mid)
                                    print(f"[✓] Ответ отправлен в чат {node_id}!", flush=True)
        except Exception as e:
            pass

        # 2. МОНИТОРИНГ ОПЛАТ
        try:
            r_ord = session.get("https://funpay.com/orders/trade", headers=headers, timeout=8)
            s_ord = BeautifulSoup(r_ord.text, "html.parser")
            for item in s_ord.find_all("a", class_=re.compile(r"tc-item")):
                href = item.get("href", "")
                m = re.search(r"/orders/([A-Z0-9]+)/", href)
                if not m:
                    continue
                order_id = m.group(1)
                if order_id in processed_orders:
                    continue

                st_div = item.find("div", class_=re.compile(r"tc-status"))
                st_txt = st_div.get_text(strip=True).lower() if st_div else ""

                if "оплачен" in st_txt:
                    desc_div = item.find("div", class_=re.compile(r"tc-desc"))
                    order_desc = desc_div.get_text(strip=True) if desc_div else ""
                    print(f"\n[!] ОПЛАЧЕН ЗАКАЗ #{order_id}: {order_desc}", flush=True)

                    if "чувствительность" in order_desc.lower():
                        processed_orders.add(order_id)
                        continue

                    order_url = f"https://funpay.com/orders/{order_id}/"
                    op = session.get(order_url, headers=headers, timeout=8).text
                    if any(x in op.lower() for x in ["товар передан покупателю", "выданный товар", "order-secrets"]):
                        print(f"[⚡] #{order_id}: выдан встроенной системой.", flush=True)
                        processed_orders.add(order_id)
                        continue

                    delivery_text = get_delivery_message(order_desc)
                    if not delivery_text:
                        processed_orders.add(order_id)
                        continue

                    chat_m = re.search(r'data-id="(\d+)"', op)
                    if chat_m:
                        c_id = chat_m.group(1)
                        if send_chat_message(session, c_id, delivery_text):
                            processed_orders.add(order_id)
                            print(f"[✓] ВЫДАН ТОВАР В ЗАКАЗ #{order_id}!", flush=True)

                elif any(s in st_txt for s in ["закрыт", "отменен", "возврат"]):
                    processed_orders.add(order_id)
        except Exception:
            pass

        time.sleep(3)

# -------------------------------------------------------------
# АВТОПОДНЯТИЕ (РАЗ В 30 МИНУТ)
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
            prof_res = session.get(f"https://funpay.com/users/{USER_ID}/", headers={"User-Agent": USER_AGENT})
            categories = set(re.findall(r"/(lots|chips)/(\d+)/", prof_res.text))
            raised_games = set()

            for cat_type, node in categories:
                try:
                    cat_page = session.get(f"https://funpay.com/{cat_type}/{node}/", headers={"User-Agent": USER_AGENT}).text
                    game_m = re.search(r'data-game="(\d+)"', cat_page)
                    payload = {"node_id": node}
                    if game_m:
                        gid = game_m.group(1)
                        if gid in raised_games:
                            continue
                        payload["game_id"] = gid

                    r1 = session.post(f"https://funpay.com/{cat_type}/raise", data=payload, headers=headers)
                    res_j = r1.json()

                    if "modal" in res_j:
                        sp = BeautifulSoup(res_j["modal"], "html.parser")
                        box = sp.find("div", class_="raise-box")
                        if box:
                            g_id = box.get("data-game", payload.get("game_id"))
                            mnode = box.get("data-node", node)
                            cbs = [inp.get("value") for inp in sp.find_all("input", type="checkbox") if inp.get("value")]
                            post_data = {
                                "game_id": g_id,
                                "node_id": mnode,
                                "node_ids[]": cbs if cbs else [node]
                            }
                            r2 = session.post(f"https://funpay.com/{cat_type}/raise", data=post_data, headers=headers)
                            res_j = r2.json()
                            if g_id:
                                raised_games.add(g_id)

                    print(f"[↑] {cat_type} #{node}: {res_j.get('msg', 'OK')}", flush=True)
                except Exception:
                    pass
                time.sleep(2)
        except Exception:
            pass
        time.sleep(1800)

if __name__ == '__main__':
    threading.Thread(target=start_bot_loop, daemon=True).start()
    threading.Thread(target=start_auto_raise, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
