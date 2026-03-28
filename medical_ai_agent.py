import time
from base_agent import BaseAgent

class MedicalAIAgent(BaseAgent):
    def __init__(self, node_id: str = None):
        super().__init__("MedicalAI", node_id)
        
    def handle_event(self, event_type: str, payload: dict, sender_id: str):
        if event_type == "SENSOR_DATA":
            drone_id = payload.get("drone_id")
            patient = payload.get("patient", {})
            
            print(f"[{self.node_id}] Received SENSOR_DATA from Drone {drone_id}. Evaluating...")
            
            # Simple AI rules engine for triage
            heart_rate = patient.get("heart_rate", 80)
            blood_loss = patient.get("blood_loss", False)
            responsive = patient.get("responsive", True)
            
            severity = "MINOR"
            if heart_rate < 50 or heart_rate > 100 or blood_loss or not responsive:
                severity = "CRITICAL"
                
            print(f"[{self.node_id}] Evaluation Complete. Severity: {severity}")
            
            eval_data = {
                "drone_id": drone_id,
                "severity": severity,
                "patient_data": patient
            }
            
            self.mine_and_gossip_block({
                "event": "SEVERITY_EVALUATED",
                "ai_node_id": self.node_id,
                "evaluation": eval_data
            })
            
            self.broadcast_event("SEVERITY_EVALUATED", eval_data)

if __name__ == "__main__":
    agent = MedicalAIAgent()
    agent.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
