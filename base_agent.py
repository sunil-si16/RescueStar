import random
import time
import threading
from typing import Dict, Any
from p2p_node import P2PNode
from blockchain_ledger import BlockchainLedger

class BaseAgent(P2PNode):
    def __init__(self, node_type: str, node_id: str = None):
        super().__init__(node_type, node_id)
        self.blockchain = BlockchainLedger()
        self.peer_last_seen = {} # {peer_id: timestamp}
        self.on_event(self._internal_event_handler)
        
        # Start Heartbeat
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
    def _heartbeat_loop(self):
        time.sleep(2) # delay start slightly
        while self.running:
            try:
                self.broadcast_event("HEARTBEAT", {"node_id": self.node_id})
            except:
                pass
            time.sleep(3)
        
    def _internal_event_handler(self, msg: Dict[str, Any]):
        event_type = msg.get("type")
        payload = msg.get("payload", {})
        sender_id = msg.get("sender_id")
        
        if event_type == "HEARTBEAT":
            self.peer_last_seen[sender_id] = time.time()
            return # Skip passing to subclass to avoid clutter
            
        if event_type == "NEW_BLOCK":
            block_data = payload.get("block_data")
            if block_data:
                added = self.blockchain.add_external_block(block_data)
                if added:
                    print(f"[{self.node_id}] Validated block #{block_data['index']} from peer network.")
            return

        self.handle_event(event_type, payload, sender_id)
        
    def mine_and_gossip_block(self, event_data: dict):
        """Mines a security record into the ledger and gossips it to the swarm."""
        print(f"[{self.node_id}] Mining new block for event: {event_data.get('event')}...")
        new_block = self.blockchain.mine_new_block(event_data)
        block_dict = {
            "index": new_block.index,
            "previous_hash": new_block.previous_hash,
            "timestamp": new_block.timestamp,
            "data": new_block.data,
            "hash": new_block.hash,
            "nonce": new_block.nonce
        }
        self.broadcast_event("NEW_BLOCK", {"block_data": block_dict})
        
    def get_dead_peers(self, timeout=10) -> list:
        now = time.time()
        dead = []
        for pid, last_seen in self.peer_last_seen.items():
            if now - last_seen > timeout:
                dead.append(pid)
        return dead

    def handle_event(self, event_type: str, payload: dict, sender_id: str):
        pass
