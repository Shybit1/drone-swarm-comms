type MessageHandler = (msg: any) => void;

export class SimWebSocket {
  private url: string;
  private ws?: WebSocket;
  private handlers: Set<MessageHandler> = new Set();

  constructor(url?: string) {
    this.url = url || (process.env.REACT_APP_WS_BASE || 'ws://localhost:8081');
  }

  connect() {
    if (this.ws) return;
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      console.log('[WS] connected');
    };
    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        this.handlers.forEach((h) => h(data));
      } catch (err) {
        console.warn('WS parse error', err);
      }
    };
    this.ws.onclose = () => {
      console.log('[WS] closed');
      this.ws = undefined;
      // auto-reconnect after a short delay
      setTimeout(() => this.connect(), 1500);
    };
    this.ws.onerror = (e) => {
      console.warn('[WS] error', e);
    };
  }

  disconnect() {
    if (!this.ws) return;
    this.ws.close();
    this.ws = undefined;
  }

  send(obj: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(obj));
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }
}

const defaultInstance = new SimWebSocket();
export default defaultInstance;
