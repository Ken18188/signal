import os
import sys
import time
from flask import Flask, request, jsonify

from apexpro.http_private_stark_key_sign import HttpPrivateStark
root_path = os.path.abspath(__file__)
root_path = '/'.join(root_path.split('/')[:-2])
sys.path.append(root_path)

from apexpro.constants import APEX_HTTP_TEST, NETWORKID_TEST, APEX_HTTP_MAIN, NETWORKID_MAIN
from apexpro.http_public import HttpPublic

app = Flask(__name__)

# API credentials
key = '7d1e88d0-fc4c-332a-1e11-b774deed7309'
secret = 'USXjNlzihsRQFlmsgQKPMEXZQ9Oq7FyNoYf7Az69'
passphrase = 'SJTvx38yhMQ9piKmMWjp'

public_key = '0x06af05d2e4cfeaaa50d555e23ab90ee574bfcd3c415ca6884495fe542a182a3c'
public_key_y_coordinate = '0x047f6cbb00a509fb717d0596c26bf93d29abab2a3360a7c37942dfd9bc86137b'
private_key = '0x02fb8240493fbe24db7cc87d8d4f5e170c93c277624b51399b0da9b56bfacd7a'

client = HttpPrivateStark(APEX_HTTP_MAIN, network_id=NETWORKID_MAIN,
                          stark_public_key=public_key,
                          stark_private_key=private_key,
                          stark_public_key_y_coordinate=public_key_y_coordinate,
                          api_key_credentials={'key': key, 'secret': secret, 'passphrase': passphrase})

configs = client.configs()
client.get_user()
client.get_account()
symbolData = {}
for v in configs.get('data').get('perpetualContract', []):
    if v.get('symbol') == "MATIC-USDC":
        symbolData = v
        break

# Variable to store stop-limit order ID
stop_limit_order_id = None

def calculate_stop_limit_params(entry_price, side):
    if side == "BUY":
        trigger_price = entry_price * 0.97
        price = trigger_price * 0.9999
        stop_side = "SELL"
    else:  # side == "SELL"
        trigger_price = entry_price * 1.03
        price = trigger_price * 1.0001
        stop_side = "BUY"
    # Format to 4 decimal places
    trigger_price = format(trigger_price, '.4f')
    price = format(price, '.4f')
    return stop_side, trigger_price, price

@app.route('/')
def home():
    return "This is working now!"

@app.route('/trade', methods=['POST'])
def trade():
    global stop_limit_order_id
    try:
        data = request.json
        if not data or 'side' not in data or 'size' not in data or 'position' not in data:
            return jsonify({'error': 'Invalid input data'}), 400

        alert_side = data['side'].upper()  # or "SELL" from the alert
        alert_size = data['size']  # from the alert
        alert_position = int(data['position'])  # from the alert

        currentTime = time.time()
        limitFeeRate = client.account['takerFeeRate']

        # Cancel the existing stop-limit order if it exists
        if stop_limit_order_id:
            deleteOrderRes = client.delete_order(id=stop_limit_order_id)
            print("Delete Order Response:", deleteOrderRes)
            stop_limit_order_id = None

        worstPrice = client.get_worst_price(symbol="MATIC-USDC", side=alert_side, size=alert_size)
        if 'data' not in worstPrice:
            raise ValueError(f"Unexpected response format: {worstPrice}")
        price = worstPrice['data']['worstPrice']

        createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                             type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                             expirationEpochSeconds=currentTime + 86400)
        print("Market Order Response:", createOrderRes)

        if createOrderRes.get('data') and alert_position != 0:
            entry_price = float(createOrderRes['data']['price'])
            
            stop_side, trigger_price, stop_price = calculate_stop_limit_params(entry_price, alert_side)

            stopLimitOrderRes = client.create_order(symbol="MATIC-USDC", side=stop_side,
                                                    type="STOP_LIMIT", size=alert_size,
                                                    expirationEpochSeconds=currentTime + 86400,
                                                    price=stop_price, limitFeeRate=limitFeeRate,
                                                    triggerPriceType="INDEX", triggerPrice=trigger_price)
            print("Stop Limit Order Response:", stopLimitOrderRes)

            if stopLimitOrderRes.get('data') and 'id' in stopLimitOrderRes['data']:
                stop_limit_order_id = stopLimitOrderRes['data']['id']

            return jsonify({"market_order": createOrderRes, "stop_limit_order": stopLimitOrderRes})
        else:
            return jsonify({"market_order": createOrderRes})

    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
