import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Callable
from core.crypto import verify_signature, hash160, sha256d

@dataclass
class TxIn:
    prev_tx: str  # Hex string of previous transaction hash
    prev_out_index: int
    signature: str = "" # Hex encoded signature
    pub_key: str = "" # Hex encoded public key

    def to_dict(self):
        return asdict(self)

@dataclass
class TxOut:
    amount: int
    address: str  # The hash160 of public key in hex

    def to_dict(self):
        return asdict(self)

class Transaction:
    def __init__(self, inputs: List[TxIn], outputs: List[TxOut]):
        self.inputs = inputs
        self.outputs = outputs
        self.id = self.calculate_hash()

    def to_dict(self, include_signatures=True):
        inputs_list = []
        for i in self.inputs:
            d = i.to_dict()
            if not include_signatures:
                d['signature'] = ""
                d['pub_key'] = ""
            inputs_list.append(d)
        
        return {
            'inputs': inputs_list,
            'outputs': [o.to_dict() for o in self.outputs]
        }
        
    @classmethod
    def from_dict(cls, data: dict):
        inputs = [TxIn(**i) for i in data.get('inputs', [])]
        outputs = [TxOut(**o) for o in data.get('outputs', [])]
        return cls(inputs, outputs)

    def calculate_hash(self) -> str:
        """Returns the hex string of the transaction's double SHA-256 hash."""
        data = json.dumps(self.to_dict(include_signatures=True), separators=(',', ':'), sort_keys=True).encode()
        return sha256d(data).hex()

    def get_sign_data(self) -> bytes:
        """
        Returns the raw data bytes used for creating and verifying signatures.
        """
        return json.dumps(self.to_dict(include_signatures=False), separators=(',', ':'), sort_keys=True).encode()

    def is_coinbase(self) -> bool:
        """Checks if this is a coinbase transaction."""
        return (len(self.inputs) == 1 and 
                self.inputs[0].prev_tx == "0" * 64 and 
                self.inputs[0].prev_out_index == 0xffffffff)

    def verify(self, get_prev_tx_out: Callable[[str, int], Optional[TxOut]]) -> bool:
        """
        Validates the transaction against the current UTXO set.
        `get_prev_tx_out` returns a TxOut given a txid and index.
        """
        if self.is_coinbase():
            return True

        input_sum = 0
        output_sum = 0
        sign_data = self.get_sign_data()

        for tx_in in self.inputs:
            prev_out = get_prev_tx_out(tx_in.prev_tx, tx_in.prev_out_index)
            if not prev_out:
                return False

            input_sum += prev_out.amount
            
            try:
                vk_bytes = bytes.fromhex(tx_in.pub_key)
                sig_bytes = bytes.fromhex(tx_in.signature)
            except ValueError:
                return False

            addr_check = hash160(vk_bytes).hex()
            if addr_check != prev_out.address:
                return False

            if not verify_signature(vk_bytes, sig_bytes, sign_data):
                return False

        for tx_out in self.outputs:
            if tx_out.amount < 0:
                return False
            output_sum += tx_out.amount

        if input_sum < output_sum:
            return False

        return True

    def calculate_fee(self, get_prev_tx_out: Callable[[str, int], Optional[TxOut]]) -> int:
        if self.is_coinbase():
            return 0
            
        input_sum = sum(get_prev_tx_out(tx_in.prev_tx, tx_in.prev_out_index).amount for tx_in in self.inputs)
        output_sum = sum(tx_out.amount for tx_out in self.outputs)
        return input_sum - output_sum

def create_coinbase_transaction(miner_address: str, block_height: int, block_reward: int = 5000000000) -> Transaction:
    """
    Creates a coinbase transaction. Halving isn't explicitly requested per exact height in instructions 
    but 50 BTC (in Satoshis) is standard. We embed height as pubkey to ensure distinct IDs.
    """
    # 0 * 64 is the classic null txid
    tx_in = TxIn(prev_tx="0" * 64, prev_out_index=0xffffffff, pub_key=str(block_height))
    tx_out = TxOut(amount=block_reward, address=miner_address)
    tx = Transaction(inputs=[tx_in], outputs=[tx_out])
    return tx
