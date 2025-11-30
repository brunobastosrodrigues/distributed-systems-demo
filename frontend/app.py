from flask import Flask, jsonify, request
import requests
import docker
import random
import time

app = Flask(__name__)
docker_client = docker.from_env()

# --- Helper to identify backend components ---
def get_backend_info():
    """Finds a running backend container to copy its config."""
    containers = docker_client.containers.list()
    for c in containers:
        # We look for containers that are NOT the frontend or loadbalancer
        if "backend" in c.name and "frontend" not in c.name:
            return c
    return None

# --- API Endpoints for Automation ---

@app.route('/get-data')
def get_data():
    try:
        response = requests.get('http://loadbalancer:80/api', timeout=1)
        return jsonify(response.json())
    except:
        return jsonify({"served_by_node": "Offline", "message": "Backend Unreachable"})

@app.route('/api/scale')
def scale_up():
    """Simulates Horizontal Scaling: Adds 3 new containers."""
    try:
        template = get_backend_info()
        if not template:
            return jsonify({"status": "error", "msg": "No backend found to copy!"})
        
        # Get the network name (e.g., distributed-demo_private_net)
        net_name = list(template.attrs['NetworkSettings']['Networks'].keys())[0]
        image_name = template.image.tags[0] if template.image.tags else template.image.id

        # Launch 3 new nodes
        created = []
        for i in range(3):
            c = docker_client.containers.run(
                image_name,
                detach=True,
                network=net_name,
                environment={"Target": "AutoScaled"}
            )
            created.append(c.short_id)
        
        return jsonify({"status": "success", "msg": f"Scaled up! Added {len(created)} nodes.", "ids": created})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/kill')
