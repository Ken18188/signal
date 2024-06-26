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
key = os.getenv('API_KEY')
secret = os.getenv('API_SECRET')
passphrase = os.getenv('API_PASSPHRASE')
public_key = os.getenv('STARK_PUBLIC_KEY')
public_key_y_coordinate = os.getenv('STARK_PUBLIC_KEY_Y_COORDINATE')
private_key = os.getenv('STARK_PRIVATE_KEY')

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

# Initialize a variable to store stop-limit order ID and open trade state
stop_limit_order_id = None
has_open_trade = False

def calculate_stop_limit_params(entry_price, side):
    if side == "BUY":
        trigger_price = entry_price * 0.97
        price = trigger_price * 0.9999
        stop_side = "SELL"
    else:  # side == "SELL"
        trigger_price = entry_price * 1.03
        price = trigger_price * 1.0001
        stop_side = "BUY"
    trigger_price = format(trigger_price, '.4f')
    price = format(price, '.4f')
    return stop_side, trigger_price, price

@app.route('/')
def home():
    return "This is working now!"

@app.route('/trade', methods=['POST'])
def trade():
    global stop_limit_order_id, has_open_trade
    try:
        data = request.json
        if not data or 'side' not in data or 'size' not in data or 'position' not in data:
            return jsonify({'error': 'Invalid input data'}), 400

        alert_side = data['side'].upper()
        alert_size = float(data['size'])
        alert_position = int(data['position'])

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
        price = float(worstPrice['data']['worstPrice'])

        # Check scenarios based on boolean and position
        if alert_position == 0:
            # Close existing trade
            has_open_trade = False
            createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                                 type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                                 expirationEpochSeconds=currentTime + 86400)
        elif has_open_trade and alert_position != 0:
            # Close existing trade and open a new trade with double the size
            alert_size *= 2
            createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                                 type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                                 expirationEpochSeconds=currentTime + 86400)
            has_open_trade = True
            alert_size /= 2  # Reset alert_size after the trade

            if createOrderRes.get('data'):
                entry_price = float(createOrderRes['data']['price'])
                stop_side, trigger_price, stop_price = calculate_stop_limit_params(entry_price, alert_side)
                stopLimitOrderRes = client.create_order(symbol="MATIC-USDC", side=stop_side,
                                                        type="STOP_LIMIT", size=alert_size,
                                                        expirationEpochSeconds=currentTime + 86400,
                                                        price=stop_price, limitFeeRate=limitFeeRate,
                                                        triggerPriceType="INDEX", triggerPrice=trigger_price)
                print("Stop Limit Order Response:", stopLimitOrderRes)
                if stopLimitOrderRes.get('data') and 'id' in stopLimitOrderRes['data']:
                    stop_limit_order_id = stopLimitOrderRes.get('data')['id']
        else:
            # Normal trade scenario
            createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                                 type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                                 expirationEpochSeconds=currentTime + 86400)
            has_open_trade = True

            if createOrderRes.get('data'):
                entry_price = float(createOrderRes['data']['price'])
                stop_side, trigger_price, stop_price = calculate_stop_limit_params(entry_price, alert_side)
                stopLimitOrderRes = client.create_order(symbol="MATIC-USDC", side=stop_side,
                                                        type="STOP_LIMIT", size=alert_size,
                                                        expirationEpochSeconds=currentTime + 86400,
                                                        price=stop_price, limitFeeRate=limitFeeRate,
                                                        triggerPriceType="INDEX", triggerPrice=trigger_price)
                print("Stop Limit Order Response:", stopLimitOrderRes)
                if stopLimitOrderRes.get('data') and 'id' in stopLimitOrderRes['data']:
                    stop_limit_order_id = stopLimitOrderRes.get('data')['id']

        print("Market Order Response:", createOrderRes)
        return jsonify({"market_order": createOrderRes, "stop_limit_order": stopLimitOrderRes})

    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
