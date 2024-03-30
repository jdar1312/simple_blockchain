import sys
import time
import tornado
from miner import Miner
from node import Node
from connections import run_server, remote_connection

MINER_ADDRESS = b'THd\x14\x13\xbe\x0f\t"\xbaOe\x05\xb66f\xb9w\xd78' # <--- 5448641413be0f0922ba4f6505b63666b977d738

if __name__ == "__main__":
    if len(sys.argv) == 1:
        REMOTE_NODES = ["ws://node.zimcoin.org:46030/"]
        node = Node.start("./blocks.sqlite").proxy()
        miner = Miner.start(node, MINER_ADDRESS).proxy()

        for remote in REMOTE_NODES:
            remote_connection(node, remote)
        miner.start_mining()

        tornado.ioloop.IOLoop.current().start()
    elif sys.argv[1] == 'server':
        PORT = 46030
        REMOTE_NODES = []
        node = Node.start("./blocks.sqlite").proxy()
        miner = Miner.start(node, MINER_ADDRESS).proxy()
        miner.start_mining()
        run_server(node, PORT)
    else:
        print("Unknown command")
