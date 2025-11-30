from flask import Flask, jsonify
import requests
import docker
import random

app = Flask(__name__)
client = docker.from_env()

# --- Backend Logic (Traffic) ---
@app.route('/get-data')
def get_data():
    try:
        response = requests.get('http://loadbalancer:80/api', timeout=1)
        return jsonify(response.json())
    except:
        return jsonify({"served_by_node": "Offline"})

# --- Control Plane Logic (Docker Management) ---
def get_backend_containers():
    """Returns a list of all Docker containers that are 'backend' nodes."""
    return [c for c in client.containers.list() if "backend" in c.name and "frontend" not in c.name]

@app.route('/api/status')
def get_status():
    """Returns the exact count and IDs of live nodes from Docker."""
    containers = get_backend_containers()
    active_nodes = [c.short_id for c in containers]
    return jsonify({
        "count": len(active_nodes), 
        "nodes": active_nodes
    })

@app.route('/api/scale')
def scale_up():
    try:
        # Find any running backend to use as a template
        containers = get_backend_containers()
        if not containers: return jsonify({"status": "error", "msg": "No template node found!"})
        template = containers[0]

        net_name = list(template.attrs['NetworkSettings']['Networks'].keys())[0]
        image = template.image.tags[0] if template.image.tags else template.image.id

        # Add 3 nodes
        for i in range(3):
            client.containers.run(image, detach=True, network=net_name)
        
        return jsonify({"status": "success", "msg": "Scaled up by 3 nodes."})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/kill')
def kill_node():
    try:
        containers = get_backend_containers()
        if not containers: return jsonify({"status": "error", "msg": "No nodes left to kill!"})
        
        victim = random.choice(containers)
        victim.stop()
        return jsonify({"status": "success", "msg": f"Stopped node {victim.short_id}"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- UI ---
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
            
            /* Header Stats */
            .header-stat { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
            .live-badge { background: #d1fae5; color: #065f46; padding: 8px 16px; border-radius: 99px; font-weight: 700; display: flex; align-items: center; gap: 8px; font-size: 1.1rem; }
            .dot { height: 12px; width: 12px; background: var(--green); border-radius: 50%; display: inline-block; box-shadow: 0 0 0 4px #d1fae5; animation: pulse 2s infinite; }
            
            /* Architecture Diagram */
            .diagram { display: flex; align-items: center; justify-content: space-between; padding: 40px 10px; position: relative; }
            .comp { text-align: center; font-weight: 600; font-size: 0.9rem; z-index: 2; }
            .comp i { font-size: 2.5rem; display: block; margin-bottom: 12px; color: #4b5563; background: #f3f4f6; padding: 20px; border-radius: 50%; }
            .arrow { flex: 1; height: 2px; background: #e5e7eb; margin: 0 20px; position: relative; }
            .arrow::after { content: '►'; position: absolute; right: 0; top: -6px; color: #e5e7eb; }
            .arrow.active { background: var(--green); transition: 0.2s; }
            .arrow.active::after { color: var(--green); }

            /* Grid */
            .grid-container { background: #f8fafc; border-radius: 12px; padding: 20px; margin-top: 10px; min-height: 100px; display: flex; flex-wrap: wrap; gap: 12px; align-content: flex-start; }
            .node { background: white; border: 2px solid #e2e8f0; padding: 10px 15px; border-radius: 8px; font-family: monospace; font-size: 0.9rem; display: flex; align-items: center; gap: 8px; transition: all 0.3s ease; }
            .node.new { animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
            .node.traffic { border-color: var(--green); box-shadow: 0 0 0 4px #d1fae5; transform: translateY(-2px); }
            
            /* Controls */
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
                <div class="comp">
                    <i class="fas fa-laptop"></i>
                    Client
                </div>
                <div class="arrow" id="arrow1"></div>
                <div class="comp">
                    <i class="fas fa-project-diagram"></i>
                    Load Balancer
                </div>
                <div class="arrow" id="arrow2"></div>
                <div class="comp" style="flex: 2">
                    <i class="fas fa-server"></i>
                    Backend Cluster
                </div>
            </div>
            
            <div class="grid-container" id="nodeGrid">
                </div>
        </div>

        <div class="card">
            <h2>Control Plane</h2>
            <p style="color: #666; font-size: 0.9rem; margin-bottom: 25px;">Manipulate the infrastructure in real-time.</p>

            <button class="btn btn-scale" onclick="apiAction('/api/scale', 'Scaling up...')">
                <span>
                    <div style="font-size:1.1rem">Add Resources</div>
                    <small>+3 Nodes (Scalability)</small>
                </span>
                <i class="fas fa-plus-circle fa-lg"></i>
            </button>

            <button class="btn btn-kill" onclick="apiAction('/api/kill', 'Killing node...')">
                <span>
                    <div style="font-size:1.1rem">Simulate Failure</div>
                    <small>Crash 1 Node (Fault Tolerance)</small>
                </span>
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
        
        // 1. SYSTEM MONITOR (Runs always)
        // Polls Docker every 1s to get the Source of Truth
        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                updateGrid(data.nodes);
                document.getElementById('nodeCount').innerText = data.count;
            } catch(e) { console.error("Monitor error", e); }
        }, 1000);

        function updateGrid(activeIds) {
            const grid = document.getElementById('nodeGrid');
            const currentElements = Array.from(grid.children);
            const currentIds = currentElements.map(el => el.id);
            
            // Add New Nodes
            activeIds.forEach(id => {
                if (!currentIds.includes(id)) {
                    const div = document.createElement('div');
                    div.id = id;
                    div.className = 'node new';
                    div.innerHTML = `<i class="fas fa-circle" style="color: #10b981; font-size: 0.6rem;"></i> ${id}`;
                    grid.appendChild(div);
                }
            });

            // Remove Dead Nodes
            currentElements.forEach(el => {
                if (!activeIds.includes(el.id)) el.remove();
            });
        }

        // 2. TRAFFIC SIMULATOR
        async function sendRequest() {
            // Visuals
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
                    if (nodeEl) {
                        nodeEl.classList.remove('traffic');
                        void nodeEl.offsetWidth; // Trigger reflow
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

        // 3. ACTIONS
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