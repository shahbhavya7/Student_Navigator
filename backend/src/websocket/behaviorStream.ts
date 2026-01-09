import { Socket } from "socket.io";
import {
  validateBehaviorEvent,
  normalizeBehaviorEvent,
  RawBehaviorEvent,
  NormalizedBehaviorEvent,
  BehaviorEventType,
} from "../models/BehaviorEvent";
import { bufferBehaviorEvent, getBehaviorEvents } from "../config/redis";
import redis from "../config/redis";
import { pythonBridge } from "../services/pythonBridge";
import { redisPubSub } from "../services/redisPubSub";
import prisma from "../config/database";

// Rate limiting map: sessionId -> { count, resetTime }
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW = 1000; // 1 second
const RATE_LIMIT_MAX_EVENTS = 100; // Max events per second per session

// Circuit breaker for Redis failures
let redisCircuitOpen = false;
let circuitOpenTime = 0;
const CIRCUIT_BREAKER_TIMEOUT = 30000; // 30 seconds
const inMemoryFallbackQueue: NormalizedBehaviorEvent[] = [];

// CLR update throttling: studentId -> lastUpdateTime
const clrUpdateThrottle = new Map<string, number>();
const CLR_UPDATE_INTERVAL = 30000; // 30 seconds between updates per student

// Track connected clients by student ID for targeted broadcasts
const studentConnections = new Map<string, Set<string>>(); // studentId -> Set<socketId>

/**
 * Check rate limit for a session
 */
function checkRateLimit(sessionId: string): boolean {
  const now = Date.now();
  const limit = rateLimitMap.get(sessionId);

  if (!limit || now > limit.resetTime) {
    rateLimitMap.set(sessionId, {
      count: 1,
      resetTime: now + RATE_LIMIT_WINDOW,
    });
    return true;
  }

  if (limit.count >= RATE_LIMIT_MAX_EVENTS) {
    return false;
  }

  limit.count++;
  return true;
}

/**
 * Check circuit breaker status
 */
function checkCircuitBreaker(): boolean {
  if (!redisCircuitOpen) return true;

  const now = Date.now();
  if (now - circuitOpenTime > CIRCUIT_BREAKER_TIMEOUT) {
    console.log("🔄 Circuit breaker: Attempting to reconnect to Redis");
    redisCircuitOpen = false;
    return true;
  }

  return false;
}

/**
 * Open circuit breaker on Redis failure
 */
function openCircuitBreaker(): void {
  if (!redisCircuitOpen) {
    console.error(
      "⚠️ Circuit breaker opened: Redis unavailable, using in-memory fallback"
    );
    redisCircuitOpen = true;
    circuitOpenTime = Date.now();
  }
}

/**
 * Buffer event to Redis or fallback queue
 */
async function bufferEvent(event: NormalizedBehaviorEvent): Promise<void> {
  if (!checkCircuitBreaker()) {
    // Circuit breaker is open, use in-memory fallback
    inMemoryFallbackQueue.push(event);

    // Limit fallback queue size
    if (inMemoryFallbackQueue.length > 10000) {
      inMemoryFallbackQueue.shift();
    }
    return;
  }

  try {
    await bufferBehaviorEvent(event.sessionId, event);

    // If we successfully buffered and have fallback items, try to flush them
    if (inMemoryFallbackQueue.length > 0) {
      console.log(
        `🔄 Flushing ${inMemoryFallbackQueue.length} events from fallback queue`
      );
      const eventsToFlush = [...inMemoryFallbackQueue];
      inMemoryFallbackQueue.length = 0;

      for (const fallbackEvent of eventsToFlush) {
        await bufferBehaviorEvent(fallbackEvent.sessionId, fallbackEvent);
      }
    }
  } catch (error) {
    console.error("Error buffering event to Redis:", error);
    openCircuitBreaker();
    inMemoryFallbackQueue.push(event);
  }
}

/**
 * Track event count and buffer size in Redis
 */
async function trackEventMetrics(sessionId: string): Promise<void> {
  try {
    const key = `metrics:${sessionId}`;
    await redis.hincrby(key, "eventCount", 1);
    await redis.expire(key, 3600); // 1 hour TTL
  } catch (error) {
    // Silently fail metrics tracking
  }
}

/**
 * Main handler for single behavior event
 */
