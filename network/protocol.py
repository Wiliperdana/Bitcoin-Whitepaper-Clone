import json

class Message:
    def __init__(self, command: str, payload: dict):
        self.command = command
        self.payload = payload

    def to_bytes(self) -> bytes:
        """Serializes the message to a single line JSON string mapped to bytes."""
        # Simple JSON-line protocol to avoid TCP stream fragmentation parsing
        d = {"command": self.command, "payload": self.payload}
        return (json.dumps(d, separators=(',', ':')) + '\n').encode('utf-8')

    @classmethod
    def from_bytes(cls, data: bytes):
        """Deserializes bytes back to a Message. Assumes a single complete JSON object string."""
        d = json.loads(data.decode('utf-8').strip())
        return cls(d["command"], d["payload"])

# Constants for command types
CMD_VERSION = "version"
CMD_VERACK = "verack"
CMD_INV = "inv"            # Broadcast knowledge of blocks/txs
CMD_GETDATA = "getdata"    # Request specific blocks/txs
CMD_TX = "tx"
CMD_BLOCK = "block"
CMD_GETHEADERS = "getheaders"
CMD_HEADERS = "headers"
CMD_ALERT = "alert"        # For SPV clients (from whitepaper section 8)
