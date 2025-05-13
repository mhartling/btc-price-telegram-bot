import os
import time
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta

# Telegram Bot Setup
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# WooCommerce API Setup
WC_API_URL = os.environ.get("WC_API_URL")
WC_API_KEY = os.environ.get("WC_API_KEY")
WC_API_SECRET = os.environ.get("WC_API_SECRET")

# In-memory store for tracking user names
user_names = {}

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

def fetch_square_invoices(full_name):
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SQUARE_API_KEY')}",
            "Content-Type": "application/json"
        }

        search_url = "https://connect.squareup.com/v2/customers/search"
        query = {
            "query": {
                "filter": {
                    "text_filter": {
                        "exact": full_name
                    }
                }
            }
        }

        response = requests.post(search_url, headers=headers, json=query)
        if response.status_code != 200:
            return "Failed to search for customer in Square."

        customers = response.json().get("customers", [])
        if not customers:
            return f"No customer found for name: {full_name}"

        customer_id = customers[0]["id"]

        location_id = os.environ.get("SQUARE_LOCATION_ID")
        invoices_url = f"https://connect.squareup.com/v2/invoices?location_id={location_id}"
        response = requests.get(invoices_url, headers=headers)
        if response.status_code != 200:
            return "Failed to retrieve invoices."

        invoices = response.json().get("invoices", [])
        now = datetime.utcnow()
        six_months_ago = now - timedelta(days=180)

        unpaid = None
        paid_list = []

        for invoice in invoices:
            if invoice.get("customer_id") != customer_id:
                continue

            status = invoice.get("status")
            updated_at = datetime.strptime(invoice.get("updated_at")[:19], "%Y-%m-%dT%H:%M:%S")

            if status == "UNPAID" and not unpaid:
                unpaid = invoice
            elif status == "PAID" and updated_at > six_months_ago:
                paid_list.append(invoice)

        result = ""

        if unpaid:
            result += f"🔴 <b>Current Unpaid Invoice</b>\nInvoice #{unpaid['invoice_number']} - Amount Due: ${unpaid['amount_money']['amount'] / 100:.2f}\n"
            result += f"View Invoice: {unpaid['public_url']}\n\n"

        if paid_list:
            result += f"✅ <b>Paid Invoices (Last 6 Months)</b>\n"
            for inv in paid_list:
                amount = inv['amount_money']['amount'] / 100
                result += f"• Invoice #{inv['invoice_number']} - ${amount:.2f}\n"

        if not result:
            return "No recent invoices found."

        return result.strip()

    except Exception as e:
        print(f"[ERROR] Square API: {e}", flush=True)
        return "An error occurred while retrieving your invoices."

def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["\U0001F50D See Prices"],
            ["👥 Hosting Clients"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    message = (
        "<b>Welcome to the Refined Capital Mining Bot \U0001F9E0\u26CF\ufe0f</b>\n\n"
        "Use this bot to check real-time pricing and manage your mining account.\n\n"
        "Choose an option below to get started:\n"
    )
    send_reply(chat_id, message, keyboard)

def send_prices_menu(chat_id):
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
    send_reply(chat_id, "\u2B07 Choose a category below:", keyboard)

def send_hosting_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🧾 My Hosting Invoices"],
            ["🖥️ My Miners"],
            ["📦 My Orders"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_reply(chat_id, "Great. Now please choose one of the options below:", keyboard)

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

                if cmd == "/start":
                    send_main_menu(chat_id)

                elif cmd == "🔍 see prices":
                    send_prices_menu(chat_id)

                elif cmd == "👥 hosting clients":
                    user_names[chat_id] = None
                    send_reply(chat_id, "Please enter your first and last name to continue:")

                elif chat_id in user_names and user_names[chat_id] is None:
                    user_names[chat_id] = text.strip()
                    send_reply(chat_id, f"Thanks, {user_names[chat_id]}!")
                    send_hosting_menu(chat_id)

                elif cmd == "🧾 my hosting invoices":
                    name = user_names.get(chat_id)
                    if not name:
                        send_reply(chat_id, "We couldn't find your name. Please start again with /start.")
                    else:
                        reply = fetch_square_invoices(name)
                        send_reply(chat_id, reply)

                elif cmd == "🖥️ my miners":
                    send_reply(chat_id, "(MaintainX API) Looking up miners for: " + user_names.get(chat_id, "Unknown"))

                elif cmd == "📦 my orders":
                    send_reply(chat_id, "(WooCommerce API) Fetching orders for: " + user_names.get(chat_id, "Unknown"))

                elif cmd == "🛍 shop now":
                    send_reply(chat_id, "\U0001F6D2 Visit our full store: https://refined-capital.com/shop")

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
