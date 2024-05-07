from apexpro.http_private import HttpPrivate
from apexpro.constants import APEX_HTTP_MAIN, NETWORKID_MAIN

from flask import Flask
import os


app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'



def get_balance():
    key = '9a8408c6-4292-5513-cb1c-20fcbc4c8077'
    secret = 'QSs6JH3NjLbMsXLP-gl32uDNkE_-QCEKICso4boo'
    passphrase = 'a32muWF4n8RAmLN7JpSq'
    client = HttpPrivate(APEX_HTTP_MAIN, network_id=NETWORKID_MAIN, api_key_credentials={'key': key, 'secret': secret, 'passphrase': passphrase})
    accountRes = client.get_account_balance()
    return str(accountRes)
