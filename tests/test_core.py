import pytest
import time
from core.crypto import generate_key_pair, hash160, sign_data, verify_signature
from core.transaction import Transaction, TxIn, TxOut, create_coinbase_transaction
from core.block import BlockHeader, Block, compute_merkle_root, compute_merkle_proof, verify_merkle_proof
from core.blockchain import Blockchain, INITIAL_TARGET

def test_crypto_signing():
    sk, vk = generate_key_pair()
    data = b"hello bitcoin"
    signature = sign_data(sk, data)
    assert verify_signature(vk.to_string(), signature, data)
    
    # Check invalid data fails
    assert not verify_signature(vk.to_string(), signature, b"hello eth")
    
    # Check invalid signature fails
    assert not verify_signature(vk.to_string(), b"1"*len(signature), data)

def test_merkle_tree():
    txids = ["a"*64, "b"*64, "c"*64]
    root = compute_merkle_root(txids)
    
    proof = compute_merkle_proof(txids, 1) # proof for "b"*64
    assert verify_merkle_proof("b"*64, proof, root)
    
    # Check invalid proof fails
    bad_proof = compute_merkle_proof(txids, 0)
    assert not verify_merkle_proof("b"*64, bad_proof, root)

def test_pow():
    h = BlockHeader(1, "0"*64, "1"*64, int(time.time()), INITIAL_TARGET, 0)
    b = Block(h, [])
    # Find valid nonce
    while not b.check_pow():
        b.header.nonce += 1
    assert b.check_pow()

def test_transactions_and_double_spend():
    chain = Blockchain()
    
    # Genesis
    cb1 = create_coinbase_transaction("alice_addr", 0)
    bb1 = Block(BlockHeader(1, "0"*64, cb1.id, 0, INITIAL_TARGET, 0), [cb1])
    while not bb1.check_pow(): bb1.header.nonce += 1
    chain.add_block(bb1)
    
    # Create valid tx spending coinbase
    sk, vk = generate_key_pair()
    alice_addr = hash160(vk.to_string()).hex()
    cb1.outputs[0].address = alice_addr # Mock it so alice owns it
    # We must rebuild chain manually since we mocked
    chain.utxo_set.clear()
    chain.rebuild_utxo(chain.tip)
    
    txin = TxIn(cb1.id, 0, pub_key=vk.to_string().hex())
    txout = TxOut(amount=cb1.outputs[0].amount - 10, address="bob")
    tx = Transaction([txin], [txout])
    
    sig = sign_data(sk, tx.get_sign_data())
    tx.inputs[0].signature = sig.hex()
    tx.id = tx.calculate_hash()
    
    # Test valid 
    def get_utxo(t, i): return chain.get_utxo(t, i)
    assert tx.verify(get_utxo)
    
    # Create block with tx
    cb2 = create_coinbase_transaction("alice_addr", 1)
    bb2 = Block(BlockHeader(1, bb1.header.hash(), "mr", 0, INITIAL_TARGET, 0), [cb2, tx])
    bb2.header.merkle_root = bb2.calculate_merkle_root()
    while not bb2.check_pow(): bb2.header.nonce += 1
    assert chain.add_block(bb2)
    
    # Double spend test: Try to spend cb1.id again in a new block extending bb2
    txin2 = TxIn(cb1.id, 0, pub_key=vk.to_string().hex())
    txout2 = TxOut(amount=1, address="eve")
    bad_tx = Transaction([txin2], [txout2])
    
    cb3 = create_coinbase_transaction("eve_addr", 2)
    bb3 = Block(BlockHeader(1, bb2.header.hash(), "mr", 0, INITIAL_TARGET, 0), [cb3, bad_tx])
    bb3.header.merkle_root = bb3.calculate_merkle_root()
    while not bb3.check_pow(): bb3.header.nonce += 1
    
    # Chain drops it because validate_transactions returns false
    assert not chain.add_block(bb3)

def test_chain_reorg():
    chain = Blockchain()
    
    cb = create_coinbase_transaction("alice", 0)
    b0 = Block(BlockHeader(1, "0"*64, cb.id, 0, INITIAL_TARGET, 0), [cb])
    while not b0.check_pow(): b0.header.nonce += 1
    chain.add_block(b0)
    
    # Fork A
    cba = create_coinbase_transaction("alice", 1)
    ba = Block(BlockHeader(1, b0.header.hash(), cba.id, 0, INITIAL_TARGET, 0), [cba])
    while not ba.check_pow(): ba.header.nonce += 1
    assert chain.add_block(ba)
    assert chain.tip.block == ba
    
    # Fork B (Orphan initially, then overtakes)
    cbb1 = create_coinbase_transaction("bob", 1)
    bb1 = Block(BlockHeader(1, b0.header.hash(), cbb1.id, 0, INITIAL_TARGET, 0), [cbb1])
    while not bb1.check_pow(): bb1.header.nonce += 1
    assert chain.add_block(bb1)
    # Tip is still ba since work is equal (it keeps first received)
    assert chain.tip.block == ba 
    
    cbb2 = create_coinbase_transaction("bob", 2)
    bb2 = Block(BlockHeader(1, bb1.header.hash(), cbb2.id, 0, INITIAL_TARGET, 0), [cbb2])
    while not bb2.check_pow(): bb2.header.nonce += 1
    assert chain.add_block(bb2)
    
    # Now branch B has more work! Reorg expects tip to switch to bb2
    assert chain.tip.block == bb2
