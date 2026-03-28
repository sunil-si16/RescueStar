import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import time
import json
from base_agent import BaseAgent
from p2p_node import P2PNode

app = FastAPI(title="AESRS Visualizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ObserverAgent(BaseAgent):
    def __init__(self):
        super().__init__("Observer")
        self.websockets = []
        
    def handle_event(self, event_type: str, payload: dict, sender_id: str):
        # We don't take action, we just forward everything to the frontend
        msg = {
            "type": event_type,
            "payload": payload,
            "sender_id": sender_id,
            "timestamp": time.time()
        }
        self.notify_frontends(msg)

    def _internal_event_handler(self, msg: dict):
        # Override to also capture system level events like PEER_CONNECTED
        super()._internal_event_handler(msg)
        self.notify_frontends(msg)

    def notify_frontends(self, msg: dict):
        # We use a simple loop (this runs in the background thread from p2p_node)
        # We need to schedule it on the asyncio event loop of FastAPI
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._broadcast_ws(msg), loop)
        except:
            pass
            
    async def _broadcast_ws(self, msg: dict):
        dead_ws = []
        for ws in self.websockets:
            try:
                await ws.send_json(msg)
            except:
                dead_ws.append(ws)
        for ws in dead_ws:
            self.websockets.remove(ws)

observer = ObserverAgent()
observer.start()

# Mount frontend
os.makedirs("frontend", exist_ok=True)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def get_home():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    observer.websockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # The frontend can send us commands too.
            cmd = json.loads(data)
            if cmd.get("action") == "TRIGGER_ACCIDENT":
                x = cmd.get("x", 50)
                y = cmd.get("y", 50)
                print(f"[Visualizer] Triggering accident at {x}, {y}")
                observer.broadcast_event("TRIGGER_ACCIDENT", {"x": x, "y": y})
    except WebSocketDisconnect:
        if websocket in observer.websockets:
            observer.websockets.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("visualizer_node:app", host="0.0.0.0", port=8000, reload=False)
