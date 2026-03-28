import hashlib
import json
import time

class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce=0):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data # Dict containing event details
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

class BlockchainLedger:
    def __init__(self, difficulty=2):
        self.chain = [self.create_genesis_block()]
        self.difficulty = difficulty

    def create_genesis_block(self):
        return Block(0, "0", time.time(), {"event": "GENESIS_BLOCK", "message": "AESRS Swarm Initialized"})

    def get_latest_block(self):
        return self.chain[-1]

    def mine_new_block(self, data):
        """Simulates proof of work for security mapping to IoT capabilities."""
        new_block = Block(
            index=self.get_latest_block().index + 1,
            previous_hash=self.get_latest_block().hash,
            timestamp=time.time(),
            data=data
        )
        self.proof_of_work(new_block)
        self.chain.append(new_block)
        return new_block

    def proof_of_work(self, block):
        target = "0" * self.difficulty
        while block.hash[:self.difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()

    def is_valid_block(self, block, previous_block):
        if previous_block.index + 1 != block.index:
            return False
        if previous_block.hash != block.previous_hash:
            return False
        if block.calculate_hash() != block.hash:
            return False
        return True
        
    def add_external_block(self, block_data: dict) -> bool:
        """Add a block received from the P2P network if valid."""
        prev = self.get_latest_block()
        b = Block(
            index=block_data['index'],
            previous_hash=block_data['previous_hash'],
            timestamp=block_data['timestamp'],
            data=block_data['data'],
            nonce=block_data['nonce']
        )
        b.hash = block_data['hash']
        
        # Is it the exact next block?
        if b.index == prev.index + 1:
            if self.is_valid_block(b, prev):
                self.chain.append(b)
                return True
        return False
        
    def to_dict(self):
        return [
            {
                "index": b.index,
                "previous_hash": b.previous_hash,
                "timestamp": b.timestamp,
                "data": b.data,
                "hash": b.hash,
                "nonce": b.nonce
            } for b in self.chain
        ]
