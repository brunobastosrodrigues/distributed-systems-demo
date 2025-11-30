# frontend/app.py
from flask import Flask, jsonify
import requests
import docker
import random
import uuid

app = Flask(__name__)
client = docker.from_env()

# --- TRAFFIC LOGIC ---
@app.route('/get-data')
def get_data():
    try:
        # 1s timeout to prevent UI freezing
        response = requests.get('http://loadbalancer:80/api', timeout=1)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"served_by_node": "Offline", "error": str(e)})

# --- CONTROL PLANE LOGIC ---

def get_backend_containers():
    """Finds all containers acting as backend nodes."""
    return [c for c in client.containers.list() if "backend" in c.name and "frontend" not in c.name]

@app.route('/api/status')
def get_status():
    """Returns the live census of the cluster."""
    containers = get_backend_containers()
    # Clean up names for display
    active_nodes = [c.name.replace("distributed-systems-demo-", "") for c in containers]
    return jsonify({"count": len(active_nodes), "nodes": active_nodes})

@app.route('/api/scale')
def scale_up():
    try:
        # 1. Locate the Private Network
        networks = client.networks.list()
        # Find the network object that contains 'private_net' in its name
        private_net = next((n for n in networks if "private_net" in n.name), None)
        if not private_net: return jsonify({"status": "error", "msg": "Private network missing!"})

        # 2. Find a template image from an existing backend
        running = get_backend_containers()
        if not running: return jsonify({"status": "error", "msg": "No template found."})
        image_name = running[0].image.tags[0] if running[0].image.tags else running[0].image.id

        # 3. Launch 3 New Nodes
        created_names = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            name = f"backend-auto-{unique_id}"
            
            # Start container detached (not on network yet)
            c = client.containers.run(image_name, detach=True, name=name, network=None)
            
            # Connect to Private Network with alias 'backend' so Nginx can find it
            private_net.connect(c, aliases=['backend'])
            created_names.append(name)
        
        return jsonify({"status": "success", "msg": f"Launched: {', '.join(created_names)}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/kill')
def kill_node():
    try:
        containers = get_backend_containers()
        if not containers: return jsonify({"status": "error", "msg": "No nodes left!"})
        
        victim = random.choice(containers)
        name = victim.name
        victim.stop()
        victim.remove() # Clean up
        return jsonify({"status": "success", "msg": f"Terminated {name}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- UI CODE ---
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Distributed Systems Lab</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root { --bg: #f8fafc; --surface: #ffffff; --primary: #3b82f6; --success: #22c55e; --danger: #ef4444; }
            body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); margin: 0; padding: 20px; color: #1e293b; }
            
            .dashboard { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; max-width: 1400px; margin: 0 auto; }
            .card { background: var(--surface); padding: 24px; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            
            h2 { margin-top: 0; font-size: 1.25rem; display: flex; align-items: center; justify-content: space-between; }
            .badge { background: #dcfce7; color: #15803d; padding: 4px 12px; border-radius: 99px; font-size: 0.875rem; font-weight: 600; }
            
            /* Diagram */
            .diagram { display: flex; align-items: center; padding: 40px 0; }
            .node-icon { display: flex; flex-direction: column; align-items: center; z-index: 2; position: relative; }
            .icon-circle { width: 64px; height: 64px; background: #f1f5f9; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #64748b; margin-bottom: 8px; border: 2px solid #e2e8f0; transition: all 0.3s; }
            .arrow { flex: 1; height: 2px; background: #e2e8f0; margin: 0 -10px; position: relative; z-index: 1; }
            .arrow::after { content: '►'; position: absolute; right: 50%; top: -8px; color: #cbd5e1; font-size: 12px; background: var(--bg); padding: 0 4px; }
            
            .arrow.active { background: var(--success); }
            .arrow.active::after { color: var(--success); }
            .node-icon.pulse .icon-circle { border-color: var(--success); color: var(--success); background: #f0fdf4; box-shadow: 0 0 0 4px #dcfce7; }

            /* Grid */
            .grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; min-height: 100px; align-content: flex-start; }
            .backend-node { background: white; border: 2px solid #e2e8f0; padding: 10px 14px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; animation: popIn 0.3s ease; }
            .backend-node i { font-size: 0.6rem; color: #cbd5e1; }
            .backend-node.online { border-color: #cbd5e1; }
            .backend-node.active { border-color: var(--success); background: #f0fdf4; box-shadow: 0 4px 6px -1px rgba(34, 197, 94, 0.2); transform: translateY(-2px); }
            .backend-node.active i { color: var(--success); }

            /* Buttons */
            .btn { width: 100%; padding: 16px; border: none; border-radius: 12px; cursor: pointer; text-align: left; margin-bottom: 12px; transition: transform 0.1s; position: relative; overflow: hidden; }
            .btn:active { transform: scale(0.99); }
            .btn-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
            .btn-blue:hover { background: #dbeafe; }
            .btn-red { background: #fef2f2; color: #b91c1c; border: 1px solid #fee2e2; }
            .btn-red:hover { background: #fee2e2; }
            .btn-black { background: #0f172a; color: white; text-align: center; justify-content: center; display: flex; align-items: center; gap: 8px; margin-top: auto; }
            
            /* Logs */
            .log-window { background: #0f172a; color: #94a3b8; padding: 16px; border-radius: 12px; height: 200px; overflow: hidden; font-family: monospace; font-size: 0.8rem; display: flex; flex-direction: column; justify-content: flex-end; }
            .log-entry { margin-bottom: 4px; border-left: 2px solid transparent; padding-left: 8px; }
            .log-entry.success { border-color: var(--success); color: #dcfce7; }
            .log-entry.error { border-color: var(--danger); color: #fecaca; }

            @keyframes popIn { from { opacity:0; transform:scale(0.9); } to { opacity:1; transform:scale(1); } }
        </style>
    </head>
    <body>

    <div class="dashboard">
        <div class="card">
            <h2>Architecture <span class="badge" id="nodeCount">Initializing...</span></h2>
            
            <div class="diagram">
                <div class="node-icon" id="icon-client">
                    <div class="icon-circle"><i class="fas fa-laptop"></i></div>
                    <small>Client</small>
                </div>
                <div class="arrow" id="arrow1"></div>
                <div class="node-icon" id="icon-lb">
                    <div class="icon-circle"><i class="fas fa-sitemap"></i></div>
                    <small>Load Balancer</small>
                </div>
                <div class="arrow" id="arrow2"></div>
                <div class="node-icon" id="icon-cluster">
                    <div class="icon-circle"><i class="fas fa-server"></i></div>
                    <small>Backend Cluster</small>
                </div>
            </div>

            <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin-top: 20px;">
                <small style="color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Active Containers</small>
                <div class="grid" id="backendGrid"></div>
            </div>
        </div>

        <div class="card" style="display: flex; flex-direction: column;">
            <h2 style="margin-bottom: 20px;">Control Plane</h2>
            
            <button class="btn btn-blue" onclick="apiAction('/api/scale')">
                <div style="font-weight: 700; font-size: 1rem;">Add Resources</div>
                <div style="font-size: 0.85rem; opacity: 0.8;">+3 Nodes (Scalability)</div>
                <i class="fas fa-plus-circle" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>

            <button class="btn btn-red" onclick="apiAction('/api/kill')">
                <div style="font-weight: 700; font-size: 1rem;">Simulate Failure</div>
                <div style="font-size: 0.85rem; opacity: 0.8;">Crash 1 Node (Fault Tolerance)</div>
                <i class="fas fa-heart-broken" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>

            <div class="log-window" id="logContainer">
                <div>System ready. Waiting for traffic...</div>
            </div>

            <button class="btn btn-black" id="trafficBtn" onclick="toggleTraffic()">
                <i class="fas fa-play"></i> Start Traffic
            </button>
        </div>
    </div>

    <script>
        let trafficInterval;
        let isRunning = false;

        // 1. POLLING (The Source of Truth)
        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                renderGrid(data.nodes);
                document.getElementById('nodeCount').innerText = `${data.count} Nodes Active`;
            } catch(e) {}
        }, 1000);

        function renderGrid(nodes) {
            const grid = document.getElementById('backendGrid');
            const existingIds = Array.from(grid.children).map(el => el.id);
            
            // Add new
            nodes.forEach(id => {
                if(!existingIds.includes(id)) {
                    const el = document.createElement('div');
                    el.className = 'backend-node';
                    el.id = id;
                    el.innerHTML = `<i class="fas fa-circle"></i> ${id.substring(0, 10)}...`;
                    grid.appendChild(el);
                }
            });

            // Remove old
            Array.from(grid.children).forEach(el => {
                if(!nodes.includes(el.id)) el.remove();
            });
        }

        // 2. TRAFFIC SIMULATION
        async function sendRequest() {
            // Animate Diagram
            document.getElementById('arrow1').classList.add('active');
            document.getElementById('icon-lb').classList.add('pulse');
            
            setTimeout(() => {
                document.getElementById('arrow2').classList.add('active');
                document.getElementById('icon-cluster').classList.add('pulse');
            }, 150);

            setTimeout(() => {
                document.querySelectorAll('.active, .pulse').forEach(el => el.classList.remove('active', 'pulse'));
            }, 500);

            try {
                const res = await fetch('/get-data');
                const data = await res.json();
                
                if(data.served_by_node) {
                    // Highlight the specific node
                    const nodeId = data.served_by_node; 
                    // Note: The ID from get-data corresponds to hostname (Short ID), 
                    // but our status API returns Names. We match loosely.
                    const gridNodes = document.getElementById('backendGrid').children;
                    for(let node of gridNodes) {
                        if(node.innerText.includes(nodeId) || nodeId.includes(node.id)) {
                            node.classList.remove('active');
                            void node.offsetWidth; // Trigger reflow
                            node.classList.add('active');
                        }
                    }
                    log(`200 OK from ${nodeId}`, 'success');
                }
            } catch(e) {
                log('Request failed', 'error');
            }
        }

        function toggleTraffic() {
            const btn = document.getElementById('trafficBtn');
            if(isRunning) {
                clearInterval(trafficInterval);
                btn.innerHTML = '<i class="fas fa-play"></i> Start Traffic';
                btn.style.background = '#0f172a';
            } else {
                trafficInterval = setInterval(sendRequest, 800);
                btn.innerHTML = '<i class="fas fa-stop"></i> Stop Traffic';
                btn.style.background = '#ef4444';
            }
            isRunning = !isRunning;
        }

        async function apiAction(endpoint) {
            log('Executing command...', 'normal');
            try {
                const res = await fetch(endpoint);
                const data = await res.json();
                log(data.msg, data.status === 'success' ? 'success' : 'error');
            } catch(e) { log(e, 'error'); }
        }

        function log(msg, type) {
            const div = document.createElement('div');
            div.className = `log-entry ${type}`;
            div.innerText = `> ${msg}`;
            const container = document.getElementById('logContainer');
            container.appendChild(div);
            if(container.children.length > 8) container.firstChild.remove();
        }
    </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)