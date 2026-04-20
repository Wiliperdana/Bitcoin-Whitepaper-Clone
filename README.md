# Educational Python Bitcoin Clone

This project is a complete, pedagogical Python implementation of the original Bitcoin protocol as described in the Satoshi Nakamoto whitepaper. It features Proof-of-Work mining, TCP-based Peer-to-Peer networking, ECDSA signatures on transactions, longest-chain branch consensus logic, and an empirical simulation of a 3-honest/1-attacker network. It uses purely standard library tools (and the pure-Python `ecdsa` package).

## Installation

Create a virtual environment or install dependencies directly:
```powershell
pip install -r requirements.txt
```

---

## Step-by-Step Guide: Forming a P2P Network

You manage everything in this directory through a unified Master CLI tool called `main.py`.

### Step 1: Start the Genesis Node (Terminal 1)
Open a terminal and establish the first node in your network on port `10001`. We will use `--mine` to tell it to start hashing strictly according to the initial difficulty.

```powershell
python main.py node --port 10001 --mine
```
*Note: This node does not have a `--connect` flag because it is acting as the bootstrap node. If you ever stop and restart this node, it will forget its history (as all data is in-memory). To recover its history, it must pull it back from a living peer!*

### Step 2: Connect a Second Node (Terminal 2)
Open a new terminal and start a second node on port `10002`. This time, we use the `--connect` flag to point it at the first node so they sync together.

```powershell
python main.py node --port 10002 --connect 127.0.0.1:10001 --mine
```
*Behind the scenes: The nodes form a TCP P2P connection. Node 10002 verifies Node 10001's chain, instantly pulls any missing blocks, and they both begin competitively mining atop the exact same unified blockchain!*

### Step 3: Browse the Blockchain Explorer (Terminal 3)
At any point, open a third terminal and dynamically inspect the blockchain history currently known to either node:

**Summarize the entire chain (newest blocks first):**
```powershell
python main.py explore --port 10001
```

**Inspect the exact cryptographic details of a specific block:**
```powershell
python main.py explore --port 10001 --block 1
```

### Step 4: Interact with RPC Commands (Terminal 3)
You can directly ask your node to execute transactions or check memory pools:

**Check Node Status:**
```powershell
python main.py client getinfo --port 10001
```

**Check Mining Balance:**
```powershell
python main.py client balance --port 10001
```

**Send test funds to another address:**
```powershell
python main.py client send --port 10001 --to <destination_address> --amount 50
```

---

## 5. Network Security Simulation
Instead of running nodes manually, you can run an automated script that securely spawns 3 Honest Nodes and an Attacker Node in parallel. It beautifully demonstrates Nakamoto Consensus, where the honest network routinely overtakes and orphans the attacker's fake chain!

```powershell
python main.py simulate
```

## 6. Gambler's Ruin Calculator (Whitepaper Section 11)
Calculates the risk of an attacker reversing history depending on how many blocks (`z`) have passed and their hashrate fraction (`q`).

```powershell
# Example: 30% attacker hashrate, 6 confirmations
python main.py math --q 0.3 --z 6
```

## 7. Testing
A comprehensive automated test suite validates the internal hashing logic, double-spend prevention, and chain reorganization dynamics.

```powershell
python main.py test
```