def kill_node():
    """Simulates a Crash: Stops one random backend container."""
    try:
        template = get_backend_info()
        if not template: 
            return jsonify({"status": "error", "msg": "System already dead."})

        template.stop()
        return jsonify({"status": "success", "msg": f"CRASHED node {template.short_id}!"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- Frontend UI ---
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Distributed Control Plane</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root { --primary: #2c3e50; --accent: #3498db; --danger: #e74c3c; --success: #27ae60; --bg: #f4f6f9; }
            body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 20px; color: #333; }
            
            .main-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
            h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; color: var(--primary); }

            /* Diagram Styles */
            .diagram { display: flex; align-items: center; justify-content: space-around; padding: 20px 0; }
            .comp { text-align: center; font-size: 0.9rem; font-weight: bold; }
            .comp i { font-size: 2.5rem; margin-bottom: 10px; display: block; }
            .arrow { font-size: 1.5rem; color: #ccc; }
            .arrow.active { color: var(--success); transition: color 0.2s; }

            /* Backend Grid */
            .node-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; justify-content: center; }
            .node { background: #ecf0f1; padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; border: 2px solid transparent; transition: all 0.3s; opacity: 0.7; }
            .node.active { border-color: var(--success); background: #fff; opacity: 1; transform: scale(1.1); box-shadow: 0 5px 15px rgba(39, 174, 96, 0.3); }

            /* Log Table */
            table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
            td, th { padding: 8px; border-bottom: 1px solid #eee; text-align: left; }
            
            /* Action Buttons */
            .btn-theory { width: 100%; padding: 12px; margin-bottom: 10px; border: none; border-radius: 6px; cursor: pointer; text-align: left; background: #fff; border: 1px solid #ddd; transition: 0.2s; display: flex; align-items: center; justify-content: space-between; }
            .btn-theory:hover { background: #f8f9fa; border-color: var(--accent); }
            .btn-theory i { font-size: 1.2rem; color: var(--accent); }
            .btn-theory strong { display: block; font-size: 1rem; }
            .btn-theory small { color: #666; font-size: 0.8rem; }
            
            /* Toast Notification */
            #toast { visibility: hidden; min-width: 250px; background-color: #333; color: #fff; text-align: center; border-radius: 4px; padding: 16px; position: fixed; z-index: 1; left: 50%; bottom: 30px; transform: translateX(-50%); }
            #toast.show { visibility: visible; -webkit-animation: fadein 0.5s, fadeout 0.5s 2.5s; animation: fadein 0.5s, fadeout 0.5s 2.5s; }
            
            @keyframes fadein { from {bottom: 0; opacity: 0;} to {bottom: 30px; opacity: 1;} }
            @keyframes fadeout { from {bottom: 30px; opacity: 1;} to {bottom: 0; opacity: 0;} }
        </style>
    </head>
    <body>

    <div class="main-grid">
        <div>
            <div class="card">
                <h2>🏛️ Live Architecture</h2>
                <div class="diagram">
                    <div class="comp"><i class="fas fa-laptop" style="color:#34495e"></i>Client</div>
                    <div class="arrow" id="arrow1">➡</div>
                    <div class="comp"><i class="fas fa-random" style="color:#e67e22"></i>Load Balancer</div>
                    <div class="arrow" id="arrow2">➡</div>
                    <div class="comp" style="flex-grow: 1">
                        <i class="fas fa-server" style="color:#27ae60"></i> Backend Cluster
                        <div class="node-grid" id="backendGrid"></div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Traffic Log</h2>
                <table>
                    <thead><tr><th>Time</th><th>Node ID</th><th>Status</th></tr></thead>
                    <tbody id="logBody"></tbody>
                </table>
            </div>
        </div>

        <div>
            <div class="card">
                <h2>🎮 Interactive Demo</h2>
                <p style="font-size: 0.9rem; color: #666; margin-bottom: 20px;">Click a concept to execute it live on the cluster.</p>

                <button class="btn-theory" onclick="runDemo('scalability')">
                    <div>
                        <strong>2. Scalability</strong>
                        <small>Auto-add 3 new nodes to the cluster</small>
                    </div>
                    <i class="fas fa-layer-group"></i>
                </button>

                <button class="btn-theory" onclick="runDemo('fault')">
                    <div>
                        <strong>3. Fault Tolerance</strong>
                        <small>Crash (Kill) a random active node</small>
                    </div>
                    <i class="fas fa-heart-broken" style="color: var(--danger)"></i>
                </button>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                
                <div style="text-align: center;">
                    <button onclick="toggleTraffic(true)" id="startBtn" style="background:var(--success); color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">▶ Start Traffic</button>
                    <button onclick="toggleTraffic(false)" id="stopBtn" style="background:var(--danger); color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer; display:none;">⏹ Stop Traffic</button>
                </div>
            </div>
        </div>
    </div>

    <div id="toast">Action Executed!</div>

    <script>
        let interval = null;
        let knownNodes = new Set();
        
        // Color Helper
        function getColor(str) {
            let hash = 0;
            for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
            return '#' + '00000'.substring(0, 6 - (hash & 0x00FFFFFF).toString(16).toUpperCase().length) + (hash & 0x00FFFFFF).toString(16).toUpperCase();
        }

        async function fetchTraffic() {
            // Visual Arrows
            document.getElementById('arrow1').classList.add('active');
            setTimeout(() => document.getElementById('arrow2').classList.add('active'), 150);
            
            try {
                const res = await fetch('/get-data');
                const data = await res.json();
                
                if (data.served_by_node) {
                    const id = data.served_by_node;
                    
                    // Auto-Discover Nodes
                    if (!knownNodes.has(id) && id !== "Offline") {
                        knownNodes.add(id);
                        renderGrid();
                    }
                    
                    // Highlight Active
                    document.querySelectorAll('.node').forEach(n => n.classList.remove('active'));
                    const el = document.getElementById('node-'+id);
                    if(el) el.classList.add('active');

                    // Log
                    const row = `<tr><td>${new Date().toLocaleTimeString()}</td><td><span style="color:${getColor(id)}; font-weight:bold">${id}</span></td><td>OK</td></tr>`;
                    document.getElementById('logBody').insertAdjacentHTML('afterbegin', row);
                }
            } catch(e) { console.log(e); }

            setTimeout(() => {
                document.getElementById('arrow1').classList.remove('active');
                document.getElementById('arrow2').classList.remove('active');
            }, 500);
        }

        function renderGrid() {
            const grid = document.getElementById('backendGrid');
            grid.innerHTML = '';
            knownNodes.forEach(id => {
                grid.innerHTML += `<div class="node" id="node-${id}" style="border-left: 5px solid ${getColor(id)}">${id}</div>`;
            });
        }

        async function runDemo(type) {
            showToast("Executing Docker Command...");
            if (type === 'scalability') {
                await fetch('/api/scale');
                showToast("✅ Scaled Up! Watch the grid.");
            } else if (type === 'fault') {
                await fetch('/api/kill');
                showToast("⚠️ Node Crashed! System recovering...");
            }
        }

        function toggleTraffic(enable) {
            if (enable) {
                interval = setInterval(fetchTraffic, 1000);
                document.getElementById('startBtn').style.display = 'none';
                document.getElementById('stopBtn').style.display = 'inline-block';
            } else {
                clearInterval(interval);
                document.getElementById('startBtn').style.display = 'inline-block';
                document.getElementById('stopBtn').style.display = 'none';
            }
        }
        
        function showToast(msg) {
            const x = document.getElementById("toast");
            x.innerText = msg;
            x.className = "show";
            setTimeout(function(){ x.className = x.className.replace("show", ""); }, 3000);
        }
    </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)