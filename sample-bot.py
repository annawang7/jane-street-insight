#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="BULBASAUR"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = False

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index=0
prod_exchange_hostname="production"

port=25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

# ~~~~~============== NETWORKING CODE ==============~~~~~
def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)

def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")

def read_from_exchange(exchange):
    return json.loads(exchange.readline())


# ~~~~~============== MAIN LOOP ==============~~~~~
exchange = None
orders_placed = 0
position = 0
BUY_NUM = 0
SELL_NUM = 1
pending_orders = []
pending_buy_orders = {"BOND": 0, "VALBZ": 0, "VALE": 0}
pending_sell_orders = {"BOND": 0, "VALBZ": 0, "VALE": 0}
positions = {"BOND": 0, "VALBZ": 0, "VALE": 0}

def main():
    global exchange
    exchange = connect()
    hello()
    hello_from_exchange = read_from_exchange(exchange)
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)
    positions["BOND"] = hello_from_exchange["symbols"][0]["position"]
    add("BOND", "BUY", 999, 100 - positions["BOND"])
    add("BOND", "SELL", 1001, 100 + positions["BOND"])

    while (True):
        server_msg = read_from_exchange(exchange)
        listen_for_fills(server_msg)

def hello():
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})

def add(symbol, direction, price, size):
    # Update order id to be order placed number
    global orders_placed
    orders_placed += 1
    # Add to pending orders list
    global pending_orders
    pending_orders.append(orders_placed)
    print("Order Placed: " + str(orders_placed))

    # Increment Buy Orders If Necessary
    if (direction == "BUY"):
        global pending_buy_orders
        pending_buy_orders[symbol] += size
    elif (direction == "SELL"):
        global pending_sell_orders
        pending_sell_orders[symbol] += size
    # Add order to exchange
    write_to_exchange(exchange, {"type": "add", "order_id": orders_placed, "symbol": symbol,
        "dir":direction, "price":price, "size": size, })
    read_from_exchange(exchange)

def cancel(order_id):
    write_to_exchange(exchange, {"type": "cancel", "order_id": order_id})

def listen_for_fills(server_msg):
    if (server_msg["type"] == "fill"):
        order_num = server_msg["order_id"]
        symbol = server_msg["symbol"]
        size = server_msg["size"]
        print("Order Partially Filled: " + str(order_num))
        if (server_msg["dir"] == "BUY"):
            add("BOND", "SELL", 1001, size)
            pending_buy_orders[symbol] -= size
        elif (server_msg["dir"] == "SELL"):
            add("BOND", "BUY", 999, size)
            pending_sell_orders[symbol] -= size

def listen_for_errors(server_msg):
    if (server_msg["type"] == "REJECT"):
        print("Order failed")
        add("BOND", "BUY", 999, 100 - positions["BOND"])
        add("BOND", "SELL", 1001, 100 + positions["BOND"])

if __name__ == "__main__":
    main()
