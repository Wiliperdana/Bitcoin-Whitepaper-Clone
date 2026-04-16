import time
import threading
from core.block import Block, BlockHeader
from core.transaction import create_coinbase_transaction
from network.node import Node
from network.protocol import Message, CMD_BLOCK, CMD_INV

class Miner(threading.Thread):
    def __init__(self, node: Node, miner_address: str):
        super().__init__(daemon=True)
        self.node = node
        self.miner_address = miner_address
        self.running = False
        self.interrupt = False
        
        # Hook into node to receive block notifications
        self.node.on_new_block_func = self.trigger_new_block
        
    def trigger_new_block(self):
        """Interrupts mining loop so miner can pull the new tip."""
        self.interrupt = True
        
    def stop(self):
        self.running = False
        self.interrupt = True
        
    def run(self):
        self.running = True
        while self.running:
            self.interrupt = False
            
            with self.node.lock:
                tip = self.node.blockchain.tip
                if not tip:
                    print("Miner waiting for Genesis block...")
                    time.sleep(1)
                    continue
                    
                prev_hash = tip.block.header.hash()
                target_bits = self.node.blockchain.calculate_next_target(tip)
                height = tip.height + 1
                
                # Deep copy pending txs from mempool to avoid mutation during mining
                # We limit to 10 for simplicity
                txs_to_mine = list(self.node.mempool.values())[:10]
            
            # Coinbase tx must be first!
            coinbase_tx = create_coinbase_transaction(self.miner_address, height)
            transactions = [coinbase_tx] + txs_to_mine
            
            block_header = BlockHeader(
                version=1,
                prev_block=prev_hash,
                merkle_root="0"*64, 
                timestamp=int(time.time()),
                target=target_bits,
                nonce=0
            )
            
            block = Block(header=block_header, transactions=transactions)
            block.header.merkle_root = block.calculate_merkle_root()
            
            print(f"[Miner] Working on block {height} with {len(txs_to_mine)} txs...")
            
            # Start Hashcash loop
            while self.running and not self.interrupt:
                if block.check_pow():
                    block_hash = block.header.hash()
                    print(f"*** Local Miner found Block {height}: {block_hash[:8]}... ***")
                    
                    # Instead of injecting via blockchain directly, we send it through Node handle_message 
                    # so loopback handles broadcast natively just like external incoming messages.
                    # Send a mock message from a fake sender, or just use node logic.
                    # Wait, calling add_block directly is safe because our Node lock handles it nicely.
                    
                    with self.node.lock:
                        success = self.node.blockchain.add_block(block)
                        if success:
                            # Clean mempool locally
                            for t in txs_to_mine:
                                if t.id in self.node.mempool:
                                    del self.node.mempool[t.id]
                    
                    if success:
                        self.node.broadcast(Message(CMD_BLOCK, block.to_dict()))
                        self.node.broadcast(Message(CMD_INV, {"inventory": [{"type": "block", "hash": block_hash}]}))
                        
                    break # Restart loop to build next block
                
                block.header.nonce += 1
                
                # Periodically yield back to update timestamp
                if block.header.nonce % 10000 == 0:
                    block.header.timestamp = int(time.time())

            if self.interrupt:
                # Got interrupted, likely by an incoming network block. Back off and restart.
                time.sleep(0.01)
