from apexpro.constants import APEX_HTTP_TEST, APEX_HTTP_MAIN
from apexpro.http_public import HttpPublic

client = HttpPublic(APEX_HTTP_MAIN)
print(client.configs_v2())
print(client.history_funding_v2(symbol="BTC-USDT"))
print(client.klines(symbol="ETHUSDT",interval=5,start=1681463600, end=1681563600, limit=5))
print(client.server_time())
print(client.depth(symbol="BTC-USDC"))
print(client.trades(symbol="BTC-USDC"))
print(client.klines(symbol="BTC-USDT",interval="15"))
print(client.ticker(symbol="BTC-USDT"))
print(client.history_funding(symbol="BTC-USDT"))

print(client.depth(symbol="ETH-USDT",limit=50))
print(client.trades(symbol="ETH-USDT",limit=50))
print(client.klines(symbol="ETH-USDT",interval="15"))
print(client.history_funding_v2(symbol="ETH-USDT",limit=100,page=0,beginTimeInclusive=1662348573000,endTimeExclusive=1662434973000))
