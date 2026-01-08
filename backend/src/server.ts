import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import dotenv from "dotenv";
import prisma from "./config/database";
import redis from "./config/redis";
import { initializeWebSocket } from "./websocket/server";
import { batchProcessor } from "./services/behaviorBatchProcessor";
import { redisPubSub } from "./services/redisPubSub";
import { getBufferStats } from "./utils/redisHelpers";
import {
  getFallbackQueueSize,
  getCircuitBreakerStatus,
} from "./websocket/behaviorStream";

// Load environment variables
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;
const WS_PORT = process.env.WS_PORT || 3001;

// Middleware
app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:3002",
    credentials: true,
  })
);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  console.log(`${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get("/api/health", async (req: Request, res: Response) => {
  try {
    // Check PostgreSQL connection
    await prisma.$queryRaw`SELECT 1`;
    const postgresStatus = "connected";

    // Check Redis connection
    await redis.ping();
    const redisStatus = "connected";

    // Get batch processor status
    const processorStatus = batchProcessor.getStatus();
    const bufferStats = await getBufferStats();
    const circuitBreaker = getCircuitBreakerStatus();

    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      services: {
        postgres: postgresStatus,
        redis: redisStatus,
        batchProcessor: {
          running: processorStatus.isRunning,
          processing: processorStatus.isProcessing,
        },
        behaviorTracking: {
          bufferedSessions: bufferStats.totalSessions,
          bufferedEvents: bufferStats.totalEvents,
          fallbackQueueSize: getFallbackQueueSize(),
          circuitBreaker: circuitBreaker,
        },
      },
    });
  } catch (error) {
    console.error("Health check failed:", error);
    res.status(503).json({
      status: "error",
      timestamp: new Date().toISOString(),
      services: {
        postgres: "disconnected",
        redis: "disconnected",
      },
    });
  }
});

// Placeholder API routes
app.get("/api/students", async (req: Request, res: Response) => {
  try {
    const students = await prisma.student.findMany({
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        createdAt: true,
      },
    });
    res.json(students);
  } catch (error) {
    console.error("Error fetching students:", error);
    res.status(500).json({ error: "Failed to fetch students" });
  }
});

app.post("/api/students", async (req: Request, res: Response) => {
  try {
    const { email, firstName, lastName, passwordHash } = req.body;

    if (!email || !firstName || !lastName || !passwordHash) {
      return res.status(400).json({ error: "Missing required fields" });
    }

    const student = await prisma.student.create({
      data: {
        email,
        firstName,
        lastName,
        passwordHash,
      },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        createdAt: true,
      },
    });

    res.status(201).json(student);
  } catch (error) {
    console.error("Error creating student:", error);
    res.status(500).json({ error: "Failed to create student" });
  }
});

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error("Error:", err);
  res.status(500).json({ error: "Internal server error" });
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: "Not found" });
});

// Start HTTP server
app.listen(PORT, () => {
  console.log("🚀 Server started successfully");
  console.log(`📡 HTTP Server: http://localhost:${PORT}`);
  console.log(`🏥 Health Check: http://localhost:${PORT}/api/health`);
});

// Initialize WebSocket server
initializeWebSocket(Number(WS_PORT));

// Initialize Redis pub/sub for agent communication
redisPubSub.initialize().catch((error) => {
  console.error("Failed to initialize Redis pub/sub:", error);
});

// Start batch processor
if (process.env.ENABLE_BEHAVIOR_TRACKING !== "false") {
  batchProcessor.start();
  console.log("✅ Behavior batch processor started");
}

// Graceful shutdown
process.on("SIGINT", async () => {
  // Cleanup Redis pub/sub
  await redisPubSub.cleanup();

  console.log("\n⏳ Shutting down gracefully...");

  // Stop batch processor
  await batchProcessor.stop();

  await prisma.$disconnect();
  await redis.quit();
  process.exit(0);
});
