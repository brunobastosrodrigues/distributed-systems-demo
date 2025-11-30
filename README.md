# 🌐 Distributed Systems Characteristics Demo

A live, interactive laboratory to demonstrate the fundamental characteristics of distributed systems using Docker.

This demo simulates a complete architecture: **Client → Load Balancer → Heterogeneous Backend Cluster**.

## 📋 Prerequisites

* **Docker** (Desktop or Engine)
* **Docker Compose**
* **Git**

---

## 🚀 Quick Start

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd distributed-systems-demo
    ```

2.  **Make scripts executable (Linux/Mac/Codespaces):**
    ```bash
    chmod +x start.sh reset.sh
    ```

3.  **Start the System:**
    ```bash
    ./start.sh
    ```
    *This will build the images, fix permissions, and launch the cluster.*

4.  **Access the Dashboard:**
    * **Local Machine:** [http://localhost:9000](http://localhost:9000)
    * **VS Code / Codespaces:** Go to the **Ports** tab and click the 🌐 icon next to port **9000**.
    * **VM/Network:** `http://<VM-IP-ADDRESS>:9000`

---

## 🎓 Lecture Guide: Mapping Concepts to Demo

Use the **Control Plane** in the dashboard to demonstrate the 6 Key Characteristics:

### 1. Transparency & 4. Openness
* **Action:** Click **"Start Traffic"**.
* **Observation:** The Client connects to the Load Balancer, never directly to the Backend nodes. The system appears as a single unit.
* **Concept:** The complexity of the backend is hidden from the user (Transparency). Components communicate using standard JSON (Openness).

### 2. Scalability
* **Action:** Click **"Add Resources (+ Python Node)"**.
* **Observation:** New nodes appear in the grid instantly. Traffic is automatically distributed to them.
* **Concept:** Horizontal Scalability. We added capacity without restarting the system.

### 3. Fault Tolerance
* **Action:** Click **"Simulate Failure"**.
* **Observation:** A node crashes (disappears/red), but the traffic logs continue with `200 OK`.
* **Concept:** The Load Balancer detects the failure and routes traffic to healthy nodes. The system tolerates partial failure.

### 2. Heterogeneity
* **Action:** Click **"Add Node.js Node"**.
* **Observation:** A new node with a **JS** icon appears.
* **Concept:** Different technologies (Python and Node.js) running on different operating systems (Debian vs Alpine) working together seamlessly.

### 6. Security
* **Action:** Click **"Security Audit"**.
* **Observation:** Access is Denied.
* **Concept:** The backend nodes are isolated in a private network (`internal: true`). Only the Load Balancer can access them.

---

## 🧹 Cleanup / Reset

To wipe the slate clean (kill all auto-scaled nodes) and prepare for the next demo:

```bash
./reset.sh