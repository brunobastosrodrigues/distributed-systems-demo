from flask import Flask, jsonify
import requests
import random

app = Flask(__name__)

# This handles the browser's request for data
@app.route('/get-data')
def get_data():
    try:
        # The Frontend Container talks to the Load Balancer
        response = requests.get('http://loadbalancer:80/api', timeout=2)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e), "served_by_node": "Offline", "message": "Backend Unreachable"})

# This serves the Dashboard UI
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Distributed System Demo</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 20px; }
            .container { max-width: 900px; margin: 0 auto; }
            .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }
            h1 { color: #2c3e50; text-align: center; }
            
            /* Status Box */
            .status-box { text-align: center; padding: 20px; background: #e8f5e9; border-radius: 8px; border: 2px solid #4caf50; }
            .node-id { font-size: 2em; font-weight: bold; color: #2e7d32; }
            
            /* Controls */
            .controls { text-align: center; margin: 20px 0; }
            button { padding: 10px 20px; font-size: 16px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 5px; transition: 0.3s; }
            button:hover { background: #0056b3; }
            button#stopBtn { background: #dc3545; display: none; }
            
            /* Log Table */
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f8f9fa; }
            
            /* Badges for Visualizing Nodes */
            .badge { padding: 5px 10px; border-radius: 4px; color: white; font-weight: bold; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌐 Distributed System Dashboard</h1>
            
            <div class="card">
                <div class="status-box">
                    <div>Current Response Served By:</div>
                    <div class="node-id" id="currentNode">Waiting...</div>
                    <div id="techStack" style="color: #666; margin-top: 5px;">-</div>
                </div>
                
                <div class="controls">
                    <button id="startBtn" onclick="toggleAutoRefresh(true)">▶ Start Auto-Request</button>
                    <button id="stopBtn" onclick="toggleAutoRefresh(false)">⏹ Stop</button>
                    <button onclick="fetchData()">🔄 Single Request</button>
                </div>
            </div>

            <div class="card">
                <h3>📊 Request Distribution Log</h3>
                <p><i>Watch how the Load Balancer rotates through the available containers (Round Robin).</i></p>
                <table id="logTable">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Backend Node ID</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        </tbody>
                </table>
            </div>
        </div>

        <script>
            let intervalId = null;

            // Generate a consistent color for a container ID so students can track it visually
            function stringToColor(str) {
                let hash = 0;
                for (let i = 0; i < str.length; i++) {
                    hash = str.charCodeAt(i) + ((hash << 5) - hash);
                }
                const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
                return '#' + '00000'.substring(0, 6 - c.length) + c;
            }

            async function fetchData() {
                try {
                    const res = await fetch('/get-data');
                    const data = await res.json();
                    updateUI(data);
                } catch (err) {
                    console.error(err);
                }
            }

            function updateUI(data) {
                const nodeId = data.served_by_node || "Unknown";
                const color = stringToColor(nodeId);
                
                // Update Main Display
                document.getElementById('currentNode').innerText = nodeId;
                document.getElementById('currentNode').style.color = color;
                document.getElementById('techStack').innerText = data.architecture || "Error";

                // Add to Log Table (Top 50 rows only)
                const table = document.getElementById('logTable').getElementsByTagName('tbody')[0];
                const newRow = table.insertRow(0);
                
                const timeCell = newRow.insertCell(0);
                timeCell.innerText = new Date().toLocaleTimeString();
                
                const nodeCell = newRow.insertCell(1);
                nodeCell.innerHTML = `<span class="badge" style="background-color: ${color}">${nodeId}</span>`;
                
                const statusCell = newRow.insertCell(2);
                statusCell.innerText = "200 OK";

                if (table.rows.length > 10) {
                    table.deleteRow(10);
                }
            }

            function toggleAutoRefresh(enable) {
                if (enable) {
                    fetchData(); // Run one immediately
                    intervalId = setInterval(fetchData, 1000); // Run every 1 second
                    document.getElementById('startBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'inline-block';
                } else {
                    clearInterval(intervalId);
                    document.getElementById('startBtn').style.display = 'inline-block';
                    document.getElementById('stopBtn').style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)