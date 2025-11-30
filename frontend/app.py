from flask import Flask, jsonify
import requests
import random
import os

app = Flask(__name__)

# --- Backend Logic ---
@app.route('/get-data')
def get_data():
    try:
        # Request goes to Nginx (Load Balancer), not directly to backend
        response = requests.get('http://loadbalancer:80/api', timeout=2)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e), "served_by_node": "Offline", "message": "Backend Unreachable"})

# --- Frontend UI (Embedded HTML/JS) ---
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Distributed Architecture Lab</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            :root { --primary: #2c3e50; --accent: #3498db; --success: #27ae60; --bg: #f8f9fa; }
            body { font-family: 'Segoe UI', sans-serif; background: var(--bg); margin: 0; padding: 0; color: #333; }
            
            /* Layout */
            .main-container { max-width: 1200px; margin: 0 auto; padding: 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
            .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
            h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-top: 0; font-size: 1.2rem; color: var(--primary); }

            /* Diagram Container */
            .diagram { display: flex; align-items: center; justify-content: space-between; padding: 30px 10px; position: relative; }
            .component { text-align: center; position: relative; z-index: 2; transition: all 0.3s; }
            .component i { font-size: 2.5rem; margin-bottom: 10px; color: var(--primary); background: white; padding: 15px; border-radius: 50%; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
            .component label { display: block; font-weight: bold; font-size: 0.9rem; }
            
            /* Arrows */
            .arrow { flex-grow: 1; height: 2px; background: #ddd; position: relative; margin: 0 15px; }
            .arrow::after { content: '►'; position: absolute; right: 0; top: -7px; color: #ddd; font-size: 14px; }
            .arrow.active { background: var(--success); transition: background 0.2s; }
            .arrow.active::after { color: var(--success); }

            /* Backend Grid */
            .backend-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 10px; background: #f1f2f6; padding: 15px; border-radius: 8px; min-width: 250px; }
            .node-box { background: white; padding: 10px; border-radius: 6px; font-size: 0.8rem; text-align: center; border: 2px solid transparent; opacity: 0.6; transition: all 0.3s; }
            .node-box.active { border-color: var(--success); opacity: 1; transform: scale(1.1); box-shadow: 0 0 10px rgba(39, 174, 96, 0.4); }
            .node-box i { font-size: 1.2rem; color: #7f8c8d; display: block; margin-bottom: 5px; }

            /* Theory Section */
            .theory-item { margin-bottom: 15px; padding: 10px; border-left: 4px solid #ddd; cursor: pointer; transition: 0.2s; }
            .theory-item:hover { background: #f1f1f1; }
            .theory-item.highlight { border-left-color: var(--accent); background: #e3f2fd; }
            .theory-title { font-weight: bold; display: flex; justify-content: space-between; }
            .theory-desc { font-size: 0.85rem; color: #666; margin-top: 5px; display: none; }
            .theory-item.highlight .theory-desc { display: block; }

            /* Log Table */
            table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
            th { text-align: left; color: #777; font-weight: 600; border-bottom: 1px solid #eee; padding: 8px; }
            td { padding: 8px; border-bottom: 1px solid #f9f9f9; }
            .badge { padding: 3px 8px; border-radius: 10px; background: #eee; font-family: monospace; }

            /* Controls */
            .btn { background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; width: 100%; margin-bottom: 10px; }
            .btn:hover { opacity: 0.9; }
            .btn.stop { background: #e74c3c; display: none; }
        </style>
    </head>
    <body>

    <div class="main-container">
        <div class="col-left">
            <div class="card">
                <h2>🏛️ System Architecture</h2>
                <div class="diagram">
                    <div class="component">
                        <i class="fas fa-laptop-code"></i>
                        <label>Web Client<br>(You)</label>
                    </div>
                    
                    <div class="arrow" id="arrow1"></div>

                    <div class="component">
                        <i class="fas fa-network-wired"></i>
                        <label>Load Balancer<br>(Nginx)</label>
                    </div>

                    <div class="arrow" id="arrow2"></div>

                    <div class="backend-container" style="text-align: center;">
                        <div class="backend-grid" id="backendGrid">
                            <div style="grid-column: 1/-1; color: #aaa; font-size: 0.8rem;">Waiting for requests...</div>
                        </div>
                        <label style="margin-top: 10px; display: block;">Backend Cluster<br>(Python Nodes)</label>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>📊 Request Log</h2>
                <table>
                    <thead>
                        <tr><th>Time</th><th>Served By Container</th><th>Status</th></tr>
                    </thead>
                    <tbody id="logBody"></tbody>
                </table>
            </div>
        </div>

        <div class="col-right">
            <div class="card">
                <h2>🎮 Controls</h2>
                <div style="text-align: center; margin-bottom: 15px;">
                    <span style="font-size: 2rem; font-weight: bold; color: var(--success);" id="currentNode">---</span>
                    <div style="font-size: 0.8rem; color: #777;">Last Response Node</div>
                </div>
                <button class="btn" id="startBtn" onclick="toggleAuto(true)">▶ Start Simulation</button>
                <button class="btn stop" id="stopBtn" onclick="toggleAuto(false)">⏹ Stop</button>
            </div>

            <div class="card">
                <h2>📚 Theory Mapping</h2>
                <p style="font-size: 0.8rem; color: #666;">Click to see how this demo proves the concept:</p>
                
                <div class="theory-item" onclick="highlightTheory(this)">
                    <div class="theory-title">1. Transparency <i class="fas fa-eye-slash"></i></div>
                    <div class="theory-desc">The 'Web Client' never knows which Python Node answers. It only sees the Load Balancer.</div>
                </div>

                <div class="theory-item" onclick="highlightTheory(this)">
                    <div class="theory-title">2. Scalability <i class="fas fa-layer-group"></i></div>
                    <div class="theory-desc">Run <code>docker compose up --scale backend=5</code>. Watch the grid above grow automatically!</div>
                </div>

                <div class="theory-item" onclick="highlightTheory(this)">
                    <div class="theory-title">3. Fault Tolerance <i class="fas fa-heartbeat"></i></div>
                    <div class="theory-desc">Run <code>docker stop [id]</code>. The grid node will turn red, but the system keeps working!</div>
                </div>

                <div class="theory-item" onclick="highlightTheory(this)">
                    <div class="theory-title">4. Heterogeneity <i class="fas fa-random"></i></div>
                    <div class="theory-desc">Client is Browser, Middleware is Nginx (C), Backend is Python. They all talk JSON.</div>
                </div>

                 <div class="theory-item" onclick="highlightTheory(this)">
                    <div class="theory-title">5. Security <i class="fas fa-lock"></i></div>
                    <div class="theory-desc">Try <code>curl http://ip:5000</code>. It fails. The Backends are isolated in a private network.</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let intervalId = null;
        let knownNodes = new Set();

        // Color generator for nodes
        function getColor(str) {
            let hash = 0;
            for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
            return '#' + '00000'.substring(0, 6 - (hash & 0x00FFFFFF).toString(16).toUpperCase().length) + (hash & 0x00FFFFFF).toString(16).toUpperCase();
        }

        async function fetchData() {
            // Visual: Activate Arrows
            document.getElementById('arrow1').classList.add('active');
            setTimeout(() => document.getElementById('arrow2').classList.add('active'), 200);

            try {
                const res = await fetch('/get-data');
                const data = await res.json();
                handleResponse(data);
            } catch (e) {
                console.error(e);
            }

            // Visual: Deactivate Arrows
            setTimeout(() => {
                document.getElementById('arrow1').classList.remove('active');
                document.getElementById('arrow2').classList.remove('active');
            }, 600);
        }

        function handleResponse(data) {
            const nodeId = data.served_by_node;
            if(!nodeId) return;

            // 1. Update known nodes logic (Auto-Discovery)
            if (!knownNodes.has(nodeId)) {
                knownNodes.add(nodeId);
                renderBackendGrid();
            }

            // 2. Highlight the active node in the grid
            document.querySelectorAll('.node-box').forEach(el => el.classList.remove('active'));
            const activeBox = document.getElementById('node-' + nodeId);
            if (activeBox) activeBox.classList.add('active');

            // 3. Update Log
            const tbody = document.getElementById('logBody');
            const row = `<tr>
                <td>${new Date().toLocaleTimeString()}</td>
                <td><span class="badge" style="background-color: ${getColor(nodeId)}; color: #fff">${nodeId}</span></td>
                <td style="color: green">200 OK</td>
            </tr>`;
            tbody.insertAdjacentHTML('afterbegin', row);
            if(tbody.rows.length > 8) tbody.deleteRow(8);

            // 4. Update Big Display
            const display = document.getElementById('currentNode');
            display.innerText = nodeId;
            display.style.color = getColor(nodeId);
        }

        function renderBackendGrid() {
            const grid = document.getElementById('backendGrid');
            grid.innerHTML = ''; // Clear
            
            knownNodes.forEach(id => {
                const color = getColor(id);
                grid.innerHTML += `
                    <div class="node-box" id="node-${id}">
                        <i class="fas fa-server" style="color: ${color}"></i>
                        ${id.substring(0,6)}...
                    </div>
                `;
            });
        }

        function toggleAuto(enable) {
            const start = document.getElementById('startBtn');
            const stop = document.getElementById('stopBtn');
            if (enable) {
                fetchData();
                intervalId = setInterval(fetchData, 1200);
                start.style.display = 'none';
                stop.style.display = 'block';
            } else {
                clearInterval(intervalId);
                start.style.display = 'block';
                stop.style.display = 'none';
            }
        }

        function highlightTheory(el) {
            document.querySelectorAll('.theory-item').forEach(e => e.classList.remove('highlight'));
            el.classList.add('highlight');
        }
    </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)