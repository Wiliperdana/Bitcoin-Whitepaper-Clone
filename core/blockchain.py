import time
import copy
from typing import List, Dict, Optional, Tuple
from core.block import Block, BlockHeader
from core.transaction import Transaction, TxOut

# Difficulty constants
# 20 bits of difficulty is appropriate for Python fast testing
INITIAL_TARGET = 2**(256 - 18) 
RETARGET_INTERVAL = 2016
TARGET_BLOCK_TIME = 10 * 60 # 10 minutes

class BlockNode:
    def __init__(self, block: Block, prev: Optional['BlockNode'], height: int, total_work: int):
        self.block = block
        self.prev = prev
        self.height = height
        self.total_work = total_work

class Blockchain:
    def __init__(self):
        self.nodes: Dict[str, BlockNode] = {} # Map block hash -> BlockNode
        self.tip: Optional[BlockNode] = None
        self.utxo_set: Dict[str, Dict[int, TxOut]] = {}

    def get_utxo(self, txid: str, index: int) -> Optional[TxOut]:
        return self.utxo_set.get(txid, {}).get(index)

    def rebuild_utxo(self, new_tip: BlockNode):
        """Rebuilds the UTXO set from genesis to new_tip. Extremely inefficient but correct for toy models."""
        self.utxo_set.clear()
        
        # Traverse back to genesis
        chain = []
        curr = new_tip
        while curr:
            chain.append(curr.block)
            curr = curr.prev
        chain.reverse()

        for block in chain:
            for tx in block.transactions:
                # Remove spent inputs
                if not tx.is_coinbase():
                    for tx_in in tx.inputs:
                        if tx_in.prev_tx in self.utxo_set and tx_in.prev_out_index in self.utxo_set[tx_in.prev_tx]:
                            del self.utxo_set[tx_in.prev_tx][tx_in.prev_out_index]
                            if not self.utxo_set[tx_in.prev_tx]:
                                del self.utxo_set[tx_in.prev_tx]

                # Add new outputs
                tx_id = tx.id
                if tx_id not in self.utxo_set:
                    self.utxo_set[tx_id] = {}
                for idx, tx_out in enumerate(tx.outputs):
                    self.utxo_set[tx_id][idx] = tx_out

    def validate_block(self, block: Block, prev_node: Optional[BlockNode]) -> bool:
        # 1. Check PoW
        if not block.check_pow():
            print("Block PoW fails")
            return False
            
        # 2. Check previous hash
        if prev_node:
            if block.header.prev_block != prev_node.block.header.hash():
                 return False
        elif block.header.prev_block != "0" * 64:
             return False # Not a valid genesis block
             
        # 3. Check Merkle Root
        if block.calculate_merkle_root() != block.header.merkle_root:
            print("Merkle root mismatch")
            return False

        # 4. Check target/difficulty adjustment match
        expected_target = self.calculate_next_target(prev_node)
        if block.header.target != expected_target:
            print(f"Target mismatch {block.header.target} != {expected_target}")
            return False

        return True

    def validate_transactions(self, block: Block, prev_node: Optional[BlockNode]) -> bool:
        # Since we just rebuild UTXO to check efficiently against branching logic,
        # we dry-run a rebuild up to the previous node, check the current block, and revert if it fails.
        # For simplicity, we just clone the current UTXO set or rebuild if needed.
        
        # Fast path: if the block extends our current tip, just use current UTXO set.
        if prev_node == self.tip:
            temp_utxo = copy.deepcopy(self.utxo_set)
        else:
            # Slower path: rebuild UTXO to the prev_node
            old_tip = self.tip
            self.rebuild_utxo(prev_node)
            temp_utxo = copy.deepcopy(self.utxo_set)
            self.rebuild_utxo(old_tip) # Restore

        # Validate with temp_utxo
        def get_tx_out(txid, index):
            return temp_utxo.get(txid, {}).get(index)

        # Check transactions
        for i, tx in enumerate(block.transactions):
            if i == 0:
                if not tx.is_coinbase(): return False
            else:
                if tx.is_coinbase(): return False
                
            if not tx.verify(get_tx_out):
                 return False
                 
            # Apply to temp_utxo to support intra-block spending
            if not tx.is_coinbase():
                 for tx_in in tx.inputs:
                     del temp_utxo[tx_in.prev_tx][tx_in.prev_out_index]
            temp_idx = tx.id
            if temp_idx not in temp_utxo: temp_utxo[temp_idx] = {}
            for idx, tx_out in enumerate(tx.outputs):
                 temp_utxo[temp_idx][idx] = tx_out

        return True

    def calculate_next_target(self, prev_node: Optional[BlockNode]) -> int:
        if not prev_node:
            return INITIAL_TARGET
            
        # We only retarget every RETARGET_INTERVAL blocks
        if (prev_node.height + 1) % RETARGET_INTERVAL != 0:
            return prev_node.block.header.target
            
        # Traverse back RETARGET_INTERVAL blocks
        curr = prev_node
        for _ in range(RETARGET_INTERVAL - 1):
            if curr.prev:
                curr = curr.prev
                
        first_block_time = curr.block.header.timestamp
        last_block_time = prev_node.block.header.timestamp
        
        actual_timespan = last_block_time - first_block_time
        target_timespan = TARGET_BLOCK_TIME * RETARGET_INTERVAL
        
        # Bounds to prevent extreme jumps
        if actual_timespan < target_timespan // 4:
            actual_timespan = target_timespan // 4
        if actual_timespan > target_timespan * 4:
            actual_timespan = target_timespan * 4
            
        new_target = (prev_node.block.header.target * actual_timespan) // target_timespan
        return new_target

    def add_block(self, block: Block) -> bool:
        block_hash = block.header.hash()
        if block_hash in self.nodes:
            return True # Already have it
            
        prev_node = self.nodes.get(block.header.prev_block)
        if not prev_node and block.header.prev_block != "0"*64:
            print("Missing previous block (orphan)")
            return False

        if not self.validate_block(block, prev_node):
            return False

        if not self.validate_transactions(block, prev_node):
            print("Transaction validation failed")
            return False

        height = prev_node.height + 1 if prev_node else 0
        
        # Calculate work (simplification: target is inversely proportional to work)
        work = (2**256) // (block.header.target + 1)
        total_work = prev_node.total_work + work if prev_node else work

        new_node = BlockNode(block, prev_node, height, total_work)
        self.nodes[block_hash] = new_node

        # Consensus rule: Longest chain (most total work)
        if not self.tip or new_node.total_work > self.tip.total_work:
            # Reorg if necessary
            self.rebuild_utxo(new_node)
            self.tip = new_node
            print(f"New tip! Height: {height}, Hash: {block_hash[:8]}...")
            return True
            
        print(f"Accepted branch block at height {height}")
        return True

    def get_main_chain(self) -> List[Block]:
        chain = []
        curr = self.tip
        while curr:
            chain.append(curr.block)
            curr = curr.prev
        chain.reverse()
        return chain
