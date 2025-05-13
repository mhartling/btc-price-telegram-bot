import os
import time
import requests
from requests.auth import HTTPBasicAuth

# Telegram Bot Setup
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# WooCommerce API Setup
WC_API_URL = os.environ.get("WC_API_URL")
WC_API_KEY = os.environ.get("WC_API_KEY")
WC_API_SECRET = os.environ.get("WC_API_SECRET")
WC_CATEGORY_ID = os.environ.get("WC_CATEGORY_ID")

# Used to avoid processing the same Telegram message multiple times
last_update_id = None

def send_reply(chat_id, message):
    url = f"{BOT_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, data=data)

def fetch_eligible_products():
    url = f"{WC_API_URL}/products"
    auth = HTTPBasicAuth(WC_API_KEY, WC_API_SECRET)
    params = {
        "category": WC_CATEGORY_ID,
        "status": "publish",
        "per_page": 100
    }

    try:
        response = requests.get(url, params=params, auth=auth)
        if response.status_code != 200:
            print(f"[ERROR] WooCommerce API: {response.status_code} - {response.text}", flush=True)
            return "Failed to retrieve products."

        products = response.json()
        filtered = []

        for p in products:
            price = float(p.get("price") or 0)
            stock_status = p.get("stock_status")
            stock_quantity = p.get("stock_quantity", "N/A")
            link = p.get("permalink")
            name = p.get("name")

            if price > 0 and stock_status == "instock":
                line = f"<a href=\"{link}\">{name}</a> - ${price} (Stock: {stock_quantity})"
                filtered.append(line)

        if not filtered:
            return "No miners currently in stock with valid prices."

        message = "Current Miner Prices:\n\n" + "\n".join(filtered)
        return message

    except Exception as e:
        print(f"[ERROR] Exception fetching products: {e}", flush=True)
        return "Error fetching product data."

def check_user_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    params = {"offset": last_update_id + 1 if last_update_id else None}
    try:
        response = requests.get(url, params=params).json()
        for update in response.get("result", []):
            last_update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            if text.strip().lower() == "/prices":
                reply = fetch_eligible_products()
                send_reply(chat_id, reply)

    except Exception as e:
        print(f"[ERROR] Exception checking messages: {e}", flush=True)

# Start the bot loop
while True:
    try:
        check_user_messages()
    except Exception as e:
        print(f"[ERROR] Bot loop crashed: {e}", flush=True)
    time.sleep(10)
