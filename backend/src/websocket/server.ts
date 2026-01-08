import { Server } from "socket.io";
import { bufferBehaviorEvent } from "../config/redis";
import {
  handleBehaviorEvent,
  handleBatchBehaviorEvents,
  handleSessionStart,
  handleSessionEnd,
} from "./behaviorStream";

let io: Server;

export const initializeWebSocket = (port: number) => {
  io = new Server(port, {
    cors: {
      origin: process.env.FRONTEND_URL || "http://localhost:3002",
      methods: ["GET", "POST"],
      credentials: true,
    },
  });

  // Main connection handler
  io.on("connection", (socket) => {
    console.log(`✓ WebSocket client connected: ${socket.id}`);

    // Handle disconnection
    socket.on("disconnect", (reason) => {
      console.log(`✗ WebSocket client disconnected: ${socket.id} (${reason})`);
    });

    // Ping/pong for connection testing
    socket.on("ping", () => {
      socket.emit("pong", { timestamp: Date.now() });
    });

    // Join student-specific room
    socket.on("join", (data: { studentId: string; sessionId: string }) => {
      const { studentId, sessionId } = data;
      socket.join(`student:${studentId}`);
      socket.join(`session:${sessionId}`);
      console.log(`Student ${studentId} joined room (session: ${sessionId})`);
      socket.emit("joined", { studentId, sessionId });
    });

    // Behavior tracking event handlers
    socket.on("behavior:event", (data) => handleBehaviorEvent(socket, data));
    socket.on("behavior:batch", (data) =>
      handleBatchBehaviorEvents(socket, data)
    );
    socket.on("session:start", (data) => handleSessionStart(socket, data));
    socket.on("session:end", (data) => handleSessionEnd(socket, data));
  });

  // Behavior tracking namespace
  const behaviorNamespace = io.of("/behavior");
  behaviorNamespace.on("connection", (socket) => {
    console.log(`✓ Behavior tracking client connected: ${socket.id}`);

    socket.on("track", async (data) => {
      const { sessionId, eventType, eventData } = data;
      await bufferBehaviorEvent(sessionId, {
        eventType,
        eventData,
        timestamp: Date.now(),
      });
    });
  });

  // Notifications namespace (for agent interventions)
  const notificationsNamespace = io.of("/notifications");
  notificationsNamespace.on("connection", (socket) => {
    console.log(`✓ Notifications client connected: ${socket.id}`);

    socket.on("subscribe", (data: { studentId: string }) => {
      socket.join(`student:${data.studentId}`);
      console.log(`Student ${data.studentId} subscribed to notifications`);
    });
  });

  console.log(`🔌 WebSocket Server: ws://localhost:${port}`);
  console.log(`🔌 Behavior Namespace: ws://localhost:${port}/behavior`);
  console.log(
    `🔌 Notifications Namespace: ws://localhost:${port}/notifications`
  );
};

// Export function to send notifications to students
export const sendNotificationToStudent = (
  studentId: string,
  notification: any
) => {
  if (io) {
    io.of("/notifications")
      .to(`student:${studentId}`)
      .emit("notification", notification);
  }
};

export { io };
