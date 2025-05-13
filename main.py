import os
import time
import json
import requests
from requests.auth import HTTPBasicAuth

# Telegram Bot Setup
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# WooCommerce API Setup
WC_API_URL = os.environ.get("WC_API_URL")
WC_API_KEY = os.environ.get("WC_API_KEY")
WC_API_SECRET = os.environ.get("WC_API_SECRET")

# Commands mapped to category IDs
commands = {
    "/allminerprices": 20,
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

last_update_id = None

def send_menu_keyboard(chat_id):
    keyboard = {
        "keyboard": [
            ["\U0001FA99 All Miners", "₿ BTC Miners"],
            ["\U0001F680 Doge/LTC Miners", "\U0001F9EA ALT Miners"],
            ["\U0001F510 ALEO", "⚡ ALPH"],
            ["\u26CF️ KAS", "\U0001F4BE ETC"],
            ["\U0001F1FA\U0001F1F8 USA Stock", "\U0001F50C PDUs"],
            ["\U0001F527 Transformers", "\U0001FA99 Parts"],
            ["\U0001F6D2 Shop Now"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    message = (
        "\u2B07 Select a category from the menu below to get real-time prices:\n"
        "(Or use the /start command for inline buttons)"
    )
    send_reply(chat_id, message, keyboard)

def send_reply(chat_id, message, keyboard=None):
    url = f"{BOT_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    response = requests.post(url, data=data)
    if not response.ok:
        print(f"[ERROR] Failed to send message: {response.text}", flush=True)

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
            last_update_id = update.get("update_id")

            if "message" in update:
                message = update["message"]
                text = message.get("text", "")
                chat_id = message["chat"]["id"]
                cmd = text.strip().lower()

                if cmd == "/menu":
                    send_menu_keyboard(chat_id)

                elif cmd == "/start":
                    welcome = (
                        "<b>Welcome to the Refined Capital Mining Bot \U0001F9E0\u26CF\ufe0f</b>\n\n"
                        "Use this bot to check real-time pricing and availability for crypto mining hardware and infrastructure.\n\n"
                        "Choose a category below to get started:\n\n"
                        "<i>Powered by Refined Capital</i>"
                    )

                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "\U0001FA99 All Miners", "callback_data": "/allminerprices"},
                                {"text": "₿ BTC Miners", "callback_data": "/btcminerprices"}
                            ],
                            [
                                {"text": "\U0001F680 Doge/LTC Miners", "callback_data": "/dogeminerprices"},
                                {"text": "\U0001F9EA ALT Miners", "callback_data": "/altminerprices"}
                            ],
                            [
                                {"text": "\U0001F510 ALEO", "callback_data": "/aleominerprices"},
                                {"text": "⚡ ALPH", "callback_data": "/alphminerprices"}
                            ],
                            [
                                {"text": "⛏️ KAS", "callback_data": "/kasminerprices"},
                                {"text": "\U0001F4BE ETC", "callback_data": "/etcminerprices"}
                            ],
                            [
                                {"text": "\U0001F1FA\U0001F1F8 USA Stock", "callback_data": "/usastockprices"},
                                {"text": "\U0001F50C PDUs", "callback_data": "/pduprices"}
                            ],
                            [
                                {"text": "\U0001F527 Transformers", "callback_data": "/xfmrprices"},
                                {"text": "\U0001FA99 Parts", "callback_data": "/partsprices"}
                            ],
                            [
                                {"text": "\U0001F6D2 Shop Now", "url": "https://refined-capital.com/shop"}
                            ]
                        ]
                    }
                    send_reply(chat_id, welcome, keyboard)

                elif cmd in commands:
                    reply = fetch_category_prices(commands[cmd])
                    send_reply(chat_id, reply)

                else:
                    menu_map = {
                        "\U0001FA99 all miners": "/allminerprices",
                        "₿ btc miners": "/btcminerprices",
                        "\U0001F680 doge/ltc miners": "/dogeminerprices",
                        "\U0001F9EA alt miners": "/altminerprices",
                        "\U0001F510 aleo": "/aleominerprices",
                        "⚡ alph": "/alphminerprices",
                        "\U0001F4BE etc": "/etcminerprices",
                        "⛏️ kas": "/kasminerprices",
                        "\U0001F1FA\U0001F1F8 usa stock": "/usastockprices",
                        "\U0001F50C pdus": "/pduprices",
                        "\U0001F527 transformers": "/xfmrprices",
                        "\U0001FA99 parts": "/partsprices"
                    }

                    if cmd in menu_map:
                        mapped_cmd = menu_map[cmd]
                        if mapped_cmd in commands:
                            reply = fetch_category_prices(commands[mapped_cmd])
                            send_reply(chat_id, reply)

                    elif cmd == "\U0001F6D2 shop now":
                        send_reply(chat_id, "\U0001F6D2 Visit our full store: https://refined-capital.com/shop")

            if "callback_query" in update:
                callback = update["callback_query"]
                data = callback.get("data", "")
                chat_id = callback["message"]["chat"]["id"]

                if data in commands:
                    reply = fetch_category_prices(commands[data])
                    send_reply(chat_id, reply)

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
    try:
        check_user_messages()
    except Exception as e:
        print(f"[ERROR] Bot loop crashed: {e}", flush=True)
    time.sleep(2)
