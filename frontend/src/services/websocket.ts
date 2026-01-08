import { io, Socket } from "socket.io-client";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:3001";

class WebSocketClient {
  private socket: Socket | null = null;
  private behaviorSocket: Socket | null = null;
  private notificationsSocket: Socket | null = null;

  // Initialize main connection
  connect(studentId?: string, sessionId?: string): Socket {
    if (this.socket?.connected) {
      return this.socket;
    }

    this.socket = io(WS_URL, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    });

    this.socket.on("connect", () => {
      console.log("✓ WebSocket connected");

      if (studentId && sessionId) {
        this.socket?.emit("join", { studentId, sessionId });
      }
    });

    this.socket.on("disconnect", (reason) => {
      console.log("✗ WebSocket disconnected:", reason);
    });

    this.socket.on("connect_error", (error) => {
      console.error("WebSocket connection error:", error);
    });

    this.socket.on("joined", (data) => {
      console.log("Joined room:", data);
    });

    this.socket.on("pong", (data) => {
      console.log("Pong received:", data);
    });

    return this.socket;
  }

  // Initialize behavior tracking namespace
  connectBehavior(): Socket {
    if (this.behaviorSocket?.connected) {
      return this.behaviorSocket;
    }

    this.behaviorSocket = io(`${WS_URL}/behavior`, {
      transports: ["websocket"],
    });

    this.behaviorSocket.on("connect", () => {
      console.log("✓ Behavior tracking connected");
    });

    return this.behaviorSocket;
  }

  // Initialize notifications namespace
  connectNotifications(studentId: string): Socket {
    if (this.notificationsSocket?.connected) {
      return this.notificationsSocket;
    }

    this.notificationsSocket = io(`${WS_URL}/notifications`, {
      transports: ["websocket"],
    });

    this.notificationsSocket.on("connect", () => {
      console.log("✓ Notifications connected");
      this.notificationsSocket?.emit("subscribe", { studentId });
    });

    this.notificationsSocket.on("notification", (notification) => {
      console.log("Notification received:", notification);
      // Emit custom event for React components to listen to
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("agent-notification", { detail: notification })
        );
      }
    });

    return this.notificationsSocket;
  }

  // Send behavioral event
  trackBehavior(sessionId: string, eventType: string, eventData: any) {
    if (!this.behaviorSocket?.connected) {
      this.connectBehavior();
    }

    this.behaviorSocket?.emit("track", {
      sessionId,
      eventType,
      eventData,
      timestamp: Date.now(),
    });
  }

  // Send behavioral event via main connection
  sendBehaviorEvent(sessionId: string, eventType: string, eventData: any) {
    this.socket?.emit("behavior:event", {
      sessionId,
      eventType,
      eventData,
      timestamp: Date.now(),
    });
  }

  // Send batch of behavioral events
  sendBehaviorBatch(events: any[]) {
    if (!this.socket?.connected) {
      console.warn("WebSocket not connected, queuing events");
      return;
    }

    this.socket.emit("behavior:batch", {
      events,
    });
  }

  // Ping server
  ping() {
    this.socket?.emit("ping");
  }

  // Disconnect all connections
  disconnect() {
    this.socket?.disconnect();
    this.behaviorSocket?.disconnect();
    this.notificationsSocket?.disconnect();

    this.socket = null;
    this.behaviorSocket = null;
    this.notificationsSocket = null;

    console.log("All WebSocket connections closed");
  }

  // Get socket instances
  getSocket(): Socket | null {
    return this.socket;
  }

  getBehaviorSocket(): Socket | null {
    return this.behaviorSocket;
  }

  getNotificationsSocket(): Socket | null {
    return this.notificationsSocket;
  }
}

// Export singleton instance
const wsClient = new WebSocketClient();
export default wsClient;
