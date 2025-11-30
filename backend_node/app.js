const http = require('http');
const os = require('os');

const server = http.createServer((req, res) => {
    if (req.url === '/api') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            message: "Hello from the Node.js backend!",
            served_by_node: os.hostname(),
            architecture: "NodeJS Backend" // Different architecture!
        }));
    } else {
        res.writeHead(404);
        res.end();
    }
});

server.listen(5000, () => {
    console.log('Node.js backend listening on port 5000');
});