export async function handleBehaviorEvent(
  socket: Socket,
  data: any
): Promise<void> {
  try {
    // Check rate limit
    if (!checkRateLimit(data.sessionId)) {
      socket.emit("behavior:ack", {
        success: false,
        error: "RATE_LIMIT_EXCEEDED",
        message: "Too many events per second",
      });
      return;
    }

    // Validate event structure
    if (!validateBehaviorEvent(data)) {
      socket.emit("behavior:ack", {
        success: false,
        error: "VALIDATION_ERROR",
        message: "Invalid event structure",
      });
      console.warn("Validation failed for event:", data);
      return;
    }

    // Enrich with server-side metadata
    const enrichedData: RawBehaviorEvent = {
      ...data,
      metadata: {
        ...data.metadata,
        serverReceivedAt: Date.now(),
        socketId: socket.id,
      },
    };

    // Normalize event
    const normalizedEvent = normalizeBehaviorEvent(enrichedData);

    // Buffer to Redis
    await bufferEvent(normalizedEvent);

    // Track metrics
    await trackEventMetrics(normalizedEvent.sessionId);

    // Send acknowledgment
    socket.emit("behavior:ack", {
      success: true,
      eventId: normalizedEvent.id,
      serverTimestamp: normalizedEvent.serverTimestamp,
    });

    // Log high priority events
    if (
      normalizedEvent.priority === "CRITICAL" ||
      normalizedEvent.priority === "HIGH"
    ) {
      console.log(
        `📊 ${normalizedEvent.priority} event: ${normalizedEvent.eventType} from session ${normalizedEvent.sessionId}`
      );
    }
  } catch (error) {
    console.error("Error handling behavior event:", error);
    socket.emit("behavior:ack", {
      success: false,
      error: "SERVER_ERROR",
      message: "Internal server error",
    });
  }
}

/**
 * Handler for batch behavior events
 */
export async function handleBatchBehaviorEvents(
  socket: Socket,
  data: { events: any[] }
): Promise<void> {
  try {
    if (!data.events || !Array.isArray(data.events)) {
      socket.emit("behavior:batch:ack", {
        success: false,
        error: "INVALID_BATCH",
        message: "Events must be an array",
      });
      return;
    }

    if (data.events.length === 0) {
      socket.emit("behavior:batch:ack", {
        success: true,
        processed: 0,
        failed: 0,
      });
      return;
    }

    // Check rate limit for first event's session
    const sessionId = data.events[0]?.sessionId;
    if (!sessionId || !checkRateLimit(sessionId)) {
      socket.emit("behavior:batch:ack", {
        success: false,
        error: "RATE_LIMIT_EXCEEDED",
        message: "Too many events per second",
      });
      return;
    }

    const results = {
      processed: 0,
      failed: 0,
      errors: [] as string[],
    };

    // Process each event in batch
    for (const event of data.events) {
      try {
        // Validate
        if (!validateBehaviorEvent(event)) {
          results.failed++;
          results.errors.push(
            `Invalid event structure for event at index ${
              results.processed + results.failed
            }`
          );
          continue;
        }

        // Enrich with metadata
        const enrichedData: RawBehaviorEvent = {
          ...event,
          metadata: {
            ...event.metadata,
            serverReceivedAt: Date.now(),
            socketId: socket.id,
            batch: true,
          },
        };

        // Normalize
        const normalizedEvent = normalizeBehaviorEvent(enrichedData);

        // Buffer
        await bufferEvent(normalizedEvent);

        // Track metrics
        await trackEventMetrics(normalizedEvent.sessionId);

        results.processed++;
      } catch (error) {
        results.failed++;
        results.errors.push(
          `Error processing event: ${
            error instanceof Error ? error.message : "Unknown error"
          }`
        );
      }
    }

    // Send batch acknowledgment
    socket.emit("behavior:batch:ack", {
      success: results.failed === 0,
      processed: results.processed,
      failed: results.failed,
      errors:
        results.errors.length > 0 ? results.errors.slice(0, 5) : undefined, // Limit error messages
    });

    console.log(
      `📦 Batch processed: ${results.processed} successful, ${results.failed} failed for session ${sessionId}`
    );
  } catch (error) {
    console.error("Error handling batch behavior events:", error);
    socket.emit("behavior:batch:ack", {
      success: false,
      error: "SERVER_ERROR",
      message: "Internal server error",
    });
  }
}

/**
 * Handler for session start
 */
export async function handleSessionStart(
  socket: Socket,
  data: { sessionId: string; studentId: string; metadata?: any }
): Promise<void> {
  try {
    const { sessionId, studentId, metadata } = data;

    if (!sessionId || !studentId) {
      socket.emit("session:start:ack", {
        success: false,
        error: "MISSING_FIELDS",
        message: "sessionId and studentId are required",
      });
      return;
    }

    // Ensure student exists in database (auto-create for testing)
    const studentExists = await prisma.student.findUnique({
      where: { id: studentId },
    });

    if (!studentExists) {
      await prisma.student.create({
        data: {
          id: studentId,
          email: `${studentId}@temp.local`,
          passwordHash: "temp",
          firstName: "Test",
          lastName: "Student",
        },
      });
      console.log(`✨ Auto-created student: ${studentId}`);
    }

    // Create session in PostgreSQL
    try {
      await prisma.session.create({
        data: {
          id: sessionId,
          studentId: studentId,
          startTime: new Date(),
          deviceInfo: metadata || {},
        },
      });
    } catch (dbError: any) {
      // If session already exists (P2002), that's OK - session might have been restarted
      if (dbError.code !== "P2002") {
        throw dbError;
      }
      console.log(`Session ${sessionId} already exists in database`);
    }

    // Initialize session in Redis
    const sessionKey = `session:${sessionId}`;
    await redis.hmset(sessionKey, {
      studentId,
      startTime: Date.now().toString(),
      lastActivity: Date.now().toString(),
      socketId: socket.id,
      metadata: JSON.stringify(metadata || {}),
    });
    await redis.expire(sessionKey, 86400); // 24 hours TTL

    // Initialize event counter
    await redis.set(`metrics:${sessionId}:eventCount`, 0, "EX", 3600);

    socket.emit("session:start:ack", {
      success: true,
      sessionId,
      serverTimestamp: Date.now(),
    });

    console.log(`🎬 Session started: ${sessionId} for student ${studentId}`);
  } catch (error) {
    console.error("Error handling session start:", error);
    socket.emit("session:start:ack", {
      success: false,
      error: "SERVER_ERROR",
      message: "Internal server error",
    });
  }
}

