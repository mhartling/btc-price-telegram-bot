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

# Used to avoid processing the same message multiple times
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
    auth = HTTPBasicAuth(WC_API_KEY, WC_API_SECRET)
    page = 1
    all_filtered = []

    try:
        while True:
            url = f"{WC_API_URL}/products"
            params = {
                "category": WC_CATEGORY_ID,
                "status": "publish",
                "per_page": 100,
                "page": page
            }

            response = requests.get(url, params=params, auth=auth)
            if response.status_code != 200:
                print(f"[ERROR] WooCommerce API: {response.status_code} - {response.text}", flush=True)
                return "Failed to retrieve products."

            products = response.json()
            print(f"[DEBUG] Fetched page {page} with {len(products)} products", flush=True)

            for p in products:
                price = float(p.get("price") or 0)
                stock_status = p.get("stock_status")
                stock_quantity = p.get("stock_quantity", "N/A")
                link = p.get("permalink")
                name = p.get("name")

                if price > 0 and stock_status == "instock":
                    line = f"<a href=\"{link}\">{name}</a> - ${price} (Stock: {stock_quantity})"
                    all_filtered.append(line)

            if len(products) < 100:
                break  # Reached the last page

            page += 1  # Go to next page

        if not all_filtered:
            return "No miners currently in stock with valid prices."

        message = "Current Miner Prices:\n\n" + "\n".join(all_filtered)
        return message

    except Exception as e:
        print(f"[ERROR] Exception fetching products: {e}", flush=True)
        return "Error fetching product data."
def check_user_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    params = {}
    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        response = requests.get(url, params=params).json()
        for update in response.get("result", []):
            update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            if text.strip().lower() == "/prices":
                print("[DEBUG] Received /prices command", flush=True)
                reply = fetch_eligible_products()
                send_reply(chat_id, reply)

            # After processing, move to the next update
            last_update_id = update_id

    except Exception as e:
        print(f"[ERROR] Exception checking messages: {e}", flush=True)

# Start the bot loop
while True:
    try:
        check_user_messages()
    except Exception as e:
        print(f"[ERROR] Bot loop crashed: {e}", flush=True)
    time.sleep(2)  # Poll more frequently for better responsiveness
