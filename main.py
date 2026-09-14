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
    return "FunPay Smart Bot 24/7 (Delivery + Auto-Raise + Runner HealthCheck) is online!"

# -------------------------------------------------------------
# КОНФИГУРАЦИЯ
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
answered_messages = set()

# -------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -------------------------------------------------------------
def get_csrf(html_text: str):
    m = re.search(r'csrf-token&quot;:&quot;([^&]+)&quot;', html_text) or re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    return m.group(1) if m else None

def get_delivery_message(page_text: str):
    text_upper = page_text.upper()
    opt_keywords = [TRIGGER_OPTIMIZATION, "OPTIMIZATION", "FPS", "ФПС", "ПРЕМИУМ", "PREMIUM"]
    if any(k in text_upper for k in opt_keywords):
        return TEXT_OPTIMIZATION

    if TRIGGER_GEMINI in text_upper:
        return TEXT_GEMINI

    if TRIGGER_SIGMA in text_upper or "SIGMA" in text_upper:
        return TEXT_SIGMA
    elif TRIGGER_ZIKO in text_upper or "RTXZIKO" in text_upper or "ЗИКО" in text_upper:
        return TEXT_ZIKO
    elif TRIGGER_HYZEN in text_upper or "HYZEN" in text_upper or "ХАЙЗЕН" in text_upper:
        return TEXT_HYZEN
        
    return None

def send_chat_runner(session, page_url: str, message_text: str):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        resp = session.get(page_url, headers=headers, timeout=12)
        html = resp.text
        
        csrf_token = get_csrf(html)
        if not csrf_token:
            print(f"[x] Ошибка: CSRF токен не найден на {page_url}", flush=True)
            return False

        soup = BeautifulSoup(html, "html.parser")
        chat_div = soup.find("div", attrs={"data-id": True, "data-tag": True})
        if chat_div:
            node_id = int(chat_div["data-id"])
            tag = chat_div.get("data-tag", "")
        else:
            m_id = re.search(r'data-id="(\d+)"', html)
            m_tag = re.search(r'data-tag="([^"]+)"', html)
            if not m_id:
                print(f"[x] Ошибка: Чат не найден на {page_url}", flush=True)
                return False
            node_id = int(m_id.group(1))
            tag = m_tag.group(1) if m_tag else ""

        msg_ids = re.findall(r'id="message-(\d+)"', html)
        last_msg_id = int(msg_ids[-1]) if msg_ids else 0

        payload = {
            "objects": json.dumps([{
                "type": "chat_node",
                "id": node_id,
                "tag": tag,
                "data": {"node": node_id, "last_message": last_msg_id, "content": ""}
            }]),
            "request": json.dumps({
                "action": "chat_message",
                "data": {"node": node_id, "last_message": last_msg_id, "content": message_text}
            }),
            "csrf_token": csrf_token
        }
        
        post_resp = session.post("https://funpay.com/runner/", data=payload, headers={
            "User-Agent": USER_AGENT,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": page_url
        }, timeout=10)
        
        return post_resp.status_code == 200
    except Exception as e:
        print(f"[x] Ошибка отправки runner ({page_url}): {e}", flush=True)
        return False

