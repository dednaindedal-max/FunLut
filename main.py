import os
import threading
import time
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "FunPay Bot is active!"

def run_bot():
    print("Бот FunPay запускается...")
    while True:
        try:
            time.sleep(15)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(10)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
