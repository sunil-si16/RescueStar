import time
from base_agent import BaseAgent

class AmbulanceAgent(BaseAgent):
    def __init__(self, node_id: str = None):
        super().__init__("Ambulance", node_id)
        self.status = "AVAILABLE"
        
    def handle_event(self, event_type: str, payload: dict, sender_id: str):
        if event_type == "SEVERITY_EVALUATED":
            severity = payload.get("severity")
            drone_id = payload.get("drone_id")
            
            if severity == "CRITICAL" and self.status == "AVAILABLE":
                print(f"[{self.node_id}] EMERGENCY ALERT! Critical severity detected from Drone {drone_id}.")
                print(f"[{self.node_id}] Dispatching ambulance to location...")
                self.status = "DISPATCHED"
                
                dispatch_data = {
                    "ambulance_id": self.node_id,
                    "target_drone": drone_id
                }
                
                self.mine_and_gossip_block({
                    "event": "AMBULANCE_DISPATCHED",
                    "dispatch_data": dispatch_data
                })
                
                self.broadcast_event("AMBULANCE_DISPATCHED", dispatch_data)
                
                # Simulate dispatch time
                time.sleep(5)
                self.status = "AVAILABLE"
                print(f"[{self.node_id}] Ambulance returned. Status: AVAILABLE.")

if __name__ == "__main__":
    agent = AmbulanceAgent()
    agent.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
