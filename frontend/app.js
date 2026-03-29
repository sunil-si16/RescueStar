const ws = new WebSocket(`ws://${window.location.host}/ws`);
const consoleEl = document.getElementById('console');
const nodeListEl = document.getElementById('node-list');
const mapEl = document.getElementById('map');
const triggerBtn = document.getElementById('trigger-btn');
const nodeCounterEl = document.getElementById('node-counter');
const globalStatusEl = document.getElementById('global-status');

let nodes = {};

ws.onopen = () => {
    logMsg('Connected to AESRS Visualizer Node.', 'system');
    logMsg('Awaiting swarm telemetry...', 'system');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleP2PEvent(data);
};

triggerBtn.addEventListener('click', () => {
    // Collect scenario settings
    const scenario = document.getElementById('scenario-type').value;
    const severity = document.getElementById('severity-level').value;
    
    // UI Elements for Demo Animation
    const demoOverlay = document.getElementById('demo-overlay');
    const overlayText = document.getElementById('overlay-text');
    
    // Disable Button
    triggerBtn.disabled = true;
    triggerBtn.classList.add('disabled');
    
    // Format text
    let formattedScenario = scenario.split('-').map(w => w.toUpperCase()).join(' ');
    overlayText.textContent = `LOCATING ${formattedScenario} EVENT...`;
    
    // Start Animation Sequence
    demoOverlay.classList.remove('hidden');
    demoOverlay.classList.add('active');
    
    globalStatusEl.className = "status-badge alert";
    globalStatusEl.innerHTML = `<span class="status-dot"></span> OUTBREAK DETECTED`;
    
    setTimeout(() => {
        overlayText.textContent = "CALCULating SWARM DISPATCH...";
        overlayText.style.color = "#f59e0b";
        document.querySelector('.scanning-circle').style.borderColor = "#f59e0b";
        
        setTimeout(() => {
            demoOverlay.classList.remove('active');
            setTimeout(() => { demoOverlay.classList.add('hidden'); }, 500);
            
            // Random Accident Coordinates
            const x = Math.floor(Math.random() * 70) + 15;
            const y = Math.floor(Math.random() * 70) + 15;
            
            // Send Command to Backend
            ws.send(JSON.stringify({
                action: 'TRIGGER_ACCIDENT',
                x: x,
                y: y,
                scenario: scenario,
                severity: severity
            }));
            
            triggerBtn.disabled = false;
            triggerBtn.classList.remove('disabled');
            
            // Reset overlay visual states for next time
            setTimeout(() => {
                overlayText.style.color = "var(--danger)";
                document.querySelector('.scanning-circle').style.borderColor = "var(--danger)";
            }, 1000);
            
        }, 1500);
    }, 1500);
});

function handleP2PEvent(msg) {
    const type = msg.type;
    const payload = msg.payload || {};
    const sender = msg.sender_id;
    
    // Log important events
    if (type !== 'DRONE_STATUS' && type !== '_greeting' && type !== 'HEARTBEAT' && type !== 'NEW_BLOCK') {
        logMsg(`[${sender?.substring(0,8) || 'SYSTEM'}] ${type}: ${JSON.stringify(payload)}`, `event-${type}`);
    }
    
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
        setTimeout(() => { alert(`🚑 AMBULANCE DISPATCHED to Coordinate!`); }, 500);
    }

    if (type === 'NEW_BLOCK') {
        addBlockToLedger(payload.block_data);
    }
}

function logMsg(text, className) {
    const el = document.createElement('div');
    el.className = `log-entry ${className}`;
    
    let now = new Date();
    let timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    el.innerHTML = `<span style="color:var(--text-muted); font-size: 0.8em; margin-right: 5px;">[${timeStr}]</span> > ${text}`;
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
                <strong style="font-size: 0.95em;">${type} Agent</strong>
                <span style="font-family:'Courier New', monospace; color:var(--text-muted); display:block; font-size: 0.75em; margin-top:2px;">ID: ${id.substring(0,8)}...</span>
            </div>
            <div id="stats-${id}" style="font-size: 0.8em; text-align: right; color: var(--text-muted); min-width: 60px;">
                <span class="flash">SYNCING</span>
            </div>
        `;
        nodeListEl.appendChild(li);
        
        // Update Counter
        nodeCounterEl.textContent = `${Object.keys(nodes).length} Active Agents`;
    }
    
    if (battery !== null && load !== null) {
        document.getElementById(`stats-${id}`).innerHTML = `
            Bat: <span style="font-weight:bold; color:${battery < 30 ? 'var(--danger)' : 'var(--success)'}">${battery}%</span><br>
            Task: ${load}
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
        marker.style.boxShadow = '0 0 20px var(--warning)';
        marker.style.borderColor = 'white';
    } else {
        marker.style.backgroundColor = 'var(--accent)';
        marker.style.boxShadow = '0 0 15px var(--accent)';
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
    li.style.borderLeftColor = '#a855f7'; 
    li.style.background = 'rgba(168, 85, 247, 0.05)';
    
    li.innerHTML = `
        <div style="width: 100%">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color: #c084fc;">Block #${block.index}</strong>
                <span style="font-size: 0.75em; color:var(--text-muted); background:rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">Nonce: ${block.nonce}</span>
            </div>
            <div style="font-size: 0.85em; margin-top: 6px; color: var(--text-main); font-weight: 500;">
                Event: ${block.data.event || "UNKNOWN_EVENT"}
            </div>
            <div style="font-size: 0.7em; margin-top: 6px; color: var(--text-muted); font-family: 'Courier New', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 4px; background: rgba(0,0,0,0.3); border-radius: 4px;" title="${block.hash}">
                ${block.hash}
            </div>
        </div>
    `;
    list.prepend(li);
}
