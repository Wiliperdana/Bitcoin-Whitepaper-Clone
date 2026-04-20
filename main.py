import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        description="Bitcoin Clone Master CLI",
        epilog="Use 'python main.py <command> --help' for details on specific commands."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available sub-systems")
    
    # 1. Simulate Command
    parse_sim = subparsers.add_parser("simulate", help="Run the honest vs attacker network simulation")
    
    # 2. Node Command
    parse_node = subparsers.add_parser("node", help="Start a local P2P full node daemon")
    parse_node.add_argument("--port", type=int, default=8333, help="TCP port to listen on for P2P connections")
    parse_node.add_argument("--connect", type=str, default="", help="IP:PORT of initial peer to bootstrap from")
    parse_node.add_argument("--mine", action="store_true", help="Turn on the Hashcash miner automatically")
    
    # 3. Client Command
    parse_cli = subparsers.add_parser("client", help="Interact with a running node daemon via RPC")
    parse_cli.add_argument("method", choices=["getinfo", "balance", "send", "mempool"], help="The RPC method to call")
    parse_cli.add_argument("--port", type=int, default=8333, help="Target Node P2P port (CLI automatically converts to RPC port)")
    parse_cli.add_argument("--to", type=str, help="Destination address (required for 'send')")
    parse_cli.add_argument("--amount", type=int, help="Amount to send (required for 'send')")
    
    # 4. Math Command (Section 11)
    parse_math = subparsers.add_parser("math", help="Calculate Gambler's Ruin probability (Whitepaper Section 11)")
    parse_math.add_argument("--q", type=float, required=True, help="Attacker hashrate fraction (e.g., 0.3 for 30%)")
    parse_math.add_argument("--z", type=int, required=True, help="Number of confirmations (blocks)")
    
    # 5. Explore Command
    parse_explore = subparsers.add_parser("explore", help="View the blockchain history like a block explorer")
    parse_explore.add_argument("--port", type=int, default=8333, help="Target Node P2P port")
    parse_explore.add_argument("--block", type=int, help="Specify a block height to view its full details")

    # 6. Test Command
    parse_test = subparsers.add_parser("test", help="Run the core Pytest suite")

    args = parser.parse_args()

    # Dispatch to appropriate internal script using subprocess to maintain isolated memory spaces
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        if args.command == "simulate":
            print("[Master] Launching Simulation Module...")
            subprocess.run([sys.executable, "simulation.py"], cwd=base_dir)
            
        elif args.command == "node":
            print(f"[Master] Launching Full Node on port {args.port}...")
            cmd = [sys.executable, "bitcoin_node.py", "--port", str(args.port)]
            if args.connect:
                cmd.extend(["--connect", args.connect])
            if args.mine:
                cmd.append("--mine")
            subprocess.run(cmd, cwd=base_dir)
            
        elif args.command == "client":
            cmd = [sys.executable, "bitcoin_cli.py", args.method, "--port", str(args.port)]
            if args.to:
                cmd.extend(["--to", args.to])
            if args.amount is not None:
                cmd.extend(["--amount", str(args.amount)])
            subprocess.run(cmd, cwd=base_dir)
            
        elif args.command == "math":
            subprocess.run([sys.executable, "probability.py", "--q", str(args.q), "--z", str(args.z)], cwd=base_dir)
            
        elif args.command == "explore":
            import socket, json
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("127.0.0.1", args.port + 1000))
                method = "getblock" if args.block is not None else "getchain_summary"
                params = {"height": args.block} if args.block is not None else {}
                
                req = {"method": method, "params": params}
                sock.sendall((json.dumps(req)+"\n").encode())
                
                f = sock.makefile('r')
                line = f.readline()
                if line:
                    resp = json.loads(line)
                    if resp.get("error"):
                        print(f"Error: {resp['error']}")
                    else:
                        print(f"\n======== BLOCKCHAIN EXPLORER (Port {args.port}) ========\n")
                        res = resp["result"]
                        if method == "getchain_summary":
                            print(f"{'HEIGHT':<8} | {'TXs':<5} | {'TIMESTAMP':<12} | {'BLOCK HASH'}")
                            print("-" * 75)
                            for b in reversed(res):
                                print(f"{b['height']:<8} | {b['tx_count']:<5} | {b['timestamp']:<12} | {b['hash']}")
                            print("\nUse 'python main.py explore --block <height>' to see detailed block/tx info.")
                        else:
                            print(json.dumps(res, indent=2))
                else:
                    print("Empty response from Node.")
            except Exception as e:
                print(f"Connection failed (is the node running?): {e}")
            finally:
                sock.close()
                
        elif args.command == "test":
            print("[Master] Executing Pytest suite...")
            subprocess.run([sys.executable, "-m", "pytest", "tests/"], cwd=base_dir)
            
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print("\n[Master] Master CLI terminated.")

if __name__ == "__main__":
    main()
