import argparse
import time
import threading
import json
import socket
import os
from network.node import Node
from network.miner import Miner
from wallet.wallet import Wallet
from core.transaction import Transaction

def start_rpc(node: Node, miner: Miner, wallet: Wallet, rpc_port: int):
    """A simplistic RPC server allowing bitcoin_cli.py to trigger node actions locally."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", rpc_port))
    server.listen(1)
    
    def handle():
        while True:
            try:
                sock, _ = server.accept()
                f = sock.makefile('r')
                line = f.readline()
                if line:
                    req = json.loads(line)
                    cmd = req.get("method")
                    resp = {"result": None}
                    
                    if cmd == "getinfo":
                        resp["result"] = {
                            "height": node.blockchain.tip.height if node.blockchain.tip else 0, 
                            "peers": len(node.peers),
                            "mempool": len(node.mempool)
                        }
                    elif cmd == "balance":
                        bal = 0
                        utxos = []
                        for tid, outs in node.blockchain.utxo_set.items():
                            for idx, out in outs.items():
                                if out.address == wallet.get_address():
                                    bal += out.amount
                                    utxos.append({"txid": tid, "index": idx, "amount": out.amount})
                        resp["result"] = {"balance": bal, "utxos_count": len(utxos)}
                    elif cmd == "send":
                        to_addr = req["params"]["to"]
                        amt = req["params"]["amount"]
                        
                        utxos = []
                        for tid, outs in node.blockchain.utxo_set.items():
                            for idx, out in outs.items():
                                if out.address == wallet.get_address():
                                    utxos.append({"txid": tid, "index": idx, "amount": out.amount})
                        try:
                            # 10 is an arbitrary fee
                            tx = wallet.create_transaction(to_addr, amt, 10, utxos)
                            tx_hash = tx.id
                            with node.lock:
                                node.mempool[tx_hash] = tx
                                node.known_txs.add(tx_hash)
                                
                            from network.protocol import Message, CMD_INV
                            node.broadcast(Message(CMD_INV, {"inventory": [{"type": "tx", "hash": tx_hash}]}))
                            resp["result"] = {"txid": tx_hash, "msg": "Broadcasted successfully"}
                        except Exception as e:
                            resp["error"] = str(e)
                    
                    sock.sendall((json.dumps(resp)+"\n").encode())
            except Exception:
                pass
    threading.Thread(target=handle, daemon=True).start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8333, help="TCP port to listen on for P2P")
    parser.add_argument('--connect', type=str, default="", help="IP:PORT of initial peer")
    parser.add_argument('--mine', action='store_true', help="Start miner automatically")
    args = parser.parse_args()

    # Provide persistent identity for the node's mining wallet
    wallet_file = f"wallet_{args.port}.txt"
    if os.path.exists(wallet_file):
        with open(wallet_file, "r") as f:
            pk = f.read().strip()
        w = Wallet(pk)
    else:
        w = Wallet()
        with open(wallet_file, "w") as f:
            f.write(w.get_private_key())
    
    print(f"Node Mining Address: {w.get_address()}")
    
    node = Node("0.0.0.0", args.port)
    node.start()
    
    miner = Miner(node, w.get_address())
    if args.mine:
        miner.start()
    
    if args.connect:
        parts = args.connect.split(":")
        node.connect(parts[0], int(parts[1]))
        
    # Start RPC port mapped at +1000 for CLI tools
    start_rpc(node, miner, w, args.port + 1000)
    
    print("Daemon running. Press Ctrl+C to terminate.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()
        miner.stop()
