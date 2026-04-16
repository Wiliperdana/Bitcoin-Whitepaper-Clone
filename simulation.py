import time
import subprocess
import os
import threading

def filter_output(proc, prefix):
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if "Mined Block" in line or "New tip" in line or "Accepted branch" in line or "Local Miner" in line:
            print(f"[{prefix}] {line}")

def run_simulation():
    print("=========================================================")
    print("   BITCOIN CLONE SIMULATION: HONEST MAJORITY VS ATTACKER ")
    print("=========================================================")
    print("Spawning 3 Honest Nodes (Ports 10001, 10002, 10003)")
    
    n1 = subprocess.Popen(["python", "bitcoin_node.py", "--port", "10001", "--mine"], 
                          stdout=subprocess.PIPE, text=True)
    time.sleep(1) 
    # Let first node generate genesis block so others can sync easily
    
    n2 = subprocess.Popen(["python", "bitcoin_node.py", "--port", "10002", "--connect", "127.0.0.1:10001", "--mine"],
                          stdout=subprocess.PIPE, text=True)
    n3 = subprocess.Popen(["python", "bitcoin_node.py", "--port", "10003", "--connect", "127.0.0.1:10002", "--mine"],
                          stdout=subprocess.PIPE, text=True)
                          
    print("Spawning 1 Attacker Node (Port 10004)")
    print("Attacker has ~25% of absolute network hashrate (1 process vs 3 processes)")
    a1 = subprocess.Popen(["python", "bitcoin_node.py", "--port", "10004", "--connect", "127.0.0.1:10001", "--mine"], 
                          stdout=subprocess.PIPE, text=True)
                          
    threads = [
        threading.Thread(target=filter_output, args=(n1, "HONEST-1"), daemon=True),
        threading.Thread(target=filter_output, args=(n2, "HONEST-2"), daemon=True),
        threading.Thread(target=filter_output, args=(n3, "HONEST-3"), daemon=True),
        threading.Thread(target=filter_output, args=(a1, "ATTACKER"), daemon=True)
    ]
    
    for t in threads:
        t.start()
        
    print("Simulation running. Watch the logs to see the Honest network significantly outpace the Attacker.")
    print("Press Ctrl+C to stop simulation.")
    
    try:
        while True:
             time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping nodes...")
        n1.terminate()
        n2.terminate()
        n3.terminate()
        a1.terminate()
        print("Simulation ended.")

if __name__ == '__main__':
    run_simulation()
