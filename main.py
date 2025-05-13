import requests
import time
import os

from requests.auth import HTTPBasicAuth

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
        
# Start the loop
while True:
    try:
        track_price()
        check_user_messages()
    except Exception as e:
        print("Error:", e)
    time.sleep(10)  # Poll every 10 seconds
