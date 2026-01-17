from kalshi_simple_ws_orderbook.orderbook_manager import OrderbookManager
from kalshi_simple_ws_orderbook.runner import start_background_feed
from kalshi_simple_ws_orderbook.kalshi_clients import KalshiWebSocketClient, Environment
from cryptography.hazmat.primitives import serialization, hashes
import time
manager = OrderbookManager()

API_KEY_ID = "YOUR API KEY"
PRIVATE_KEY_PATH = "kalshikey.pem"

try:
    with open('kalshkey.pem', "rb") as key_file:
        PRIVATE_KEY = serialization.load_pem_private_key(
            key_file.read(),
            password=None  # Provide the password if your key is encrypted
        )

except Exception as e:
    raise Exception(f"Error loading private key: {str(e)}")

ws_client = KalshiWebSocketClient(
    key_id=API_KEY_ID,
    private_key=PRIVATE_KEY,
    environment=Environment.PROD
)

start_background_feed(
    manager,
    ws_client,
    market_tickers=["KXPRESPERSON-28-JVAN"]
)
time.sleep(2)




# get Liquidity stats
liq = manager.calculate_liquidity_in_range("KXPRESPERSON-28-JVAN", side="yes", price_delta_cents=5)


print(liq)




# Basic Book
book = manager.get_orderbook("KXPRESPERSON-28-JVAN")


print(book)


