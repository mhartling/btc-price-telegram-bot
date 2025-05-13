import os
import requests
from requests.auth import HTTPBasicAuth

# Load WooCommerce API credentials and endpoint from environment variables
WC_API_URL = os.environ.get("WC_API_URL")  # Example: https://refined-capital.com/wp-json/wc/v3
WC_API_KEY = os.environ.get("WC_API_KEY")
WC_API_SECRET = os.environ.get("WC_API_SECRET")
WC_CATEGORY_ID = os.environ.get("WC_CATEGORY_ID")  # Numeric ID or slug for the "miners" category

def get_valid_miner_products():
    url = f"{WC_API_URL}/products"
    auth = HTTPBasicAuth(WC_API_KEY, WC_API_SECRET)

    params = {
        "category": WC_CATEGORY_ID,
        "per_page": 100,         # Max 100 per page
        "status": "publish",     # Only published products
        "orderby": "date",
        "order": "desc"
    }

    try:
        print("[INFO] Fetching products from WooCommerce...", flush=True)
        response = requests.get(url, params=params, auth=auth)

        print(f"[DEBUG] Status code: {response.status_code}", flush=True)
        if response.status_code != 200:
            print(f"[ERROR] Failed request: {response.text}", flush=True)
            return

        products = response.json()
        print(f"[INFO] Retrieved {len(products)} products.", flush=True)

        valid_products = []

        for product in products:
            name = product.get("name")
            price = product.get("price")
            stock_status = product.get("stock_status")

            # Filter conditions
            if not price or price == "0":
                continue
            if stock_status != "instock":
                continue

            valid_products.append({
                "name": name,
                "price": price,
                "stock_status": stock_status
            })

        print(f"[INFO] Filtered to {len(valid_products)} valid products.", flush=True)

        # Output result
        for p in valid_products:
            print(f"{p['name']} - ${p['price']} ({p['stock_status']})", flush=True)

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}", flush=True)

# Run script
if __name__ == "__main__":
    get_valid_miner_products()
