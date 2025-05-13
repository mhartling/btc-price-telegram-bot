import requests
import time
import os

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

last_alert_price = None

def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    response = requests.get(url).json()
    return response['bitcoin']['usd']

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
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

while True:
    try:
        track_price()
    except Exception as e:
        print("Error:", e)
    time.sleep(60)
