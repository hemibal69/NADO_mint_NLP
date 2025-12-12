#!/usr/bin/env python3
import requests
import json
import time
from eth_account import Account
from eth_account.messages import encode_defunct

# ================== НАСТРОЙКИ ==================
PRIVATE_KEY = "0xВАШ_PRIVATE_KEY"  # <- вставь свой приватный ключ
SENDER = "ВАШ_subaccount_number"  # твой bytes32 subaccount
MINT_AMOUNT = 100  # токенов для будущего mint
CHECK_INTERVAL = 60  # секунд между проверками

V1_URL = "https://gateway.prod.nado.xyz/v1/query"

# ================== АККАУНТ ==================
account = Account.from_key(PRIVATE_KEY)
derived_address = account.address.lower()
print(f"[info] derived ETH address: {derived_address}")
print(f"[info] using SENDER bytes32: {SENDER}")

# ================== ФУНКЦИИ ==================
def post_v1_query(payload):
    try:
        r = requests.post(V1_URL, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data
    except requests.RequestException as e:
        print("Ошибка запроса (v1/query):", e)
        try:
            print("Ответ сервера:", e.response.text)
        except Exception:
            pass
        return None
    except ValueError as e:
        print("Ошибка парсинга JSON:", e)
        return None

def fetch_nlp_pool_balance(pool_id="NLP"):
    """
    Возвращает баланс NLP-пула по poolId
    """
    payload = {
        "type": "nlp_pool_info",
        "poolId": pool_id
    }
    data = post_v1_query(payload)
    if not data:
        return None
    if data.get("status") != "success":
        print("❌ NLP Pool API вернул ошибку:", data)
        return None
    pool_data = data.get("data", {})
    total_usdt = int(pool_data.get("totalUsdt", "0")) / 1e6
    return total_usdt

def fetch_max_nlp_mintable(sender_bytes32, product_id=1):
    """
    Возвращает максимум, который можно mint
    """
    payload = {
        "type": "max_nlp_mintable",
        "sender": sender_bytes32,
        "productId": product_id
    }
    data = post_v1_query(payload)
    if not data:
        return None
    if data.get("status") != "success":
        print("❌ max_nlp_mintable API вернул ошибку:", data)
        return None
    max_amount = int(data.get("data", {}).get("max_quote_amount", "0")) / 1e6
    return max_amount

def sign_mint_tx(amount_tokens, sender_bytes32, product_id=1):
    """
    Формирует и подписывает tx для будущего mint
    """
    amount_base = str(int(amount_tokens * 10**18))
    quote_low = str(int(amount_tokens * 1e18))   # пример диапазона
    quote_high = str(int(amount_tokens * 2e18))
    nonce = str(int(time.time()))
    tx = {
        "sender": sender_bytes32.replace("0x", ""),
        "productId": product_id,
        "amountBase": amount_base,
        "quoteAmountLow": quote_low,
        "quoteAmountHigh": quote_high,
        "nonce": nonce
    }
    tx_json = json.dumps(tx, separators=(",", ":"), sort_keys=True)
    message = encode_defunct(text=tx_json)
    signed = account.sign_message(message)
    signature = signed.signature.hex()
    return {"mint_lp": {"tx": tx, "signature": signature}}

# ================== ОСНОВНОЙ ЦИКЛ ==================
def main_loop():
    print(f"🚀 Запуск Mint NLP бота (MINT_AMOUNT={MINT_AMOUNT})\n")
    while True:
        try:
            pool_balance = fetch_nlp_pool_balance()
            if pool_balance is None:
                print("❌ Не удалось получить баланс пула.")
            else:
                print(f"[POOL] текущий баланс NLP-пула: {pool_balance} USDT0")

            max_mintable = fetch_max_nlp_mintable(SENDER)
            if max_mintable is None:
                print("❌ Не удалось получить max mintable.")
            else:
                print(f"[ACCOUNT] max доступно для mint: {max_mintable} USDT0")

            if pool_balance and pool_balance > 0 and max_mintable and max_mintable >= MINT_AMOUNT:
                print(f"💧 Условия выполнены — можно минтить {MINT_AMOUNT} токенов.")
                tx_payload = sign_mint_tx(MINT_AMOUNT, SENDER)
                # Здесь можно отправлять POST на gateway для mint
                # r = requests.post("https://gateway.prod.nado.xyz/v1", json=tx_payload)
                # print("Ответ на mint:", r.json())
            else:
                print("→ Пул не готов или недостаточно лимита для mint.")

        except Exception as ex:
            print("❌ Ошибка в основном цикле:", ex)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
