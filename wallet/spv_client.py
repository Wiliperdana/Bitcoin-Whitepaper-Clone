import socket
import threading
from typing import List, Dict
from network.protocol import Message, CMD_HEADERS, CMD_GETHEADERS, CMD_VERSION, CMD_ALERT
from core.block import BlockHeader, verify_merkle_proof

class SPVClient:
    def __init__(self):
        self.headers: List[BlockHeader] = [] 
        self.sock = None
        self.running = False

    def connect(self, node_host: str, node_port: int):
        print(f"SPV Client connecting to full node at {node_host}:{node_port}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((node_host, node_port))
        self.running = True
        
        threading.Thread(target=self._listen, daemon=True).start()
        
        # Send version to start sync, simulating height 0
        self.send(Message(CMD_VERSION, {"version": 1, "height": len(self.headers)}))

    def stop(self):
        self.running = False
        if self.sock: self.sock.close()

    def _listen(self):
        try:
             f = self.sock.makefile('r')
             while self.running:
                 line = f.readline()
                 if not line: break
                 try:
                     msg = Message.from_bytes(line.encode('utf-8'))
                     
                     if msg.command == CMD_HEADERS:
                         new_headers = msg.payload.get("headers", [])
                         for h_dict in new_headers:
                             header = BlockHeader(**h_dict)
                             self.headers.append(header)
                         print(f"[SPV] Synced up to {len(self.headers)} verified headers.")
                         
                     elif msg.command == CMD_ALERT:
                         print(f"*** [SPV SECURITY ALERT from network] ***")
                         print(f"Invalid block detected: {msg.payload.get('message')}")
                         print(f"SPV Client should ideally download the full block {msg.payload.get('hash')} to verify inconsistency manually.")
                         
                 except Exception as e:
                     print(f"SPV parse error: {e}")
        except Exception:
             pass

    def send(self, msg: Message):
        try:
            self.sock.sendall(msg.to_bytes())
        except Exception:
            pass
        
    def verify_transaction(self, tx_hash: str, proof: List[Dict[str, str]], block_height: int) -> bool:
        """
        Implements SPV: Section 8 of whitepaper.
        Verifies that a transaction is included in a block by mapping its Merkle proof 
        to the stored block header's Merkle root.
        """
        # Heights are 0-indexed in our list
        if block_height >= len(self.headers):
            print(f"[SPV] Cannot verify: block height {block_height} not synced yet.")
            return False
            
        header = self.headers[block_height]
        
        # Validate PoW of header just to be safe
        data = header.hash()
        if int(data, 16) > header.target:
             print("[SPV] Warning: stored header fails PoW!")
             return False
             
        # Map merkle branch
        if verify_merkle_proof(tx_hash, proof, header.merkle_root):
             print(f"[SPV] VERIFIED! Tx {tx_hash[:8]} is included at height {block_height}")
             return True
        else:
             print(f"[SPV] REJECTED! Tx {tx_hash[:8]} has invalid Merkle proof.")
             return False
