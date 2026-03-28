import socket
import threading
import json
import time
import uuid
from typing import Callable, Dict, Any

# Shared port for UDP discovery broadcasts
DISCOVERY_PORT = 50000

class P2PNode:
    """
    A foundational Peer-to-Peer node that auto-discovers peers via UDP broadcasts
    and establishes direct TCP connections to form a decentralized mesh network.
    """
    def __init__(self, node_type: str, node_id: str = None):
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.node_type = node_type
        
        # Determine local IP (a basic hack to get the actual LAN IP)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            self.ip = s.getsockname()[0]
        except Exception:
            self.ip = '127.0.0.1'
        finally:
            s.close()
            
        self.peers = {} # {node_id: {"ip": ip, "port": port, "conn": socket}}
        self.seen_messages = set()
        
        # Setup TCP Server for incoming peer connections
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.bind(('0.0.0.0', 0)) # bind to any available port
        self.tcp_server.listen(5)
        self.tcp_port = self.tcp_server.getsockname()[1]
        
        # Event callbacks
        self.callbacks = []
        
        self.running = False
        
    def start(self):
        self.running = True
        
        # Start TCP listener
        threading.Thread(target=self._accept_tcp_connections, daemon=True).start()
        
        # Start UDP discovery listener
        threading.Thread(target=self._listen_for_discovery, daemon=True).start()
        
        # Start UDP broadcaster
        threading.Thread(target=self._broadcast_presence, daemon=True).start()
        
        print(f"[{self.node_type}:{self.node_id}] Node started. IP: {self.ip}, TCP Port: {self.tcp_port}")

    def stop(self):
        self.running = False
        self.tcp_server.close()
        for peer in self.peers.values():
            if peer.get('conn'):
                try: peer['conn'].close()
                except: pass

    def on_event(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback to handle incoming P2P events."""
        self.callbacks.append(callback)

    def broadcast_event(self, event_type: str, payload: dict):
        """Broadcasts an event to all connected peers in the mesh."""
        msg_id = str(uuid.uuid4())
        msg = {
            "msg_id": msg_id,
            "sender_id": self.node_id,
            "sender_type": self.node_type,
            "type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }
        self.seen_messages.add(msg_id)
        self._send_to_all_peers(msg)
        
    def _send_to_all_peers(self, msg_dict: dict):
        msg_bytes = (json.dumps(msg_dict) + "\n").encode('utf-8')
        dead_peers = []
        for peer_id, peer_info in self.peers.items():
            conn = peer_info.get("conn")
            if conn:
                try:
                    conn.sendall(msg_bytes)
                except Exception as e:
                    print(f"[{self.node_id}] Failed to send to {peer_id}: {e}")
                    dead_peers.append(peer_id)
                    
        for dp in dead_peers:
            self._disconnect_peer(dp)

    def _broadcast_presence(self):
        """Periodically broadcast presence via UDP."""
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        presence_msg = json.dumps({
            "node_id": self.node_id,
            "node_type": self.node_type,
            "ip": self.ip,
            "tcp_port": self.tcp_port
        }).encode('utf-8')
        
        while self.running:
            try:
                # 255.255.255.255 is the standard broadcast address
                udp_socket.sendto(presence_msg, ('<broadcast>', DISCOVERY_PORT))
            except Exception as e:
                # Fallback for systems that don't like <broadcast>
                try:
                    udp_socket.sendto(presence_msg, ('255.255.255.255', DISCOVERY_PORT))
                except:
                    pass
            time.sleep(2)

    def _listen_for_discovery(self):
        """Listen for UDP presence broadcasts from other nodes."""
        udp_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # On Windows, using SO_BROADCAST and binding to empty string or broadcast addr is sometimes tricky.
        # usually binding to 0.0.0.0 and DISCOVERY_PORT works for receiving broadcasts
        try:
            udp_listener.bind(('', DISCOVERY_PORT))
        except Exception as e:
            print(f"[{self.node_id}] Failed to bind UDP discovery port: {e}. Node discovery may be restricted.")
            return

        while self.running:
            try:
                data, addr = udp_listener.recvfrom(1024)
                info = json.loads(data.decode('utf-8'))
                peer_id = info.get("node_id")
                
                # If we discovered ourselves, ignore
                if peer_id == self.node_id:
                    continue
                    
                # If we don't know this peer yet, connect to them
                if peer_id not in self.peers:
                    peer_ip = info.get("ip")
                    peer_port = info.get("tcp_port")
                    # Special local dev handling: if IP is same as us but port differs, it's local
                    if peer_ip == self.ip and peer_port == self.tcp_port:
                        continue
                    
                    self._connect_to_peer(peer_id, peer_ip, peer_port, info.get("node_type"))
                    
            except Exception as e:
                pass

    def _connect_to_peer(self, peer_id, ip, port, node_type):
        """Initiate a TCP connection to a newly discovered peer."""
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((ip, port))
            
            # Send an initial greeting to tell them who we are
            greeting = json.dumps({
                "type": "_greeting",
                "node_id": self.node_id,
                "node_type": self.node_type
            }) + "\n"
            conn.sendall(greeting.encode('utf-8'))
            
            self.peers[peer_id] = {
                "ip": ip,
                "port": port,
                "type": node_type,
                "conn": conn
            }
            print(f"[{self.node_id}] Discovered and connected to {node_type} ({peer_id}) at {ip}:{port}")
            
            # Start listening to this peer
            threading.Thread(target=self._handle_peer_connection, args=(conn, peer_id), daemon=True).start()
            
            # Notify app of new peer
            self._notify_callbacks({
                "type": "PEER_CONNECTED",
                "peer_id": peer_id,
                "peer_type": node_type
            })
            
        except Exception as e:
            print(f"[{self.node_id}] Failed to connect to peer {peer_id}: {e}")

    def _accept_tcp_connections(self):
        """Accept incoming TCP connections from other peers."""
        while self.running:
            try:
                conn, addr = self.tcp_server.accept()
                # Start a thread to read from this connection
                threading.Thread(target=self._handle_incoming_connection, args=(conn, addr), daemon=True).start()
            except:
                pass

    def _handle_incoming_connection(self, conn, addr):
        """Read the greeting to identify the peer, then switch to normal handling."""
        try:
            conn.settimeout(5.0)
            # Read line by line. We expect a greeting first.
            f = conn.makefile('r', encoding='utf-8')
            greeting_line = f.readline()
            if not greeting_line:
                conn.close()
                return
                
            greeting = json.loads(greeting_line)
            if greeting.get("type") == "_greeting":
                peer_id = greeting.get("node_id")
                peer_type = greeting.get("node_type")
                
                # Check if we already have them (cross-connection). If so, keep the existing one or handle gracefully.
                # For simplicity, we just add it and close the old one if it existed.
                if peer_id not in self.peers:
                    print(f"[{self.node_id}] Accepted connection from {peer_type} ({peer_id}) at {addr}")
                    self.peers[peer_id] = {
                        "ip": addr[0],
                        "port": addr[1],
                        "type": peer_type,
                        "conn": conn
                    }
                    self._notify_callbacks({
                        "type": "PEER_CONNECTED",
                        "peer_id": peer_id,
                        "peer_type": peer_type
                    })
                    
                conn.settimeout(None) # Remove timeout for normal operation
                self._handle_peer_connection(conn, peer_id, f)
            else:
                conn.close()
        except Exception as e:
            conn.close()

    def _handle_peer_connection(self, conn, peer_id, file_obj=None):
        """Read loop for an established TCP peer connection."""
        if not file_obj:
            file_obj = conn.makefile('r', encoding='utf-8')
            
        while self.running:
            try:
                line = file_obj.readline()
                if not line:
                    break # Connection closed
                    
                msg = json.loads(line)
                msg_id = msg.get("msg_id")
                
                # Gossip Protocol: Only process and forward if we haven't seen this message
                if msg_id and msg_id not in self.seen_messages:
                    self.seen_messages.add(msg_id)
                    
                    # Process locally
                    self._notify_callbacks(msg)
                    
                    # Relay to other peers (except sender)
                    self._relay_message(line, peer_id)
                    
            except Exception as e:
                break
                
        self._disconnect_peer(peer_id)

    def _relay_message(self, line: str, exclude_peer_id: str):
        msg_bytes = line.encode('utf-8')
        dead_peers = []
        for pid, peer_info in self.peers.items():
            if pid != exclude_peer_id:
                conn = peer_info.get("conn")
                if conn:
                    try:
                        conn.sendall(msg_bytes)
                    except:
                        dead_peers.append(pid)
        for dp in dead_peers:
            self._disconnect_peer(dp)

    def _disconnect_peer(self, peer_id):
        if peer_id in self.peers:
            peer_info = self.peers.pop(peer_id)
            conn = peer_info.get("conn")
            if conn:
                try: conn.close()
                except: pass
            print(f"[{self.node_id}] Peer {peer_id} disconnected.")
            self._notify_callbacks({
                "type": "PEER_DISCONNECTED",
                "peer_id": peer_id
            })

    def _notify_callbacks(self, msg: dict):
        for cb in self.callbacks:
            try:
                cb(msg)
            except Exception as e:
                print(f"Callback error: {e}")

if __name__ == "__main__":
    # Simple test for stateful handshake
    node = P2PNode("TestNode")
    node.on_event(lambda e: print(f"Event: {e['type']}"))
    node.start()
    
    try:
        while True:
            time.sleep(5)
            node.broadcast_event("PING", {"status": "alive"})
    except KeyboardInterrupt:
        node.stop()
