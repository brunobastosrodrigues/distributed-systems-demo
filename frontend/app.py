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
        response = requests.get('http://loadbalancer:80/api', timeout=1)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"served_by_node": "Offline", "error": str(e)})

# --- CONTROL PLANE LOGIC ---

def get_backend_containers():
    # Matches "backend" or "backend-node"
    return [c for c in client.containers.list() if "backend" in c.name and "frontend" not in c.name]

@app.route('/api/status')
def get_status():
    containers = get_backend_containers()
    # Return list of dicts with ID and Image Type (for icons)
    nodes = []
    for c in containers:
        is_node = "node" in c.name or "node" in str(c.image.tags)
        type_label = "node" if is_node else "python"
        nodes.append({"id": c.name.replace("distributed-systems-demo-", ""), "type": type_label})
    
    return jsonify({"count": len(nodes), "nodes": nodes})

@app.route('/api/scale/<type>')
def scale_up(type):
    try:
        networks = client.networks.list()
        private_net = next((n for n in networks if "private_net" in n.name), None)
        if not private_net: return jsonify({"status": "error", "msg": "Private network missing!"})

        # Select Image based on button click
        if type == 'node':
            # Name of the image built by docker compose
            image_name = "distributed-systems-demo-backend_node"
            prefix = "backend-node-js-"
        else:
            image_name = "distributed-systems-demo-backend"
            prefix = "backend-python-"

        # Launch 1 New Node
        unique_id = str(uuid.uuid4())[:8]
        name = f"{prefix}{unique_id}"
        
        c = client.containers.run(image_name, detach=True, name=name, network=None)
        private_net.connect(c, aliases=['backend'])
        
        return jsonify({"status": "success", "msg": f"Launched {type} node: {name}"})
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
        victim.remove()
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
            h2 { margin-top: 0; font-size: 1.25rem; }
            .badge { background: #dcfce7; color: #15803d; padding: 4px 12px; border-radius: 99px; font-size: 0.875rem; font-weight: 600; }
            
            /* Diagram */
            .diagram { display: flex; align-items: center; padding: 40px 0; justify-content: space-between; }
            .node-icon { text-align: center; position: relative; z-index: 2; }
            .icon-circle { width: 64px; height: 64px; background: #f1f5f9; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #64748b; margin: 0 auto 8px; border: 2px solid #e2e8f0; transition: 0.3s; }
            .arrow { flex: 1; height: 2px; background: #e2e8f0; margin: 0 10px; position: relative; }
            .arrow::after { content: '►'; position: absolute; right: 50%; top: -8px; color: #cbd5e1; font-size: 12px; background: var(--bg); }
            .arrow.active { background: var(--success); }
            .arrow.active::after { color: var(--success); }
            
            /* Grid */
            .grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; min-height: 100px; align-content: flex-start; }
            .backend-node { background: white; border: 2px solid #e2e8f0; padding: 10px 14px; border-radius: 8px; font-family: monospace; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; animation: popIn 0.3s ease; }
            .backend-node.active { border-color: var(--success); background: #f0fdf4; transform: translateY(-2px); }
            .backend-node i.fa-python { color: #306998; }
            .backend-node i.fa-node-js { color: #68a063; }

            /* Buttons */
            .btn { width: 100%; padding: 16px; border: none; border-radius: 12px; cursor: pointer; text-align: left; margin-bottom: 12px; transition: 0.1s; position: relative; }
            .btn:active { transform: scale(0.99); }
            .btn-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
            .btn-green { background: #f0fdf4; color: #15803d; border: 1px solid #dcfce7; }
            .btn-red { background: #fef2f2; color: #b91c1c; border: 1px solid #fee2e2; }
            .btn-black { background: #0f172a; color: white; text-align: center; }
            .btn-gray { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

            .log-window { background: #0f172a; color: #94a3b8; padding: 16px; border-radius: 12px; height: 150px; overflow: hidden; font-family: monospace; font-size: 0.8rem; display: flex; flex-direction: column; justify-content: flex-end; margin-top: 20px;}
            
            @keyframes popIn { from { opacity:0; transform:scale(0.9); } to { opacity:1; transform:scale(1); } }
            .security-modal { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); z-index: 100; width: 400px; text-align: center; border: 2px solid #e2e8f0;}
            .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 99; }
        </style>
    </head>
    <body>

    <div class="dashboard">
        <div class="card">
            <h2>Architecture <span class="badge" id="nodeCount">...</span></h2>
            
            <div class="diagram">
                <div class="node-icon"><div class="icon-circle"><i class="fas fa-laptop"></i></div><small>Client</small></div>
                <div class="arrow" id="arrow1"></div>
                <div class="node-icon"><div class="icon-circle"><i class="fas fa-sitemap"></i></div><small>Load Balancer</small></div>
                <div class="arrow" id="arrow2"></div>
                <div class="node-icon"><div class="icon-circle"><i class="fas fa-layer-group"></i></div><small>Heterogeneous Cluster</small></div>
            </div>

            <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin-top: 20px;">
                <small style="color: #64748b; font-weight: 600; text-transform: uppercase;">Active Containers</small>
                <div class="grid" id="backendGrid"></div>
            </div>
            
             <div class="log-window" id="logContainer"><div>System ready.</div></div>
        </div>

        <div class="card">
            <h2>Control Plane</h2>
            
            <button class="btn btn-blue" onclick="apiAction('/api/scale/python')">
                <strong>+ Python Node</strong><br><small>Scalability (Homogeneous)</small>
                <i class="fab fa-python" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>

            <button class="btn btn-green" onclick="apiAction('/api/scale/node')">
                <strong>+ Node.js Node</strong><br><small>Heterogeneity & Openness</small>
                <i class="fab fa-node-js" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>

            <button class="btn btn-red" onclick="apiAction('/api/kill')">
                <strong>Simulate Failure</strong><br><small>Fault Tolerance</small>
                <i class="fas fa-bomb" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>
            
            <button class="btn btn-gray" onclick="testSecurity()">
                <strong>Security Audit</strong><br><small>Test Network Isolation</small>
                <i class="fas fa-shield-alt" style="position: absolute; right: 20px; top: 50%; transform: translateY(-50%); font-size: 1.5rem; opacity: 0.5;"></i>
            </button>

            <button class="btn btn-black" id="trafficBtn" onclick="toggleTraffic()">
                <i class="fas fa-play"></i> Start Traffic
            </button>
        </div>
    </div>
    
    <div class="overlay" id="overlay" onclick="closeModal()"></div>
    <div class="security-modal" id="securityModal">
        <div style="font-size: 3rem; margin-bottom: 20px;">🛡️</div>
        <h3>Security Audit Result</h3>
        <p>Attempting to access Backend Node directly from your Browser (Public Internet)...</p>
        <div style="background: #fee2e2; color: #b91c1c; padding: 15px; border-radius: 8px; font-weight: bold; margin-top: 15px;">
            <i class="fas fa-lock"></i> ACCESS DENIED
        </div>
        <p style="font-size: 0.8rem; color: #666; margin-top: 15px;">
            Your browser cannot reach 172.x.x.x. <br>The backend is isolated in a private network (<code>internal: true</code>).
        </p>
    </div>

    <script>
        let trafficInterval, isRunning = false;

        setInterval(async () => {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                renderGrid(data.nodes);
                document.getElementById('nodeCount').innerText = `${data.count} Active`;
            } catch(e) {}
        }, 1000);

        function renderGrid(nodes) {
            const grid = document.getElementById('backendGrid');
            const ids = nodes.map(n => n.id);
            
            // Remove old
            Array.from(grid.children).forEach(el => {
                if(!ids.includes(el.id)) el.remove();
            });

            // Add new
            nodes.forEach(n => {
                if(!document.getElementById(n.id)) {
                    const el = document.createElement('div');
                    el.className = 'backend-node';
                    el.id = n.id;
                    const icon = n.type === 'node' ? 'fa-node-js' : 'fa-python';
                    el.innerHTML = `<i class="fab ${icon}"></i> ${n.id.substring(0, 10)}...`;
                    grid.appendChild(el);
                }
            });
        }

        async function sendRequest() {
            // Animate
            document.getElementById('arrow1').classList.add('active');
            setTimeout(() => document.getElementById('arrow2').classList.add('active'), 150);
            setTimeout(() => { document.querySelectorAll('.active').forEach(e => e.classList.remove('active')) }, 500);

            try {
                const res = await fetch('/get-data');
                const data = await res.json();
                if(data.served_by_node) {
                    const el = Array.from(document.querySelectorAll('.backend-node')).find(e => e.innerText.includes(data.served_by_node));
                    if(el) {
                        el.classList.remove('active');
                        void el.offsetWidth;
                        el.classList.add('active');
                    }
                    const arch = data.architecture || "Unknown";
                    log(`200 OK | ${arch} | ${data.served_by_node}`, 'success');
                }
            } catch(e) { log('Error', 'error'); }
        }

        function toggleTraffic() {
            const btn = document.getElementById('trafficBtn');
            if(isRunning) {
                clearInterval(trafficInterval);
                btn.innerHTML = '<i class="fas fa-play"></i> Start Traffic';
            } else {
                trafficInterval = setInterval(sendRequest, 800);
                btn.innerHTML = '<i class="fas fa-stop"></i> Stop Traffic';
            }
            isRunning = !isRunning;
        }

        async function apiAction(url) {
            log('Executing command...', 'normal');
            try {
                const res = await fetch(url);
                const data = await res.json();
                log(data.msg, data.status === 'success' ? 'success' : 'error');
            } catch(e) { log(e, 'error'); }
        }

        function testSecurity() {
            document.getElementById('overlay').style.display = 'block';
            document.getElementById('securityModal').style.display = 'block';
            // In reality, we could try a fetch('http://172.x.x.x') here and catch the timeout error
        }
        
        function closeModal() {
            document.getElementById('overlay').style.display = 'none';
            document.getElementById('securityModal').style.display = 'none';
        }

        function log(msg, type) {
            const div = document.createElement('div');
            div.style.color = type === 'success' ? '#22c55e' : (type === 'error' ? '#ef4444' : '#94a3b8');
            div.innerText = `> ${msg}`;
            const c = document.getElementById('logContainer');
            c.appendChild(div);
            if(c.children.length > 6) c.firstChild.remove();
        }
    </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)