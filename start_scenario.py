import subprocess
import time
import sys

scripts = [
    ("visualizer_node.py", "Visualizer"),
    ("drone_agent.py", "Drone 1"),
    ("drone_agent.py", "Drone 2"),
    ("drone_agent.py", "Drone 3"),
    ("medical_ai_agent.py", "Medical AI"),
    ("ambulance_agent.py", "Ambulance")
]

processes = []

print("Initializing AESRS P2P Swarm...")

for script, name in scripts:
    print(f"Starting {name}...")
    p = subprocess.Popen([sys.executable, script])
    processes.append(p)
    time.sleep(1) # Stagger starts so visualizer is up first

print("\n" + "="*50)
print("🚀 SWARM DEPLOYED SUCCESSFULLY!")
print("==================================================")
print("1. Open your browser to: http://127.0.0.1:8000")
print("2. Watch the nodes auto-discover via P2P UDP broadcasts.")
print("3. Click 'Trigger Accident Simulation' to watch them coordinate.")
print("==================================================\n")
print("Press Ctrl+C to shutdown the entire swarm.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down swarm nodes...")
    for p in processes:
        p.terminate()
        p.wait()
    print("Swarm offline.")