/**
 * Handler for session end - triggers immediate flush
 */
export async function handleSessionEnd(
  socket: Socket,
  data: { sessionId: string }
): Promise<void> {
  try {
    const { sessionId } = data;

    if (!sessionId) {
      socket.emit("session:end:ack", {
        success: false,
        error: "MISSING_SESSION_ID",
        message: "sessionId is required",
      });
      return;
    }

    // Get buffered events
    const events = await getBehaviorEvents(sessionId);
    const eventCount = events.length;

    // Mark session for immediate processing
    await redis.sadd("sessions:pending_flush", sessionId);
    await redis.expire("sessions:pending_flush", 300); // 5 minutes

    // Update session end time
    const sessionKey = `session:${sessionId}`;
    await redis.hset(sessionKey, {
      endTime: Date.now().toString(),
      status: "ended",
    });

    // Trigger Python agent workflow
    try {
      const studentId = socket.data.studentId || "demo-student";
      await pythonBridge.triggerAgentWorkflow(
        studentId,
        sessionId,
        "session_end"
      );

      // Also publish to Redis pub/sub for Python backend
      await redisPubSub.publishEvent("sessions:ended", {
        type: "session_ended",
        student_id: studentId,
        session_id: sessionId,
        timestamp: Date.now(),
      });
    } catch (error) {
      console.error("Error triggering agent workflow:", error);
      // Don't fail the session end if agent trigger fails
    }

    socket.emit("session:end:ack", {
      success: true,
      sessionId,
      eventsBuffered: eventCount,
      message: "Session ended, events will be processed shortly",
    });

    console.log(
      `🏁 Session ended: ${sessionId} with ${eventCount} buffered events`
    );
  } catch (error) {
    console.error("Error handling session end:", error);
    socket.emit("session:end:ack", {
      success: false,
      error: "SERVER_ERROR",
      message: "Internal server error",
    });
  }
}

/**
 * Get fallback queue size for monitoring
 */
export function getFallbackQueueSize(): number {
  return inMemoryFallbackQueue.length;
}

/**
 * Get circuit breaker status
 */
export function getCircuitBreakerStatus(): { open: boolean; since?: number } {
  return {
    open: redisCircuitOpen,
    since: redisCircuitOpen ? circuitOpenTime : undefined,
  };
}

/**
 * Register student connection for targeted CLR broadcasts
 */
export function registerStudentConnection(
  studentId: string,
  socketId: string
): void {
  if (!studentConnections.has(studentId)) {
    studentConnections.set(studentId, new Set());
  }
  studentConnections.get(studentId)!.add(socketId);
  console.log(`📡 Student ${studentId} connected on socket ${socketId}`);
}

/**
 * Unregister student connection
 */
export function unregisterStudentConnection(
  studentId: string,
  socketId: string
): void {
  const sockets = studentConnections.get(studentId);
  if (sockets) {
    sockets.delete(socketId);
    if (sockets.size === 0) {
      studentConnections.delete(studentId);
    }
  }
}

/**
 * Broadcast CLR update to specific student
 */
export function broadcastCLRUpdate(
  io: any,
  studentId: string,
  clrData: any
): void {
  // Check throttling
  const now = Date.now();
  const lastUpdate = clrUpdateThrottle.get(studentId);

  if (lastUpdate && now - lastUpdate < CLR_UPDATE_INTERVAL) {
    console.log(`⏱️ CLR update throttled for student ${studentId}`);
    return;
  }

  // Update throttle timestamp
  clrUpdateThrottle.set(studentId, now);

  // Get connected sockets for this student
  const sockets = studentConnections.get(studentId);

  if (!sockets || sockets.size === 0) {
    console.log(`📭 No active connections for student ${studentId}`);
    return;
  }

  // Broadcast to all student's sockets
  const message = {
    type: "COGNITIVE_LOAD_UPDATE",
    data: {
      studentId: clrData.student_id,
      sessionId: clrData.session_id,
      cognitiveLoadScore: clrData.cognitive_load_score,
      mentalFatigueLevel: clrData.mental_fatigue_level,
      detectedPatterns: clrData.detected_patterns || [],
      recommendations: clrData.recommendations || [],
      timestamp: clrData.timestamp || Date.now(),
    },
  };

  sockets.forEach((socketId) => {
    io.to(socketId).emit("clr:update", message);
  });

  console.log(
    `📊 CLR update broadcasted to ${sockets.size} connection(s) for student ${studentId}`
  );
}
