import argparse
import math

def attacker_success_probability(q: float, z: int) -> float:
    """
    Computes the probability of an attacker catching up from z blocks behind,
    given the attacker controls q fraction of the network hashrate.
    
    This is a direct translation of the C code block from Section 11 of the 
    Satoshi Nakamoto Bitcoin Whitepaper.
    """
    p = 1.0 - q
    if q >= p:
        return 1.0
        
    lam = z * (q / p)
    
    sum_prob = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam)
        for i in range(1, k + 1):
            poisson *= lam / i
        sum_prob -= poisson * (1 - math.pow(q / p, z - k))
        
    return sum_prob

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Calculate Nakamoto Gambler's Ruin attacker probability.")
    parser.add_argument('--q', type=float, required=True, help="Attacker hashrate fraction (e.g. 0.3 for 30%)")
    parser.add_argument('--z', type=int, required=True, help="Number of confirmations (blocks)")
    
    args = parser.add_argument() if hasattr(parser, "parse_args") else parser.parse_args()
    
    prob = attacker_success_probability(args.q, args.z)
    print(f"Given Attacker Hashrate (q) = {args.q*100}%")
    print(f"Given Confirmations (z)     = {args.z}")
    print(f"Probability of Catchup      = {prob:.10f}")
    if prob < 0.001:
        print("Verdict: Extremely safe (less than 0.1% chance of double-spend).")
    else:
        print("Verdict: Vulnerable to double-spending.")
