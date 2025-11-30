from flask import Flask, jsonify
import socket
import os

app = Flask(__name__)

@app.route('/api')
def hello():
    # Returns the container ID (Hostname) to prove where the response came from
    return jsonify({
        "message": "Hello from the distributed backend!",
        "served_by_node": socket.gethostname(),
        "architecture": "Python/Flask Backend"
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)