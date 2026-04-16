# Educational Python Bitcoin Clone

This project is a complete, pedagogical Python implementation of the original Bitcoin protocol as described in the Satoshi Nakamoto whitepaper. It features Proof-of-Work mining, TCP-based Peer-to-Peer networking, ECDSA signatures on transactions, longest-chain branch consensus logic, and an empirical simulation of a 3-honest/1-attacker network. It uses purely standard library tools (and the pure-Python `ecdsa` package).

## Installation

1. Create a virtual environment or install dependencies directly:
   ```bash
   pip install -r requirements.txt
   ```

## Using the CLI

### 1. Run a Full Node

Start the first full node in its own terminal:
```bash
python bitcoin_node.py --port 10001 --mine
```

### 2. Connect another Node
Start a second node that peers with the first:
```bash
python bitcoin_node.py --port 10002 --connect 127.0.0.1:10001 --mine
```

### 3. Interact via CLI

The CLI uses an RPC port offset automatically from the P2P port (`P2P_PORT + 1000`). For the first node (`10001`), use `--port 10001` with the CLI:

**Get Balance**
```bash
python bitcoin_cli.py balance --port 10001
```

**Send Funds**
```bash
python bitcoin_cli.py send --port 10001 --to <destination_address> --amount 50
```

**Get Node Info**
```bash
python bitcoin_cli.py getinfo --port 10001
```

## Gambler's Ruin Calculator (Whitepaper Section 11)

Calculates the risk of an attacker reversing history depending on how many blocks (`z`) have passed and their hashrate fraction (`q`).

```bash
# Example: 30% attacker hashrate, 6 confirmations
python probability.py --q 0.3 --z 6
```

## Running the Security Simulation

The simulation script demonstrates the honest network outpacing an attacker with lesser hashrate (25%).

```bash
python simulation.py
```

## Testing

A comprehensive automated test suite validates the internal hashing logic, double-spend prevention, and chain reorganization dynamics.

```bash
python -m pytest tests/
```
