// src/socket.js
// Reusable pure Javascript WebSocket manager featuring auto-reconnection logic.
// Buffers messages locally while offline and drains buffer upon reconnection.

export class SocketManager {
  constructor(url, onMessageCallback, onConnectCallback) {
    this.url = url;
    this.ws = null;
    this.onMessage = onMessageCallback;
    this.onConnect = onConnectCallback;
    this.retryCount = 0;
    this.messageQueue = [];
    this.connect();
  }

  // Establishes connection using backoff strategy on failure.
  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.retryCount = 0;
      this.flushQueue();
      if (this.onConnect) this.onConnect(true);
    };
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (this.onMessage) this.onMessage(data);
    };
    this.ws.onclose = () => {
      if (this.onConnect) this.onConnect(false);
      this.scheduleReconnect();
    };
  }

  // Schedules the recursive reconnection attempt securely using exponential math.
  scheduleReconnect() {
    const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
    this.retryCount++;
    setTimeout(() => this.connect(), delay);
  }

  // Pushes a serialized action down the socket tube if alive, otherwise queues it.
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
    }
  }

  // Rapid-fires any locked up messages that were held while disconnected.
  flushQueue() {
    while (this.messageQueue.length > 0 && this.ws.readyState === WebSocket.OPEN) {
      const msg = this.messageQueue.shift();
      this.ws.send(JSON.stringify(msg));
    }
  }
}
