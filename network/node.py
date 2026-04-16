import socket
import threading
import json
import time
from typing import Dict, Set

from core.blockchain import Blockchain
from core.transaction import Transaction
from core.block import Block, BlockHeader
from network.protocol import *

class PeerConnection(threading.Thread):
    def __init__(self, node, sock, address):
        super().__init__(daemon=True)
        self.node = node
        self.sock = sock
        self.address = address
        self.running = True

    def run(self):
        try:
            f = self.sock.makefile('r')
            while self.running:
                line = f.readline()
                if not line:
                    break
                try:
                    msg = Message.from_bytes(line.encode('utf-8'))
                    self.node.handle_message(msg, self)
                except Exception as e:
                    print(f"Error parsing message from {self.address}: {e}")
        except Exception as e:
            print(f"Connection error with {self.address}: {e}")
        finally:
            self.node.disconnect(self)

    def send(self, msg: Message):
        try:
            self.sock.sendall(msg.to_bytes())
        except Exception:
            self.node.disconnect(self)

class Node:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        
        self.peers: Set[PeerConnection] = set()
        self.blockchain = Blockchain()
        self.mempool: Dict[str, Transaction] = {}
        
        # Track what we've broadcasted to prevent loops
        self.known_txs = set()
        self.known_blocks = set()
        
        self.lock = threading.Lock()
        self.running = False
        
        # Events for the miner to hook into
        self.on_new_block_func = None

    def start(self):
        self.running = True
        self.server.listen(10)
        print(f"Node listening on {self.host}:{self.port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.server.close()
        for peer in list(self.peers):
            peer.sock.close()

    def _accept_loop(self):
        while self.running:
            try:
                sock, addr = self.server.accept()
                peer = PeerConnection(self, sock, addr)
                with self.lock:
                    self.peers.add(peer)
                peer.start()
                # Automatically sync
                self._send_version(peer)
            except Exception:
                pass

    def connect(self, host: str, port: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
            peer = PeerConnection(self, sock, (host, port))
            with self.lock:
                self.peers.add(peer)
            peer.start()
            self._send_version(peer)
        except Exception as e:
            print(f"Failed to connect to {host}:{port} : {e}")

    def disconnect(self, peer: PeerConnection):
        peer.running = False
        with self.lock:
            if peer in self.peers:
                self.peers.remove(peer)
        try:
            peer.sock.close()
        except:
            pass

    def broadcast(self, msg: Message, exclude_peer: PeerConnection = None):
        with self.lock:
            for peer in self.peers:
                if peer != exclude_peer:
                    peer.send(msg)

    def _send_version(self, peer: PeerConnection):
        height = self.blockchain.tip.height if self.blockchain.tip else 0
        peer.send(Message(CMD_VERSION, {"version": 1, "height": height}))

    def handle_message(self, msg: Message, sender: PeerConnection):
        if msg.command == CMD_VERSION:
            if not self.blockchain.tip:
                sender.send(Message(CMD_GETHEADERS, {"hash": "0"*64}))
            else:
                sender.send(Message(CMD_VERACK, {}))
                if msg.payload.get("height", 0) > self.blockchain.tip.height:
                    # We are behind, ask for blocks
                    sender.send(Message(CMD_GETDATA, {"type": "block", "hash": self.blockchain.tip.block.header.hash()}))

        elif msg.command == CMD_INV:
            for item in msg.payload.get("inventory", []):
                inv_type = item["type"]
                inv_hash = item["hash"]
                if inv_type == "tx" and inv_hash not in self.known_txs and inv_hash not in self.mempool:
                    sender.send(Message(CMD_GETDATA, {"type": "tx", "hash": inv_hash}))
                elif inv_type == "block" and inv_hash not in self.known_blocks and inv_hash not in self.blockchain.nodes:
                    sender.send(Message(CMD_GETDATA, {"type": "block", "hash": inv_hash}))

        elif msg.command == CMD_GETDATA:
            req_type = msg.payload.get("type")
            req_hash = msg.payload.get("hash")
            if req_type == "tx" and req_hash in self.mempool:
                sender.send(Message(CMD_TX, self.mempool[req_hash].to_dict(include_signatures=True)))
            elif req_type == "block":
                if req_hash in self.blockchain.nodes:
                    b = self.blockchain.nodes[req_hash].block
                    sender.send(Message(CMD_BLOCK, b.to_dict()))
                elif req_hash == "0"*64 and self.blockchain.tip:
                    # Requesting from genesis? Send full chain
                    chain = self.blockchain.get_main_chain()
                    for b in chain:
                        sender.send(Message(CMD_BLOCK, b.to_dict()))

        elif msg.command == CMD_TX:
            tx = Transaction.from_dict(msg.payload)
            tx_hash = tx.calculate_hash()
            with self.lock:
                if tx_hash not in self.known_txs and tx_hash not in self.mempool:
                    # Basic verify: we might not be able to verify easily if we don't have UTXO lock,
                    # but we'll do an optimistic add for purely P2P propagation or test against tip
                    # Real nodes check strictly before mempool insertion
                    # We will optimistic-broadcast
                    self.known_txs.add(tx_hash)
                    self.mempool[tx_hash] = tx
                    
            # Relay
            self.broadcast(Message(CMD_INV, {"inventory": [{"type": "tx", "hash": tx_hash}]}), sender)

        elif msg.command == CMD_BLOCK:
            block = Block.from_dict(msg.payload)
            block_hash = block.header.hash()
            
            with self.lock:
                if block_hash in self.known_blocks or block_hash in self.blockchain.nodes:
                    return
                self.known_blocks.add(block_hash)
            
            # Try to add block
            with self.lock:
                success = self.blockchain.add_block(block)
                if success:
                    # Clean up mempool
                    for tx in block.transactions:
                        if tx.id in self.mempool:
                            del self.mempool[tx.id]
                            
                    # Inform miner to restart
                    if self.on_new_block_func:
                        self.on_new_block_func()
                    
                    # Relay
                    print(f"[Node {self.port}] Accepted new block: {block_hash[:8]}")
                    self.broadcast(Message(CMD_INV, {"inventory": [{"type": "block", "hash": block_hash}]}), sender)
                else:
                    print(f"[Node {self.port}] Rejected block: {block_hash[:8]}")
                    # In a real node we might issue an ALERT to SPV clients here if check_pow passed but txs failed
                    if block.check_pow():
                        self.broadcast(Message(CMD_ALERT, {"message": f"Invalid block detected: {block_hash}", "hash": block_hash}))

        elif msg.command == CMD_GETHEADERS:
            # Send all headers from requested hash to tip
            chain = self.blockchain.get_main_chain()
            headers = [b.header.to_dict() for b in chain]
            sender.send(Message(CMD_HEADERS, {"headers": headers}))
