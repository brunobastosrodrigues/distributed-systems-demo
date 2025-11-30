from flask import Flask, jsonify
import requests
import docker
import random
import uuid
import time

app = Flask(__name__)
client = docker.from_env()

# --- Backend Logic (Traffic) ---
@app.route('/get-data')
def get_data():
    try:
        # 1 sec timeout so the UI doesn't freeze if Nginx is slow
        response = requests.get('http://loadbalancer:80/api', timeout=1)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"served_by_node": "Offline", "error": str(e)})

# --- Control Plane Logic ---

def get_backend_containers():
    """Returns list of backend containers based on name or image."""
    # Improved Filter: Looks for "backend" in the name OR the original image name
    return [
        c for c in client.containers.list() 
        if "backend" in c.name and "frontend" not in c.name
    ]

@app.route('/api/status')
def get_status():
    """Returns real-time census from Docker Engine."""
    containers = get_backend_containers()
    active_nodes = [c.name.replace("distributed-systems-demo-", "") for c in containers]
    return jsonify({
        "count": len(active_nodes), 
        "nodes": active_nodes
    })

@app.route('/api/scale')
def scale_up():
    try:
        # 1. Find the Network Name dynamically
        # We need the 'private_net' so Nginx can reach the new nodes
        networks = client.networks.list()
        private_net = next((n for n in networks if "private_net" in n.name), None)
        
        if not private_net:
            return jsonify({"status": "error", "msg": "Private network not found!"})

        # 2. Find the Image Name
        # We use the existing backend as a template
        running_backends = get_backend_containers()
        if not running_backends:
            return jsonify({"status": "error", "msg": "No template backend found."})
        
        image_name = running_backends[0].image.tags[0] if running_backends[0].image.tags else running_backends[0].image.id

        # 3. Create 3 New Nodes with SPECIFIC names and ALIASES
        created_names = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            container_name = f"backend-auto-{unique_id}"
            
            # Start the container (Not attached to network yet to avoid race conditions)
            container = client.containers.run(
                image_name, 
                detach=True,
                name=container_name, 
                network=None # We connect manually below
            )
            
            # Connect to Private Network with alias 'backend'
            # THIS IS KEY: The alias 'backend' allows Nginx to load balance to it!
            private_net.connect(container, aliases=['backend'])
            
            created_names.append(container_name)
        
        return jsonify({"status": "success", "msg": f"Added: {', '.join(created_names)}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/kill')
def kill_node():
    try:
        containers = get_backend_containers()
        if not containers: return jsonify({"status": "error", "msg": "No nodes left!"})
        
        # Don't kill the last one if possible, just to be nice
        victim = random.choice(containers)
        name = victim.name
        victim.stop()
        # Clean up the container so the name can be reused or just to keep things tidy
        victim.remove()
        
        return jsonify({"status": "success", "msg": f"Killed {name}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- UI (Same as before) ---
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Distributed Admin Console</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root { --bg: #f0f2f5; --card: #ffffff; --text: #1a1a1a; --green: #10b981; --red: #ef4444; --blue: #3b82f6; }
            body { font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
            
            .dashboard { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
            .card { background: var(--card); padding: 25px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
            
            .header-stat { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
            .live-badge { background: #d1fae5; color: #065f46; padding: 8px 16px; border-radius: 99px; font-weight: 700; display: flex; align-items: center; gap: 8px; font-size: 1.1rem; }
            .dot { height: 12px; width: 12px; background: var(--green); border-radius: 50%; display: inline-block; box-shadow: 0 0 0 4px #d1fae5; animation: pulse 2s infinite; }
            
            .diagram { display: flex; align-items: center; justify-content: space-between; padding: 40px 10px; position: relative; }
            .comp { text-align: center; font-weight: 600; font-size: 0.9rem; z-index: 2; }
            .comp i { font-size: 2.5rem; display: block; margin-bottom: 12px; color: #4b5563; background: #f3f4f6; padding: 20px; border-radius: 50%; }
            .arrow { flex: 1; height: 2px; background: #e5e7eb; margin: 0 20px; position: relative; }
            .arrow::after { content: '►'; position: absolute; right: 0; top: -6px; color: #e5e7eb; }
            .arrow.active { background: var(--green); transition: 0.2s; }
            .arrow.active::after { color: var(--green); }

            .grid-container { background: #f8fafc; border-radius: 12px; padding: 20px; margin-top: 10px; min-height: 100px; display: flex; flex-wrap: wrap; gap: 12px; align-content: flex-start; }
            .node { background: white; border: 2px solid #e2e8f0; padding: 10px 15px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; display: flex; align-items: center; gap: 8px; transition: all 0.3s ease; }
            .node.new { animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
            .node.traffic { border-color: var(--green); box-shadow: 0 0 0 4px #d1fae5; transform: translateY(-2px); }
            
            .btn { width: 100%; padding: 16px; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; transition: transform 0.1s; text-align: left; }
            .btn:active { transform: scale(0.98); }
            .btn-scale { background: #eff6ff; color: #1e40af; border: 1px solid #dbeafe; }
            .btn-kill { background: #fef2f2; color: #991b1b; border: 1px solid #fee2e2; }
            .btn-traffic { background: var(--text); color: white; justify-content: center; margin-top: 20px; }
            
            @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); } 100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
            @keyframes popIn { from { opacity: 0; transform: scale(0.5); } to { opacity: 1; transform: scale(1); } }
        </style>
    </head>
    <body>

    <div class="dashboard">
        <div class="card">
            <div class="header-stat">
                <h2>Architecture View</h2>
                <div class="live-badge">
                    <span class="dot"></span>
                    <span id="nodeCount">...</span> Active Nodes
                </div>
            </div>

            <div class="diagram">
                <div class="comp"><i class="fas fa-laptop"></i>Client</div>
                <div class="arrow" id="arrow1"></div>
                <div class="comp"><i class="fas fa-project-diagram"></i>Load Balancer</div>
                <div class="arrow" id="arrow2"></div>
                <div class="comp" style="flex: 2"><i class="fas fa-server"></i>Backend Cluster</div>
            </div>
            
            <div class="grid-container" id="nodeGrid"></div>
        </div>

        <div class="card">
            <h2>Control Plane</h2>
            <p style="color: #666; font-size: 0.9rem; margin-bottom: 25px;">Manipulate the infrastructure in real-time.</p>

            <button class="btn btn-scale" onclick="apiAction('/api/scale', 'Scaling up...')">
                <span><div style="font-size:1.1rem">Add Resources</div><small>+3 Nodes (Scalability)</small></span>
                <i class="fas fa-plus-circle fa-lg"></i>
            </button>

            <button class="btn btn-kill" onclick="apiAction('/api/kill', 'Killing node...')">
                <span><div style="font-size:1.1rem">Simulate Failure</div><small>Crash 1 Node (Fault Tolerance)</small></span>
                <i class="fas fa-bomb fa-lg"></i>
            </button>

            <button class="btn btn-traffic" id="trafficBtn" onclick="toggleTraffic()">
                <i class="fas fa-play" style="margin-right: 8px;"></i> Start Traffic Simulation
            </button>
            
            <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                <h3>Latest Logs</h3>
                <div id="logs" style="font-family: monospace; font-size: 0.8rem; color: #666; height: 150px; overflow: hidden; position: relative;">
                    <div style="position: absolute; bottom: 0; width: 100%;" id="logContent"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let isRunning = false;
        let trafficInterval;
        
        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                updateGrid(data.nodes);
                document.getElementById('nodeCount').innerText = data.count;
            } catch(e) {}
        }, 1000);

        function updateGrid(activeIds) {
            const grid = document.getElementById('nodeGrid');
            const currentElements = Array.from(grid.children);
            const currentIds = currentElements.map(el => el.id);
            
            activeIds.forEach(id => {
                if (!currentIds.includes(id)) {
                    const div = document.createElement('div');
                    div.id = id;
                    div.className = 'node new';
                    div.innerHTML = `<i class="fas fa-circle" style="color: #10b981; font-size: 0.6rem;"></i> ${id.substring(0, 12)}`;
                    grid.appendChild(div);
                }
            });

            currentElements.forEach(el => {
                if (!activeIds.includes(el.id)) el.remove();
            });
        }

        async function sendRequest() {
            document.getElementById('arrow1').classList.add('active');
            setTimeout(() => document.getElementById('arrow2').classList.add('active'), 150);
            setTimeout(() => {
                document.getElementById('arrow1').classList.remove('active');
                document.getElementById('arrow2').classList.remove('active');
            }, 500);

            try {
                const res = await fetch('/get-data');
                const data = await res.json();
                if (data.served_by_node) {
                    const nodeEl = document.getElementById(data.served_by_node);
                    if(!nodeEl) {
                        // If we got a response from a node we don't see yet, look for its name in our grid
                        const allNodes = document.querySelectorAll('.node');
                        allNodes.forEach(n => {
                            if(n.innerText.includes(data.served_by_node)) {
                                n.classList.remove('traffic');
                                void n.offsetWidth;
                                n.classList.add('traffic');
                            }
                        })
                    } else {
                        nodeEl.classList.remove('traffic');
                        void nodeEl.offsetWidth; 
                        nodeEl.classList.add('traffic');
                    }
                    addLog(`200 OK from ${data.served_by_node}`);
                }
            } catch(e) {}
        }

        function toggleTraffic() {
            const btn = document.getElementById('trafficBtn');
            if (isRunning) {
                clearInterval(trafficInterval);
                btn.innerHTML = '<i class="fas fa-play" style="margin-right: 8px;"></i> Start Traffic Simulation';
                btn.style.background = '#1a1a1a';
            } else {
                trafficInterval = setInterval(sendRequest, 800);
                btn.innerHTML = '<i class="fas fa-stop" style="margin-right: 8px;"></i> Stop Traffic';
                btn.style.background = '#ef4444';
            }
            isRunning = !isRunning;
        }

        async function apiAction(url, logMsg) {
            addLog(logMsg);
            await fetch(url);
        }

        function addLog(msg) {
            const container = document.getElementById('logContent');
            const div = document.createElement('div');
            div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
            container.appendChild(div);
            if (container.children.length > 8) container.firstChild.remove();
        }
    </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)