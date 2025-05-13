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

def fetch_category_prices(category_id):
    auth = HTTPBasicAuth(WC_API_KEY, WC_API_SECRET)
    page = 1
    all_filtered = []

    try:
        while True:
            url = f"{WC_API_URL}/products"
            params = {
                "category": category_id,
                "status": "publish",
                "per_page": 100,
                "page": page
            }

            response = requests.get(url, params=params, auth=auth)
            if response.status_code != 200:
                print(f"[ERROR] WooCommerce API: {response.status_code} - {response.text}", flush=True)
                return "Failed to retrieve products."

            products = response.json()
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
                break
            page += 1

        if not all_filtered:
            return "No products currently in stock with valid prices."

        message = "Product Prices:\n\n" + "\n".join(all_filtered)
        return message

    except Exception as e:
        print(f"[ERROR] Exception fetching category {category_id}: {e}", flush=True)
        return "Error fetching product data."
        
def check_user_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    params = {}
    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        response = requests.get(url, params=params).json()
        results = response.get("result", [])

        for update in results:
            update_id = update.get("update_id")
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            commands = {
                "/allminerprices": 20,        # You can use this as default All Miners category
                "/btcminerprices": 16,
                "/dogeminerprices": 21,
                "/altminerprices": 22,
                "/aleominerprices": 337,
                "/alphminerprices": 128,
                "/etcminerprices": 189,
                "/kdaminerprices": 192,
                "/kasminerprices": 102,
                "/usastockprices": 199,
                "/pduprices": 105,
                "/xfmrprices": 106,
                "/partsprices": 23
            }
            
            cmd = text.strip().lower()
            if cmd == "/start":
                welcome = (
                    "<b>Welcome to the Refined Capital Mining Bot 🧠⛏️</b>\n\n"
                    "Use this bot to check real-time availability and pricing for mining hardware and power equipment.\n\n"
                    "<b>Commands:</b>\n"
                    "🟩 <b>Miners by Category:</b>\n"
                    "/allminerprices – All Miners\n"
                    "/btcminerprices – BTC Miners\n"
                    "/dogeminerprices – LTC & DOGE Miners\n"
                    "/altminerprices – ALT Miners\n"
                    "/aleominerprices – ALEO Miners\n"
                    "/alphminerprices – ALPH Miners\n"
                    "/etcminerprices – ETC Miners\n"
                    "/kdaminerprices – KDA Miners\n"
                    "/kasminerprices – KAS Miners\n\n"
                    " \n\n"
                    "🟦 <b>Other Hardware:</b>\n"
                    "/usastockprices – USA Stock Only\n"
                    "/pduprices – PDUs\n"
                    "/xfmrprices – Transformers\n"
                    "/partsprices – Parts & Accessories\n\n"
                    "Type any of the above commands to get the latest pricing and stock for that category.\n\n"
                    "<i>Powered by Refined Capital</i>\n"
                )
                send_reply(chat_id, welcome)
            if cmd == "/help":
                help = (
                    ""<b>Commands:</b>\n"
                    "🟩 <b>Miners by Category:</b>\n"
                    "/allminerprices – All Miners\n"
                    "/btcminerprices – BTC Miners\n"
                    "/dogeminerprices – LTC & DOGE Miners\n"
                    "/altminerprices – ALT Miners\n"
                    "/aleominerprices – ALEO Miners\n"
                    "/alphminerprices – ALPH Miners\n"
                    "/etcminerprices – ETC Miners\n"
                    "/kdaminerprices – KDA Miners\n"
                    "/kasminerprices – KAS Miners\n\n"
                    " \n\n"
                    "🟦 <b>Other Hardware:</b>\n"
                    "/usastockprices – USA Stock Only\n"
                    "/pduprices – PDUs\n"
                    "/xfmrprices – Transformers\n"
                    "/partsprices – Parts & Accessories\n\n"
                )
                send_reply(chat_id, help)
            if cmd in commands:
                print(f"[DEBUG] Received {cmd} from chat {chat_id}", flush=True)
                reply = fetch_category_prices(commands[cmd])
                send_reply(chat_id, reply)
                
            # Move the update ID forward regardless of command
            last_update_id = update_id

    except Exception as e:
        print(f"[ERROR] Exception checking messages: {e}", flush=True)

def flush_old_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    response = requests.get(url).json()
    results = response.get("result", [])
    if results:
        last_update_id = results[-1]["update_id"]
        print(f"[INFO] Flushed old messages up to update_id: {last_update_id}", flush=True)

flush_old_messages()

while True:
    check_user_messages()
    time.sleep(2)

# Start the bot loop
while True:
    try:
        check_user_messages()
    except Exception as e:
        print(f"[ERROR] Bot loop crashed: {e}", flush=True)
    time.sleep(2)  # Poll more frequently for better responsiveness
