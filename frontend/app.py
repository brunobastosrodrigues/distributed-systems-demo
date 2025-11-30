from flask import Flask
import requests

app = Flask(__name__)

@app.route('/')
def home():
    try:
        # We request the Load Balancer, NOT the backend directly
        # This demonstrates Location Transparency
        response = requests.get('http://loadbalancer:80/api', timeout=2)
        data = response.json()
        
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding: 20px;">
            <h1>Distributed System Dashboard</h1>
            <h3 style="color: green;">Status: Online</h3>
            <p><b>Response served by Container ID:</b> {data['served_by_node']}</p>
            <p><b>Service Type:</b> {data['architecture']}</p>
            <hr>
            <p><i>Refresh this page to observe the Load Balancer distributing traffic.</i></p>
        </div>
        """
    except Exception as e:
        return f"<h1 style='color: red'>Backend Unavailable</h1><p>{e}</p>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)