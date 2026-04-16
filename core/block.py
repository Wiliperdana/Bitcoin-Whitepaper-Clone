import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict
from core.crypto import sha256d
from core.transaction import Transaction

def compute_merkle_root(txids: List[str]) -> str:
    if not txids:
        return "0" * 64
    
    current_level = txids[:]
    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
        
        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i+1]
            hashed = sha256d(bytes.fromhex(combined)).hex()
            next_level.append(hashed)
        current_level = next_level
        
    return current_level[0]

def compute_merkle_proof(txids: List[str], index: int) -> List[Dict[str, str]]:
    """Returns a list of dictionaries [{'hash': str, 'position': 'left'|'right'}]."""
    if not txids or index >= len(txids) or index < 0:
        return []
    
    current_level = txids[:]
    proof = []
    
    current_index = index
    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])
            
        is_right_child = current_index % 2 == 1
        sibling_index = current_index - 1 if is_right_child else current_index + 1
        
        proof.append({
            'hash': current_level[sibling_index],
            'position': 'left' if is_right_child else 'right'
        })
        
        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i+1]
            hashed = sha256d(bytes.fromhex(combined)).hex()
            next_level.append(hashed)
            
        current_level = next_level
        current_index //= 2
        
    return proof

def verify_merkle_proof(tx_hash: str, proof: List[Dict[str, str]], root: str) -> bool:
    current_hash = tx_hash
    for p in proof:
        if p['position'] == 'left':
            combined = p['hash'] + current_hash
        else:
            combined = current_hash + p['hash']
        current_hash = sha256d(bytes.fromhex(combined)).hex()
        
    return current_hash == root

@dataclass
class BlockHeader:
    version: int
    prev_block: str
    merkle_root: str
    timestamp: int
    target: int  # Store as absolute integer for precise difficulty
    nonce: int

    def to_dict(self):
        return asdict(self)

    def hash(self) -> str:
        data = json.dumps(self.to_dict(), separators=(',', ':'), sort_keys=True).encode()
        return sha256d(data).hex()

class Block:
    def __init__(self, header: BlockHeader, transactions: List[Transaction]):
        self.header = header
        self.transactions = transactions

    def to_dict(self):
        return {
            'header': self.header.to_dict(),
            'transactions': [tx.to_dict(include_signatures=True) for tx in self.transactions]
        }

    @classmethod
    def from_dict(cls, data: dict):
        header = BlockHeader(**data['header'])
        transactions = [Transaction.from_dict(tx) for tx in data['transactions']]
        return cls(header, transactions)

    def calculate_merkle_root(self) -> str:
        txids = [tx.calculate_hash() for tx in self.transactions]
        return compute_merkle_root(txids)

    def check_pow(self) -> bool:
        block_hash = self.header.hash()
        return int(block_hash, 16) < self.header.target
