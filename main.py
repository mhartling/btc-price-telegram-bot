import requests
import time
import os

from requests.auth import HTTPBasicAuth

WC_API_URL = os.environ.get("WC_API_URL")
WC_API_KEY = os.environ.get("WC_API_KEY")
WC_API_SECRET = os.environ.get("WC_API_SECRET")

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
BOT_API = f"https://api.telegram.org/bot{TOKEN}"

last_alert_price = None
last_update_id = None  # For reading messages without duplicates

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url).json()
    return response['bitcoin']['usd']

def send_telegram_message(message):
    url = f"{BOT_API}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": message
    }
    requests.post(url, data=data)

def track_price():
    global last_alert_price
    current_price = get_btc_price()
    rounded_price = round(current_price / 1000) * 1000

    if last_alert_price is None:
        last_alert_price = rounded_price
        return

    if rounded_price != last_alert_price:
        direction = "rises above" if rounded_price > last_alert_price else "drops below"
        message = f"BTC price {direction} ${rounded_price:,} (Current: ${current_price:,.2f})"
        send_telegram_message(message)
        last_alert_price = rounded_price

def check_user_messages():
    global last_update_id
    url = f"{BOT_API}/getUpdates"
    params = {
        "offset": last_update_id + 1 if last_update_id else None,
        "timeout": 5
    }
    response = requests.get(url, params=params).json()

    if not response.get("ok"):
        return

    for update in response["result"]:
        last_update_id = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if text.lower().startswith("/price"):
            current_price = get_btc_price()
            reply = f"Current BTC price: ${current_price:,.2f}"
            send_reply(chat_id, reply)
            
        if text.lower().startswith("/current_product_prices"):
            product_message = get_all_miners()
            send_reply(chat_id, product_message)
            
def send_reply(chat_id, message):
    url = f"{BOT_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, data=data)

def get_all_miners():
    url = f"{WC_API_URL}/products"
    auth = HTTPBasicAuth(WC_API_KEY, WC_API_SECRET)

    # Build query parameters
    params = {
        "per_page": 20,
        "orderby": "date",
        "order": "desc"
    }

    if WC_CATEGORY_ID:
        params["category"] = WC_CATEGORY_ID

    try:
        print("[DEBUG] Sending request to WooCommerce...", flush=True)
        print(f"[DEBUG] URL: {url}", flush=True)
        print(f"[DEBUG] Params: {params}", flush=True)

        response = requests.get(url, params=params, auth=auth)

        print(f"[DEBUG] Response status code: {response.status_code}", flush=True)

        if response.status_code != 200:
            print(f"[ERROR] WooCommerce API error: {response.text[:500]}", flush=True)
            return f"Error fetching miners: {response.status_code}"

        products = response.json()

        if not products:
            print("[DEBUG] No products found in response.", flush=True)
            return "No miners found in this category."

        message_lines = ["Current Miner Prices:"]
        for product in products:
            name = product.get("name", "Unnamed Product")
            price = product.get("price", "N/A")
            stock_status = product.get("stock_status", "unknown")
            message_lines.append(f"{name} - ${price} ({stock_status})")

        print(f"[DEBUG] Successfully fetched {len(products)} products.", flush=True)

        return "\n".join(message_lines)

    except Exception as e:
        print(f"[ERROR] Exception occurred during WooCommerce API request: {e}", flush=True)
        return "An error occurred while fetching miner data."
        
# Start the loop
while True:
    try:
        track_price()
        check_user_messages()
    except Exception as e:
        print("Error:", e)
    time.sleep(10)  # Poll every 10 seconds
