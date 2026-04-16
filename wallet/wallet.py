import json
from ecdsa import SigningKey, SECP256k1
from core.crypto import generate_key_pair, hash160, sign_data
from core.transaction import Transaction, TxIn, TxOut

class Wallet:
    def __init__(self, private_key_hex=None):
        if private_key_hex:
            self.sk = SigningKey.from_string(bytes.fromhex(private_key_hex), curve=SECP256k1)
            self.vk = self.sk.get_verifying_key()
        else:
            self.sk, self.vk = generate_key_pair()
            
        self.vk_bytes = self.vk.to_string()
        self.address = hash160(self.vk_bytes).hex()

    def get_address(self) -> str:
        return self.address
        
    def get_private_key(self) -> str:
        return self.sk.to_string().hex()

    def create_transaction(self, to_address: str, amount: int, fee: int, utxos: list) -> Transaction:
        """
        Constructs and signs a transaction.
        `utxos` is a list of available funds, format: 
        [{'txid': str, 'index': int, 'amount': int}, ...]
        """
        inputs = []
        input_sum = 0
        
        for utxo in utxos:
            input_sum += utxo['amount']
            inputs.append(TxIn(
                prev_tx=utxo['txid'],
                prev_out_index=utxo['index'],
                pub_key=self.vk_bytes.hex()
            ))
            if input_sum >= amount + fee:
                break
                
        if input_sum < amount + fee:
             raise ValueError(f"Insufficient funds. Have {input_sum}, need {amount+fee}")
             
        outputs = [TxOut(amount=amount, address=to_address)]
        
        # Change back to ourselves
        change = input_sum - amount - fee
        if change > 0:
            outputs.append(TxOut(amount=change, address=self.address))
            
        tx = Transaction(inputs=inputs, outputs=outputs)
        
        # Sign the hash using our private key
        # Since we use a simple signature hashing scheme, we generate it once
        sign_data_bytes = tx.get_sign_data()
        signature = sign_data(self.sk, sign_data_bytes)
        
        # Apply signatures
        for tx_in in tx.inputs:
            tx_in.signature = signature.hex()
            
        # Re-initialize the finalized ID
        tx.id = tx.calculate_hash()
        return tx
