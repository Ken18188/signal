import os
from flask import Flask, request, jsonify
from apexpro.http_private_stark_key_sign import HttpPrivateStark

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

@app.route('/trade', methods=['POST'])
def trade():
    try:
        data = request.json
        if not data or 'side' not in data or 'size' not in data:
            return jsonify({'error': 'Invalid input data'}), 400

        alert_side = data['side'].upper()
        alert_size = data['size']

        currentTime = time.time()
        limitFeeRate = client.account['takerFeeRate']

        worstPrice = client.get_worst_price(symbol="MATIC-USDC", side=alert_side, size=alert_size)
        if 'data' not in worstPrice:
            raise ValueError(f"Unexpected response format: {worstPrice}")
        price = worstPrice['data']['worstPrice']

        createOrderRes = client.create_order(symbol="MATIC-USDC", side=alert_side,
                                             type="MARKET", size=alert_size, price=price, limitFeeRate=limitFeeRate,
                                             expirationEpochSeconds=currentTime)
        print(createOrderRes)
        return jsonify(createOrderRes)
    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
