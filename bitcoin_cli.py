import sys
import json
import socket
import argparse

def send_rpc(port: int, method: str, params: dict = None):
    if params is None:
        params = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("127.0.0.1", port))
        req = {"method": method, "params": params}
        sock.sendall((json.dumps(req)+"\n").encode())
        f = sock.makefile('r')
        line = f.readline()
        if line:
            resp = json.loads(line)
            print(json.dumps(resp, indent=2))
        else:
            print("Empty response from Node.")
    except Exception as e:
        print(f"RPC connection failed (is the node running?): {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bitcoin Clone CLI interface.")
    parser.add_argument('method', choices=['getinfo', 'balance', 'send'], help="RPC method to call")
    parser.add_argument('--port', type=int, default=8333, help="Node P2P port (RPC relies on port+1000)")
    parser.add_argument('--to', type=str, help="Destination address (for send)")
    parser.add_argument('--amount', type=int, help="Amount to send in arbitrary units")
    
    args = parser.parse_args()
    rpc_port = args.port + 1000
    
    params = {}
    if args.method == 'send':
        if not args.to or not args.amount:
            print("Error: The 'send' command requires --to and --amount.")
            sys.exit(1)
        params = {"to": args.to, "amount": args.amount}
        
    send_rpc(rpc_port, args.method, params)
