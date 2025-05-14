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

# In-memory store for tracking user names and emails
user_profiles = {}

# Commands mapped to category IDs and labels
commands = {
    "/allminerprices": (31, "All Miners"),
    "/btcminerprices": (16, "BTC Miners"),
    "/dogeminerprices": (21, "DOGE/LTC Miners"),
    "/altminerprices": (22, "ALT Miners"),
    "/aleominerprices": (337, "ALEO Miners"),
    "/alphminerprices": (128, "ALPH Miners"),
    "/etcminerprices": (189, "ETC Miners"),
    "/kdaminerprices": (192, "KDA Miners"),
    "/kasminerprices": (102, "KAS Miners"),
    "/usastockprices": (199, "USA Stock"),
    "/pduprices": (105, "PDUs"),
    "/xfmrprices": (106, "Transformers"),
    "/partsprices": (23, "Parts & Accessories")
}

last_update_id = None

# --- SQUARE INVOICE BY EMAIL ---
def fetch_square_invoices_by_email(email):
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('SQUARE_API_KEY')}",
            "Content-Type": "application/json",
            "Square-Version": "2025-02-20"
        }

        search_url = "https://connect.squareup.com/v2/customers/search"
        query = {
            "query": {
                "filter": {
                    "email_address": {"exact": email}
                }
            }
        }

        response = requests.post(search_url, headers=headers, json=query)
        customers = response.json().get("customers", [])
        if not customers:
            return f"No customer found with email: {email}"

        customer_id = customers[0]["id"]
        location_id = os.environ.get("SQUARE_LOCATION_ID")

        search_invoice_url = "https://connect.squareup.com/v2/invoices/search"
        invoice_query = {
            "query": {
                "filter": {
                    "location_ids": [location_id],
                    "customer_ids": [customer_id]
                }
            }
        }

        invoice_resp = requests.post(search_invoice_url, headers=headers, json=invoice_query)
        if invoice_resp.status_code != 200:
            return "Failed to retrieve invoices."

        invoices = invoice_resp.json().get("invoices", [])
        unpaid = []
        paid = []

        for inv in invoices:
            status = inv.get("status")
            if status in ["UNPAID", "SCHEDULED"]:
                unpaid.append(inv)
            elif status == "PAID":
                paid.append(inv)

        result = ""
        if unpaid:
            result += "\U0001F534 <b>Unpaid Invoices</b>\n"
            for u in unpaid:
                amount = u["payment_requests"][0]["computed_amount_money"]["amount"] / 100
                result += f"• #{u['invoice_number']} - ${amount:.2f}\nPay: https://app.squareup.com/pay-invoice/{u['id']}\n"
            result += "\n"

        if paid:
            result += "\U00002705 <b>Paid Invoices</b>\n"
            for p in paid[-5:]:
                amount = p["payment_requests"][0]["computed_amount_money"]["amount"] / 100
                result += f"• #{p['invoice_number']} - ${amount:.2f}\n"

        return result or "No invoices found."

    except Exception as e:
        print(f"[ERROR] Square Email Lookup: {e}", flush=True)
        return "An error occurred while retrieving your invoices."

# --- PRICING DATA ---
def fetch_category_prices(category_id, label):
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

        today = datetime.now().strftime("%B %d, %Y")
        message = f"<b>{label} - {today}</b>\n\n" + "\n".join(all_filtered)
        return message

    except Exception as e:
        print(f"[ERROR] Exception fetching category {category_id}: {e}", flush=True)
        return "Error fetching product data."

# --- UI HANDLERS ---
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
    requests.post(url, data=data)

def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🔍 See Prices"],
            ["👥 Hosting Clients"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_reply(chat_id, "Welcome to Refined Capital.\nChoose an option:", keyboard)

def send_prices_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🪙 All Miners", "₿ BTC Miners"],
            ["🚀 Doge/LTC Miners", "🧪 ALT Miners"],
            ["🔐 ALEO", "⚡ ALPH"],
            ["⛏️ KAS", "💾 ETC"],
            ["🇺🇸 USA Stock", "🔌 PDUs"],
            ["🔧 Transformers", "🧩 Parts"],
            ["🛒 Shop Now"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    send_reply(chat_id, "👇 Select a category to view prices:", keyboard)

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
    send_reply(chat_id, "Choose an option:", keyboard)

# --- MAIN LOOP ---
def check_user_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    params = {"offset": last_update_id + 1} if last_update_id else {}
    response = requests.get(url, params=params).json()

    for update in response.get("result", []):
        last_update_id = update.get("update_id")
        message = update.get("message", {})
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")
        cmd = text.lower()

        if cmd == "/start":
            send_main_menu(chat_id)

        elif text == "🔍 See Prices":
            send_prices_menu(chat_id)

        elif text == "👥 Hosting Clients":
            user_profiles[chat_id] = {"step": "name"}
            send_reply(chat_id, "Please enter your full name:")

        elif chat_id in user_profiles:
            profile = user_profiles[chat_id]
            step = profile.get("step")

            if step == "name":
                profile["name"] = text
                profile["step"] = "email"
                send_reply(chat_id, "Thanks! Now enter your email:")

            elif step == "email":
                profile["email"] = text
                profile["step"] = "done"
                send_reply(chat_id, f"Thanks, {profile['name']}!\nAccess granted.")
                send_hosting_menu(chat_id)

        elif text == "🧾 My Hosting Invoices":
            email = user_profiles.get(chat_id, {}).get("email")
            if not email:
                send_reply(chat_id, "Please start with /start and enter your info.")
            else:
                result = fetch_square_invoices_by_email(email)
                send_reply(chat_id, result)

        elif text == "🖥️ My Miners":
            send_reply(chat_id, "(MaintainX API integration coming soon)")

        elif text == "📦 My Orders":
            send_reply(chat_id, "(WooCommerce API integration coming soon)")

        elif cmd in {
            "🪙 all miners": "/allminerprices",
            "₿ btc miners": "/btcminerprices",
            "🚀 doge/ltc miners": "/dogeminerprices",
            "🧪 alt miners": "/altminerprices",
            "🔐 aleo": "/aleominerprices",
            "⚡ alph": "/alphminerprices",
            "💾 etc": "/etcminerprices",
            "⛏️ kas": "/kasminerprices",
            "🇺🇸 usa stock": "/usastockprices",
            "🔌 pdus": "/pduprices",
            "🔧 transformers": "/xfmrprices",
            "🧩 parts": "/partsprices"
        }:
            mapped = {
                "🪙 all miners": "/allminerprices",
                "₿ btc miners": "/btcminerprices",
                "🚀 doge/ltc miners": "/dogeminerprices",
                "🧪 alt miners": "/altminerprices",
                "🔐 aleo": "/aleominerprices",
                "⚡ alph": "/alphminerprices",
                "💾 etc": "/etcminerprices",
                "⛏️ kas": "/kasminerprices",
                "🇺🇸 usa stock": "/usastockprices",
                "🔌 pdus": "/pduprices",
                "🔧 transformers": "/xfmrprices",
                "🧩 parts": "/partsprices"
            }
            category_id = commands.get(mapped[cmd])
            if category_id:
                result = fetch_category_prices(category_id)
                send_reply(chat_id, result)

        elif cmd == "🛒 shop now":
            send_reply(chat_id, "🛒 Visit our full store: https://refined-capital.com/shop")

def flush_old():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    r = requests.get(url).json()
    if r.get("result"):
        last_update_id = r["result"][-1]["update_id"]

flush_old()
while True:
    try:
        check_user_messages()
    except Exception as e:
        print(f"[ERROR] Loop crash: {e}")
    time.sleep(2)
