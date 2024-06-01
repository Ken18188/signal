import os
import sys
import time
from flask import Flask, request, jsonify
from apexpro import HTTP as HttpPrivateStark
from apexpro.constants import APEX_HTTP_TEST, NETWORKID_TEST, APEX_HTTP_MAIN, NETWORKID_MAIN
from apexpro.http_public import HttpPublic

app = Flask(__name__)

# Load environment variables
key = os.getenv('API_KEY')
secret = os.getenv('API_SECRET')
passphrase = os.getenv('API_PASSPHRASE')
public_key = os.getenv('STARK_PUBLIC_KEY')
public_key_y_coordinate = os.getenv('STARK_PUBLIC_KEY_Y_COORDINATE')
private_key = os.getenv('STARK_PRIVATE_KEY')

if not all([key, secret, passphrase, public_key, public_key_y_coordinate, private_key]):
    raise ValueError("One or more environment variables are not set. Check your .env file and Render environment variables.")

client = HttpPrivateStark(
    APEX_HTTP_MAIN,
    network_id=NETWORKID_MAIN,
    stark_public_key=public_key,
    stark_private_key=private_key,
    stark_public_key_y_coordinate=public_key_y_coordinate,
    api_key_credentials={
        'key': key,
        'secret': secret,
        'passphrase': passphrase
    }
)

@app.route('/')
def home():
    return "This is working now!"

def calculate_stop_limit_params(entry_price, side):
    if side == "BUY":
        trigger_price = entry_price * 0.97
        price = trigger_price * 0.9999
        stop_side = "SELL"
    else:  # side == "SELL"
        trigger_price = entry_price * 1.03
        price = trigger_price * 1.0001
        stop_side = "BUY"
    trigger_price = format(trigger_price, '.5f')
    price = format(price, '.5f')
    return stop_side, trigger_price, price

@app.route('/trade', methods=['POST'])
def trade():
    try:
        data = request.json
        if not data or 'side' not in data or 'size' not in data:
            return jsonify({'error': 'Invalid input data'}), 400

        alert_side = data['side'].upper()  # or "SELL" from the alert
        alert_size = data['size']  # from the alert

        currentTime = time.time()
        limitFeeRate = client.account['takerFeeRate']

        worstPrice = client.get_worst_price(symbol="MATIC-USDC", side=alert_side, size=alert_size)
        if 'data' not in worstPrice:
            raise ValueError(f"Unexpected response format: {worstPrice}")
        price = worstPrice['data']['worstPrice']

        createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                             type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                             expirationEpochSeconds=currentTime)
        
        if createOrderRes.get('data', {}).get('status') == 'PENDING':
            entry_price = float(createOrderRes['data']['price'])
            stop_side, trigger_price, stop_price = calculate_stop_limit_params(entry_price, alert_side)
            stopLimitOrderRes = client.create_order(
                symbol="MATIC-USDC",
                side=stop_side,
                type="STOP_LIMIT",
                size=alert_size,
                expirationEpochSeconds=currentTime + 86400,  # 1 day in the future
                price=stop_price,
                limitFeeRate=limitFeeRate,
                triggerPriceType="INDEX",
                triggerPrice=trigger_price
            )
            print("Stop Limit Order Response:", stopLimitOrderRes)

        print(createOrderRes)
        return jsonify(createOrderRes)
    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
