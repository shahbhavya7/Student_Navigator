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

// Rate limiting map: sessionId -> { count, resetTime }
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const RATE_LIMIT_WINDOW = 1000; // 1 second
const RATE_LIMIT_MAX_EVENTS = 100; // Max events per second per session

// Circuit breaker for Redis failures
let redisCircuitOpen = false;
let circuitOpenTime = 0;
const CIRCUIT_BREAKER_TIMEOUT = 30000; // 30 seconds
const inMemoryFallbackQueue: NormalizedBehaviorEvent[] = [];

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

    // Initialize session in Redis
    const sessionKey = `session:${sessionId}`;
    await redis.hset(sessionKey, {
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
