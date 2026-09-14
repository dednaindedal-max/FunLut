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
processed_msg_ids = set()

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

def get_csrf(session):
    try:
        r = session.get("https://funpay.com/", headers={"User-Agent": USER_AGENT}, timeout=10)
        m = re.search(r'csrf-token&quot;:&quot;([^&]+)&quot;', r.text) or re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
        return m.group(1) if m else None
    except Exception:
        return None

def send_chat_reply(session, csrf_token, node_id, tag, last_msg_id, text):
    try:
        payload = {
            "objects": json.dumps([{
                "type": "chat_node",
                "id": int(node_id),
                "tag": tag,
                "data": {"node": int(node_id), "last_message": int(last_msg_id), "content": ""}
            }]),
            "request": json.dumps({
                "action": "chat_message",
                "data": {"node": int(node_id), "last_message": int(last_msg_id), "content": text}
            }),
            "csrf_token": csrf_token
        }
        res = session.post("https://funpay.com/runner/", data=payload, headers={
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://funpay.com/chat/"
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[x] Ошибка отправки в чат {node_id}: {e}", flush=True)
        return False

# -------------------------------------------------------------
# ЦИКЛ АВТОВЫДАЧИ И ЛОВЛИ %1
# -------------------------------------------------------------
def start_bot_loop():
    time.sleep(3)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}

    csrf_token = get_csrf(session)

    # Инициализация выполненных заказов
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
        print(f"[✓] Архив заказов загружен ({len(processed_orders)} шт.). Бот на связи!", flush=True)
    except Exception as e:
        print(f"[x] Синхронизация заказов: {e}", flush=True)

    bookmarks_tag = ""

    while True:
        if not csrf_token:
            csrf_token = get_csrf(session)

        # 1. СЛУШАЕМ ВХОДЯЩИЕ СООБЩЕНИЯ ЧЕРЕЗ RUNNER (CHAT BOOKMARKS)
        try:
            bm_payload = {
                "objects": json.dumps([{
                    "type": "chat_bookmarks",
                    "id": USER_ID,
                    "tag": bookmarks_tag,
                    "data": False
                }]),
                "request": False,
                "csrf_token": csrf_token
            }
            r_bm = session.post("https://funpay.com/runner/", data=bm_payload, headers={
                "User-Agent": USER_AGENT,
                "X-Requested-With": "XMLHttpRequest"
            }, timeout=8)

            if r_bm.status_code == 200:
                data = r_bm.json()
                for obj in data.get("objects", []):
                    if obj.get("type") == "chat_bookmarks":
                        bookmarks_tag = obj.get("tag", bookmarks_tag)
                        bm_data = obj.get("data", {})
                        if isinstance(bm_data, dict) and "html" in bm_data:
                            soup_bm = BeautifulSoup(bm_data["html"], "html.parser")
                            for item in soup_bm.find_all("a", class_=re.compile(r"chat-item")):
                                text_el = item.find(class_=re.compile(r"chat-item-text"))
                                p_text = text_el.get_text(strip=True) if text_el else ""

                                if "%1" in p_text:
                                    node_id = item.get("data-id")
                                    if not node_id:
                                        m_n = re.search(r"node=(\d+)", item.get("href", ""))
                                        node_id = m_n.group(1) if m_n else None

                                    if node_id:
                                        # Открываем чат того, кто написал %1
                                        c_url = f"https://funpay.com/chat/?node={node_id}"
                                        cp = session.get(c_url, headers=headers, timeout=8).text
                                        soup_c = BeautifulSoup(cp, "html.parser")
                                        
                                        tag_m = re.search(r'data-tag="([^"]+)"', cp)
                                        chat_tag = tag_m.group(1) if tag_m else ""
                                        
                                        msg_items = soup_c.find_all("div", class_=re.compile(r"chat-msg-item"))
                                        if msg_items:
                                            last_el = msg_items[-1]
                                            mid = last_el.get("id", "")
                                            msg_text_el = last_el.find(class_=re.compile(r"chat-msg-text"))
                                            
                                            if msg_text_el and "%1" in msg_text_el.get_text() and mid not in processed_msg_ids:
                                                # Не отвечаем на свое же сообщение
                                                author_el = last_el.find(class_=re.compile(r"media-user-name"))
                                                author_str = author_el.get_text(strip=True) if author_el else ""
                                                
                                                if "Dednain" not in author_str:
                                                    last_num = int(mid.replace("message-", "")) if "message-" in mid else 0
                                                    print(f"[!] Пользователь написал %1 в чате {node_id}! Отправляем ответ...", flush=True)
                                                    if send_chat_reply(session, csrf_token, node_id, chat_tag, last_num, "На связи 🤖 Все системы работают штатно!"):
                                                        processed_msg_ids.add(mid)
                                                        print(f"[✓] Ответ доставлен автору %1!", flush=True)
        except Exception:
            pass

        # 2. МОНИТОРИНГ ОПЛАТ И ВЫДАЧА ТОВАРОВ
        try:
            r_o = session.get("https://funpay.com/orders/trade", headers=headers, timeout=8)
            s_o = BeautifulSoup(r_o.text, "html.parser")
            for item in s_o.find_all("a", class_=re.compile(r"tc-item")):
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
                    print(f"\n[!] ОПЛАЧЕН НОВЫЙ ЗАКАЗ #{order_id}: {order_desc}", flush=True)

                    if "чувствительность" in order_desc.lower():
                        processed_orders.add(order_id)
                        continue

                    order_url = f"https://funpay.com/orders/{order_id}/"
                    op = session.get(order_url, headers=headers, timeout=8).text
                    if any(x in op.lower() for x in ["товар передан покупателю", "выданный товар", "order-secrets"]):
                        processed_orders.add(order_id)
                        continue

                    deliv_text = get_delivery_message(order_desc)
                    if deliv_text:
                        chat_m = re.search(r'data-id="(\d+)"', op)
                        tag_m = re.search(r'data-tag="([^"]+)"', op)
                        msg_m = re.findall(r'id="message-(\d+)"', op)
                        
                        if chat_m:
                            cid = int(chat_m.group(1))
                            ctag = tag_m.group(1) if tag_m else ""
                            l_mid = int(msg_m[-1]) if msg_m else 0
                            if send_chat_reply(session, csrf_token, cid, ctag, l_mid, deliv_text):
                                processed_orders.add(order_id)
                                print(f"[✓] Товар успешно отправлен в заказ #{order_id}!", flush=True)

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
    headers = {"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest"}

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
