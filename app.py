from flask import Flask, jsonify, render_template
import requests
import json
import os

app = Flask(__name__)


last_wallet_address = "bc1qc4v832lfa6cqz5ccvjsu0s7eddfvq9w7grpnhy"
initial_price = 1.0  
price = initial_price  
transactions_file = 'static/transactions.json'


if not os.path.exists(transactions_file):
    with open(transactions_file, 'w') as f:
        json.dump([], f)  

# Функция для получения текущей цены Bitcoin
def get_current_price():
    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
    if response.status_code == 200:
        return response.json()['bitcoin']['usd']
    else:
        return None


@app.route('/')
def index():
    return render_template('index.html', last_wallet=last_wallet_address, current_price=price)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/status', methods=['GET'])
def status():
    return jsonify({"last_wallet": last_wallet_address, "current_price": price})


@app.route('/check_transaction/<wallet_address>', methods=['GET'])
def check_transaction(wallet_address):
    global last_wallet_address, price
    
    response = requests.get(f"https://blockchain.info/unspent?active={wallet_address}")
    
    if response.status_code == 200:
        transactions = response.json().get('unspent_outputs', [])
        
        if not transactions:
            return jsonify({"status": "error", "message": "No transactions found for this wallet."}), 404
        
        confirmed_transactions = []  
        
        for tx in transactions:
            amount = tx['value'] / 10**8  
            current_market_price = get_current_price()
            if current_market_price is None:
                return jsonify({"status": "error", "message": "Could not retrieve current Bitcoin price."}), 500
            
            if current_market_price - 1 <= amount <= current_market_price + 1:
                last_wallet_address = wallet_address  
                price *= 2
                
                confirmed_transactions.append({
                    "from": last_wallet_address,
                    "to": tx['tx_hash'],  
                    "amount": amount,
                    "tx_hash": tx['tx_hash']
                })

                with open(transactions_file, 'r+') as f:
                    data = json.load(f)
                    data.append(confirmed_transactions[-1]) 
                    f.seek(0) 
                    json.dump(data, f, indent=4)  
                
                return jsonify({
                    "status": "success",
                    "message": "Transaction confirmed.",
                    "new_price": price,
                    "last_paying_wallet": last_wallet_address,
                    "confirmed_transaction": confirmed_transactions[-1]
                }), 200
        
        return jsonify({"status": "error", "message": "Transaction amount not found within the expected range."}), 404
    
    return jsonify({"status": "error", "message": f"API error: {response.status_code}"}), 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
