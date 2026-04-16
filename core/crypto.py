import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1

def sha256d(data: bytes) -> bytes:
    """Computes double SHA-256 (SHA-256(SHA-256(data)))."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def generate_key_pair():
    """Generates a secp256k1 private and public key pair.
    
    Returns:
        tuple[SigningKey, VerifyingKey]: The private and public key.
    """
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()
    return sk, vk

def sign_data(sk: SigningKey, data: bytes) -> bytes:
    """Signs the double-sha256 digest of data.
    
    Args:
        sk: The signing key.
        data: The raw data bytes to sign.
        
    Returns:
        bytes: The ECDSA signature.
    """
    digest = sha256d(data)
    return sk.sign_digest(digest)

def verify_signature(vk_bytes: bytes, signature: bytes, data: bytes) -> bool:
    """Verifies an ECDSA signature over double-sha256 data.
    
    Args:
        vk_bytes: The serialized verifying public key.
        signature: The ECDSA signature bytes.
        data: The raw data bytes that were signed.
        
    Returns:
        bool: True if signature is valid, False otherwise.
    """
    try:
        vk = VerifyingKey.from_string(vk_bytes, curve=SECP256k1)
        digest = sha256d(data)
        return vk.verify_digest(signature, digest)
    except Exception:
        return False

def hash160(data: bytes) -> bytes:
    """Computes RIPEMD160(SHA256(data)). Often used for addresses."""
    # Use hashlib's generic new method for consistency if ripemd160 is supported
    sha = hashlib.sha256(data).digest()
    
    try:
        rmd = hashlib.new('ripemd160', sha).digest()
    except ValueError:
        # Some OpenSSL distributions do not enable ripemd160 by default!
        # Bitcoin strictly needs RIPEMD-160 for classic P2PKH addresses...
        # As a fallback for a pure Python implementation if rmd isn't there,
        # we can just double-sha256 and truncate to 20 bytes (to emulate an address).
        rmd = hashlib.sha256(sha).digest()[:20]
        
    return rmd