# -------------------------------------------------------------
# ПОТОК МОНИТОРИНГА И ВЫДАЧИ
# -------------------------------------------------------------
def start_bot_loop():
    time.sleep(3)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"}

    # Загружаем уже закрытые заказы при старте
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
        print(f"[✓] Инициализация: {len(processed_orders)} завершенных заказов пропущено.", flush=True)
    except Exception as e:
        print(f"[x] Ошибка синхронизации истории: {e}", flush=True)

    bookmarks_tag = ""

    while True:
        # 1. Проверка команды %1 через chat_bookmarks
        try:
            bm_payload = {
                "objects": json.dumps([{
                    "type": "chat_bookmarks",
                    "id": USER_ID,
                    "tag": bookmarks_tag,
                    "data": False
                }]),
                "request": False,
                "csrf_token": ""
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
                                        c_url = f"https://funpay.com/chat/?node={node_id}"
                                        cp = session.get(c_url, headers=headers, timeout=8).text
                                        soup_c = BeautifulSoup(cp, "html.parser")
                                        
                                        msg_items = soup_c.find_all("div", class_=re.compile(r"chat-msg-item"))
                                        if msg_items:
                                            last_el = msg_items[-1]
                                            mid = last_el.get("id", "")
                                            msg_text_el = last_el.find(class_=re.compile(r"chat-msg-text"))
                                            
                                            if msg_text_el and "%1" in msg_text_el.get_text() and mid not in answered_messages:
                                                author_el = last_el.find(class_=re.compile(r"media-user-name"))
                                                author_str = author_el.get_text(strip=True) if author_el else ""
                                                
                                                if "Dednain" not in author_str:
                                                    print(f"[!] Сработал %1 от {author_str} (чат {node_id})!", flush=True)
                                                    if send_chat_runner(session, c_url, "На связи 🤖 Все системы работают штатно!"):
                                                        answered_messages.add(mid)
                                                        print(f"[✓] Ответ на %1 доставлен!", flush=True)
        except Exception:
            pass

        # 2. Мониторинг заказов и выдача
        try:
            r_o = session.get("https://funpay.com/orders/trade", headers=headers, timeout=8)
            s_o = BeautifulSoup(r_o.text, "html.parser")
            order_items = s_o.find_all("a", class_=re.compile(r"tc-item"))

            for item in order_items:
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
                    order_url = f"https://funpay.com/orders/{order_id}/"
                    op = session.get(order_url, headers=headers, timeout=8).text
                    
                    if any(x in op.lower() for x in ["товар передан покупателю", "выданный товар", "order-secrets"]):
                        print(f"[⚡] #{order_id}: товар уже выдан FunPay. Пропуск.", flush=True)
                        processed_orders.add(order_id)
                        continue

                    deliv_text = get_delivery_message(op)
                    if not deliv_text:
                        continue

                    print(f"\n[!] ОПЛАЧЕН НОВЫЙ ЗАКАЗ #{order_id}. Отправка товара...", flush=True)
                    if send_chat_runner(session, order_url, deliv_text):
                        processed_orders.add(order_id)
                        print(f"[✓] УСПЕШНО ВЫДАН ТОВАР В ЗАКАЗ #{order_id}!", flush=True)
                    else:
                        print(f"[x] Ошибка доставки #{order_id}", flush=True)

                elif any(s in st_txt for s in ["закрыт", "отменен", "возврат"]):
                    processed_orders.add(order_id)
        except Exception:
            pass

        time.sleep(4)

# -------------------------------------------------------------
# ПОТОК АВТОПОДНЯТИЯ ЛОТОВ (КАЖДЫЕ 30 МИНУТ)
# -------------------------------------------------------------
def start_auto_raise():
    time.sleep(10)
    session = requests.Session()
    session.cookies.set("golden_key", GOLDEN_KEY)
    headers = {
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    while True:
        try:
            print("\n[↑] Запуск цикла поднятия лотов...", flush=True)
            prof_res = session.get(f"https://funpay.com/users/{USER_ID}/", headers={"User-Agent": USER_AGENT}, timeout=12)
            csrf_token = get_csrf(prof_res.text)
            
            if not csrf_token:
                print("[x] Не удалось получить CSRF-токен для поднятия лотов!", flush=True)
            else:
                categories = set(re.findall(r"/(lots|chips)/(\d+)/", prof_res.text))
                print(f"[↑] Найдено категорий в профиле: {len(categories)}", flush=True)
                raised_games = set()

                for cat_type, node in categories:
                    try:
                        cat_page = session.get(f"https://funpay.com/{cat_type}/{node}/", headers={"User-Agent": USER_AGENT}, timeout=10).text
                        game_m = re.search(r'data-game="(\d+)"', cat_page)
                        
                        payload = {
                            "node_id": node,
                            "csrf_token": csrf_token
                        }
                        
                        if game_m:
                            gid = game_m.group(1)
                            if gid in raised_games:
                                continue
                            payload["game_id"] = gid

                        r1 = session.post(f"https://funpay.com/{cat_type}/raise", data=payload, headers=headers, timeout=10)
                        res_j = r1.json()

                        if "modal" in res_j:
                            soup = BeautifulSoup(res_j["modal"], "html.parser")
                            raise_box = soup.find("div", class_="raise-box")
                            if raise_box:
                                g_id = raise_box.get("data-game", payload.get("game_id"))
                                mnode = raise_box.get("data-node", node)
                                cbs = [inp.get("value") for inp in soup.find_all("input", type="checkbox") if inp.get("value")]

                                post_data = {
                                    "game_id": g_id,
                                    "node_id": mnode,
                                    "node_ids[]": cbs if cbs else [node],
                                    "csrf_token": csrf_token
                                }
                                r2 = session.post(f"https://funpay.com/{cat_type}/raise", data=post_data, headers=headers, timeout=10)
                                res_j = r2.json()
                                if g_id:
                                    raised_games.add(g_id)

                        msg = res_j.get("msg", "OK")
                        print(f"[↑] Раздел {cat_type} #{node}: {msg}", flush=True)
                    except Exception as cat_e:
                        print(f"[x] Ошибка поднятия #{node}: {cat_e}", flush=True)

                    time.sleep(2)

        except Exception as e:
            print(f"[x] Ошибка в потоке автоподнятия: {e}", flush=True)

        time.sleep(1800)

# -------------------------------------------------------------
# ТОЧКА ВХОДА
# -------------------------------------------------------------
if __name__ == '__main__':
    threading.Thread(target=start_bot_loop, daemon=True).start()
    threading.Thread(target=start_auto_raise, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
