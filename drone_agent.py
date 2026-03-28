import math
import random
import threading
import time
from base_agent import BaseAgent

class DroneAgent(BaseAgent):
    def __init__(self, node_id: str = None):
        super().__init__("Drone", node_id)
        # Random initial position on a 100x100 grid
        self.x = random.uniform(0, 100)
        self.y = random.uniform(0, 100)
        
        # Advanced Logic fields
        self.battery = random.randint(50, 100)
        self.load = random.uniform(0, 5) # Current workload weight
        
        self.status = "IDLE" # IDLE, RESPONDING
        self.current_accident = None
        self.bids_to_accident = {} # {drone_id: score}
        self.decision_timer = None
        self.active_responder = None
        
        # Start status broadcasting
        threading.Thread(target=self._broadcast_status_loop, daemon=True).start()

    def _broadcast_status_loop(self):
        while self.running:
            try:
                # Slowly drain battery
                if self.battery > 0:
                    self.battery -= 0.1 if self.status == "IDLE" else 0.5
                    
                self.broadcast_event("DRONE_STATUS", {
                    "id": self.node_id,
                    "x": self.x,
                    "y": self.y,
                    "status": self.status,
                    "battery": round(self.battery, 1),
                    "load": round(self.load, 1)
                })
                
                # Check for dead responders (self-healing swarm)
                if self.active_responder and self.active_responder != self.node_id:
                    dead_peers = self.get_dead_peers(timeout=10)
                    if self.active_responder in dead_peers and self.current_accident:
                        print(f"[{self.node_id}] WARNING: Active responder {self.active_responder} is dead! Re-negotiating.")
                        self.active_responder = None
                        self._trigger_bidding(self.current_accident["x"], self.current_accident["y"])
                        
            except:
                pass
            time.sleep(2)

    def handle_event(self, event_type: str, payload: dict, sender_id: str):
        if event_type == "TRIGGER_ACCIDENT":
            acc_x = payload.get("x")
            acc_y = payload.get("y")
            self._trigger_bidding(acc_x, acc_y)
            
        elif event_type == "DRONE_RESPOND_BID":
            # Another drone reported its score
            self.bids_to_accident[payload.get("drone_id")] = payload.get("score")
            
        elif event_type == "DRONE_RESPONDING":
            # Another drone won the bid
            self.active_responder = sender_id
            if self.node_id != sender_id:
                print(f"[{self.node_id}] Drone {sender_id} won bid. I'll standby.")
                self.status = "IDLE"
                if self.decision_timer:
                    self.decision_timer.cancel()

    def _trigger_bidding(self, acc_x, acc_y):
        self.current_accident = {"x": acc_x, "y": acc_y}
        
        dist = math.hypot(self.x - acc_x, self.y - acc_y)
        # Score-based allocation: Lower is better
        score = (dist * 0.5) - (self.battery * 0.3) + self.load
        
        print(f"[{self.node_id}] Accident at ({acc_x:.1f}, {acc_y:.1f}). Dist:{dist:.1f}, Bat:{self.battery:.1f}% -> Score: {score:.1f}")
        
        self.bids_to_accident[self.node_id] = score
        self.broadcast_event("DRONE_RESPOND_BID", {
            "drone_id": self.node_id,
            "score": score
        })
        
        if self.decision_timer:
            self.decision_timer.cancel()
        self.decision_timer = threading.Timer(2.0, self._negotiate_responder)
        self.decision_timer.start()

    def _negotiate_responder(self):
        # Find the drone with the minimum score
        if not self.bids_to_accident: return
        min_drone = min(self.bids_to_accident, key=self.bids_to_accident.get)
        
        if min_drone == self.node_id:
            # I am the best fit!
            self.status = "RESPONDING"
            self.active_responder = self.node_id
            print(f"[{self.node_id}] I am RESPONDING to the accident (Lowest Score).")
            self.broadcast_event("DRONE_RESPONDING", {"drone_id": self.node_id})
            
            # Mine it into the ledger
            self.mine_and_gossip_block({
                "event": "DRONE_RESPONDING",
                "drone_id": self.node_id,
                "score": self.bids_to_accident[self.node_id],
                "location": self.current_accident
            })
            
            # Simulate arriving and sending patient data
            time.sleep(3)
            self._send_sensor_data()
        
        self.bids_to_accident.clear()

    def _send_sensor_data(self):
        if self.status != "RESPONDING": return
        
        heart_rate = random.choice([45, 80, 120])
        blood_loss = random.choice([True, False])
        
        print(f"[{self.node_id}] Transmitting sensor data.")
        patient_data = {
            "heart_rate": heart_rate,
            "blood_loss": blood_loss,
            "responsive": not blood_loss
        }
        
        self.mine_and_gossip_block({
            "event": "SENSOR_DATA_TRANSMITTED",
            "drone_id": self.node_id,
            "patient_data": patient_data
        })
        
        self.broadcast_event("SENSOR_DATA", {
            "drone_id": self.node_id,
            "patient": patient_data
        })

if __name__ == "__main__":
    agent = DroneAgent()
    agent.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
