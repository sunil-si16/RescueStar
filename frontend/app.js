const ws = new WebSocket(`ws://${window.location.host}/ws`);
const consoleEl = document.getElementById('console');
const nodeListEl = document.getElementById('node-list');
const mapEl = document.getElementById('map');
const triggerBtn = document.getElementById('trigger-btn');

let nodes = {};

ws.onopen = () => {
    logMsg('Connected to AESRS Visualizer Node.', 'system');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleP2PEvent(data);
};

triggerBtn.addEventListener('click', () => {
    // Generate random accident coordinates
    const x = Math.floor(Math.random() * 80) + 10;
    const y = Math.floor(Math.random() * 80) + 10;
    
    ws.send(JSON.stringify({
        action: 'TRIGGER_ACCIDENT',
        x: x,
        y: y
    }));
    
    triggerBtn.disabled = true;
    setTimeout(() => { triggerBtn.disabled = false; }, 5000);
});

function handleP2PEvent(msg) {
    const type = msg.type;
    const payload = msg.payload || {};
    const sender = msg.sender_id;
    
    // Log to console
    if (type !== 'DRONE_STATUS' && type !== '_greeting' && type !== 'HEARTBEAT' && type !== 'NEW_BLOCK') {
        logMsg(`[${sender}] ${type}: ${JSON.stringify(payload)}`, `event-${type}`);
    }
    
    // Handle Node Discovery
    if (type === 'PEER_CONNECTED') {
        const peerId = payload.peer_id || msg.peer_id; 
        const pId = peerId || msg.payload?.peer_id;
        const pType = payload.peer_type || msg.payload?.peer_type || msg.peer_type;
        if(pId && pType) addNodeToList(pId, pType);
    }
    
    if (type === 'DRONE_STATUS') {
        updateDroneOnMap(payload.id, payload.x, payload.y, payload.status);
        addNodeToList(payload.id, 'Drone', payload.battery, payload.load);
    }
    
    if (type === 'TRIGGER_ACCIDENT') {
        showAccidentOnMap(payload.x, payload.y);
    }
    
    if (type === 'AMBULANCE_DISPATCHED') {
        alert(`🚑 AMBULANCE DISPATCHED to Target!`);
    }

    if (type === 'NEW_BLOCK') {
        addBlockToLedger(payload.block_data);
    }
}

function logMsg(text, className) {
    const el = document.createElement('div');
    el.className = `log-entry ${className}`;
    el.textContent = `> ${text}`;
    consoleEl.appendChild(el);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

function addNodeToList(id, type, battery=null, load=null) {
    if (!nodes[id]) {
        nodes[id] = { type: type };
        
        const li = document.createElement('li');
        li.className = `node-item type-${type}`;
        li.id = `node-li-${id}`;
        li.innerHTML = `
            <div>
                <strong>${type}</strong>
                <span style="font-family:monospace; color:var(--text-muted); display:block; font-size: 0.8em;">${id.substring(0,6)}</span>
            </div>
            <div id="stats-${id}" style="font-size: 0.8em; text-align: right; color: var(--text-muted);">
            </div>
        `;
        nodeListEl.appendChild(li);
    }
    
    if (battery !== null && load !== null) {
        document.getElementById(`stats-${id}`).innerHTML = `
            Bat: <span style="color:${battery < 30 ? 'var(--danger)' : 'var(--success)'}">${battery}%</span><br>
            Load: ${load}
        `;
    }
}

function updateDroneOnMap(id, x, y, status) {
    let marker = document.getElementById(`drone-${id}`);
    if (!marker) {
        marker = document.createElement('div');
        marker.id = `drone-${id}`;
        marker.className = 'node-marker Drone';
        mapEl.appendChild(marker);
        addNodeToList(id, "Drone");
    }
    
    marker.style.left = `${x}%`;
    marker.style.top = `${y}%`;
    
    if (status === 'RESPONDING') {
        marker.style.backgroundColor = 'var(--warning)';
        marker.style.boxShadow = '0 0 15px var(--warning)';
    } else {
        marker.style.backgroundColor = 'var(--accent)';
        marker.style.boxShadow = 'var(--neon-glow)';
    }
}

function showAccidentOnMap(x, y) {
    const existing = document.querySelector('.accident-marker');
    if (existing) existing.remove();
    
    const marker = document.createElement('div');
    marker.className = 'accident-marker';
    marker.style.left = `${x}%`;
    marker.style.top = `${y}%`;
    mapEl.appendChild(marker);
}

function addBlockToLedger(block) {
    if (!block) return;
    const list = document.getElementById('ledger-list');
    const li = document.createElement('li');
    li.className = `node-item`;
    li.style.borderLeftColor = '#8b5cf6'; // Purple for blockchain
    li.innerHTML = `
        <div style="width: 100%">
            <div style="display:flex; justify-content:space-between;">
                <strong>Block #${block.index}</strong>
                <span style="font-size: 0.8em; color:var(--text-muted)">Nonce: ${block.nonce}</span>
            </div>
            <div style="font-size: 0.85em; margin-top: 4px; color: var(--text-main);">
                ${block.data.event || "UNKNOWN_EVENT"}
            </div>
            <div style="font-size: 0.7em; margin-top: 4px; color: var(--text-muted); font-family: monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${block.hash}">
                Hash: ${block.hash}
            </div>
        </div>
    `;
    list.prepend(li);
}

