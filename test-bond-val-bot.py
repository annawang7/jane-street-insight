#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json
import time

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name="BULBASAUR"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = True

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
pending_orders = []
pending_buy_orders = {"BOND": 0, "VALBZ": 0, "VALE": 0, "XLF": 0}
pending_sell_orders = {"BOND": 0, "VALBZ": 0, "VALE": 0, "XLF": 0}
positions = {"BOND": 0, "VALBZ": 0, "VALE": 0, "XLF": 0}
vale_buy_pending_id = None
vale_sell_pending_id = None
vale_sell = 0
vale_buy = 0

xlf_buy_pending_id = None
xlf_sell_pending_id = None
xlf_sell = 0
xlf_buy = 0

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
    global positions
    positions["BOND"] = hello_from_exchange["symbols"][0]["position"]
    positions["VALE"] = hello_from_exchange["symbols"][5]["position"]
    positions["VALBZ"] = hello_from_exchange["symbols"][4]["position"]
    positions["XLF"] = hello_from_exchange["symbols"][7]["position"]

    add("BOND", "BUY", 999, 100 - positions["BOND"])
    add("BOND", "SELL", 1001, 100 + positions["BOND"])

    while (True):
        server_msg = read_from_exchange(exchange)
        buy_sell_vale()
        buy_sell_xlf()
        listen_for_fills(server_msg)
        listen_for_book(server_msg)
        listen_for_errors(server_msg)
        
def hello():
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})

def add(symbol, direction, price, size):
    # Update order id to be order placed number
    global orders_placed
    orders_placed += 1
    # Add to pending orders list
    global pending_orders
    pending_orders.append(orders_placed)
    #if symbol == "VALE":
    print("Order Placed: " + str(orders_placed) + " Position: " + str(positions[symbol])+ " Size: " + str(size) + " Dir: " + direction + " Symbol: " + symbol + " Price: " + str(price) + "")

    # Increment Buy Orders If Necessary
    if (direction == "BUY"):
        global pending_buy_orders
        pending_buy_orders[symbol] += size
    elif (direction == "SELL"):
        global pending_sell_orders
        pending_sell_orders[symbol] += size
    # Add order to exchange
    write_to_exchange(exchange, {"type": "add", "order_id": orders_placed, "symbol": symbol,
        "dir":direction, "price":price, "size": size })
    # 
    read_from_exchange(exchange)

def cancel(order_id):
    write_to_exchange(exchange, {"type": "cancel", "order_id": order_id}) 

def listen_for_fills(server_msg):
    if (server_msg["type"] == "fill"):
        # Get info of filled order
        order_num = server_msg["order_id"]
        symbol = server_msg["symbol"]
        size = server_msg["size"]
        direction = server_msg["dir"]
        global positions
        # Update bond order fill and buy/sell as necessary
        if (symbol == "BOND"):
            # print("Bond Order Partially Filled: " + str(order_num))
            if (direction == "BUY"):
                pending_buy_orders[symbol] -= size
                add("BOND", "SELL", 1001, size)
            elif (direction == "SELL"):
                pending_sell_orders[symbol] -= size
                add("BOND", "BUY", 999, size)
        # Update Vale Order fill and hedge as necessary
        if (symbol == "VALE"):
            print("Vale Order Filled: " + str(order_num) + " " + direction + " Size: " + str(size))
            if (direction == "BUY"):
                pending_buy_orders[symbol] -= size
                positions["VALE"] += size
            elif (direction == "SELL"):
                positions["VALE"] -= size
                pending_sell_orders[symbol] -= size
        if (symbol == "XLF"):
            print("XLF Order Filled: " + str(order_num) + " " + direction + " Size: " + str(size))
            if (direction == "BUY"):
                pending_buy_orders[symbol] -= size
                positions["XLF"] += size
            elif (direction == "SELL"):
                positions["XLF"] -= size
                pending_sell_orders[symbol] -= size

def listen_for_book(server_msg):
    if (server_msg["type"] == "book"):
        global vale_sell
        global vale_buy
        global xlf_sell
        global xlf_buy
        if (server_msg["symbol"] == "VALE"):
            if len(server_msg["sell"]) > 0:
                vale_sell = server_msg["sell"][0][0]
            if len(server_msg["buy"]) > 0:
                vale_buy = server_msg["buy"][0][0]
        if (server_msg["symbol"] == "XLF"):
            if len(server_msg["sell"]) > 0:
                xlf_sell = server_msg["sell"][0][0]
            if len(server_msg["buy"]) > 0:
                xlf_buy = server_msg["buy"][0][0]

def buy_sell_vale():
    if vale_buy > 0 and vale_sell > 0:
        global pending_sell_orders
        global pending_buy_orders
        if ( pending_buy_orders["VALE"] + positions["VALE"] < 10):
            global vale_buy_pending_id
            if vale_buy_pending_id:
                cancel(vale_buy_pending_id)
                pending_buy_orders["VALE"] = 0
                vale_buy_pending_id = None
                print("Cancel VALE BUY Order: " + str(orders_placed))
                time.sleep(1)
                num_stock = 10 - positions["VALE"]
                add("VALE", "BUY", vale_buy + 1, 10 - positions["VALE"])

            vale_buy_pending_id = orders_placed
        elif (positions["VALE"] - pending_sell_orders["VALE"] > -10):
            global vale_sell_pending_id
            if vale_sell_pending_id:
                print("Cancel VALE Sell Order: " + str(orders_placed))
                cancel(vale_sell_pending_id)
                pending_sell_orders["VALE"] = 0
                vale_sell_pending_id = None
                time.sleep(1)
                num_stock = 10 - positions["VALE"]
                add("VALE", "SELL", vale_sell - 1, num_stock)
            vale_sell_pending_id = orders_placed

def buy_sell_xlf():
    if xlf_buy > 0 and xlf_sell > 0:
        global pending_sell_orders
        global pending_buy_orders
        if ( pending_buy_orders["XLF"] + positions["XLF"] < 100):
            global xlf_buy_pending_id
            if xlf_buy_pending_id:
                cancel(xlf_buy_pending_id)
                pending_buy_orders["XLF"] = 0
                xlf_buy_pending_id = None
                print("Cancel XLF Order: " + str(orders_placed))
                time.sleep(1)
                add("XLF", "BUY", xlf_buy + 1, 100 - positions["XLF"])
            xlf_buy_pending_id = orders_placed
        elif (positions["XLF"] - pending_sell_orders["XLF"] > -100):
            global xlf_sell_pending_id
            if xlf_sell_pending_id:
                print("Cancel XLF Order: " + str(orders_placed))
                cancel(xlf_sell_pending_id)
                pending_sell_orders["XLF"] = 0
                xlf_sell_pending_id = None
                time.sleep(1)
                add("XLF", "SELL", xlf_sell - 1, 100 + positions["XLF"])
            xlf_sell_pending_id = orders_placed

def listen_for_errors(server_msg):
    if (server_msg["type"] == "reject"):
        print("ERROR: ORDER FAILED, id: " + str(server_msg["order_id"]) + " " + server_msg["error"])
    if (server_msg["type"] == "error"):
        print("ERROR: ORDER FAILED, id: " + str(id) + " " + server_msg["error"])
    if (server_msg["type"] == "ack"):
        print("Order Completed: " + str(server_msg["order_id"]))
    if (server_msg["type"] == "out"):
        print("Order Successfully Canceled: " + str(server_msg["order_id"]))

        #add("BOND", "BUY", 999, 100 - positions["BOND"])
        #add("BOND", "SELL", 1001, 100 + positions["BOND"])

if __name__ == "__main__":
    main()
