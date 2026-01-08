import redis from "../config/redis";

/**
 * Buffer statistics interface
 */
export interface BufferStats {
  totalSessions: number;
  totalEvents: number;
  sessionDetails: Array<{
    sessionId: string;
    eventCount: number;
  }>;
}

/**
 * Get all active session IDs with buffered events
 */
export async function getActiveSessionIds(): Promise<string[]> {
  try {
    const keys = await redis.keys("behavior:*");
    const sessionIds = keys.map((key) => key.replace("behavior:", ""));
    return sessionIds;
  } catch (error) {
    console.error("Error getting active session IDs:", error);
    return [];
  }
}

/**
 * Get event count for a specific session
 */
export async function getSessionEventCount(sessionId: string): Promise<number> {
  try {
    const key = `behavior:${sessionId}`;
    const count = await redis.llen(key);
    return count;
  } catch (error) {
    console.error(`Error getting event count for session ${sessionId}:`, error);
    return 0;
  }
}

/**
 * Force flush events for a specific session to database
 */
export async function flushSessionEvents(sessionId: string): Promise<void> {
  try {
    await redis.sadd("sessions:pending_flush", sessionId);
    await redis.expire("sessions:pending_flush", 300); // 5 minutes
    console.log(`✅ Session ${sessionId} marked for immediate flush`);
  } catch (error) {
    console.error(`Error flushing session ${sessionId}:`, error);
    throw error;
  }
}

/**
 * Get buffer statistics across all sessions
 */
export async function getBufferStats(): Promise<BufferStats> {
  try {
    const sessionIds = await getActiveSessionIds();
    const sessionDetails = await Promise.all(
      sessionIds.map(async (sessionId) => ({
        sessionId,
        eventCount: await getSessionEventCount(sessionId),
      }))
    );

    const totalEvents = sessionDetails.reduce(
      (sum, s) => sum + s.eventCount,
      0
    );

    return {
      totalSessions: sessionIds.length,
      totalEvents,
      sessionDetails,
    };
  } catch (error) {
    console.error("Error getting buffer stats:", error);
    return {
      totalSessions: 0,
      totalEvents: 0,
      sessionDetails: [],
    };
  }
}

/**
 * Clean up expired sessions
 */
export async function cleanupExpiredSessions(): Promise<number> {
  try {
    const sessionKeys = await redis.keys("session:*");
    let cleanedCount = 0;

    for (const key of sessionKeys) {
      const ttl = await redis.ttl(key);

      // If TTL is -1 (no expiry set) or -2 (key doesn't exist)
      if (ttl === -1) {
        await redis.expire(key, 86400); // Set 24 hour expiry
      } else if (ttl === -2) {
        cleanedCount++;
      }
    }

    // Clean up orphaned behavior buffers (sessions that no longer exist)
    const behaviorKeys = await redis.keys("behavior:*");
    for (const key of behaviorKeys) {
      const sessionId = key.replace("behavior:", "");
      const sessionExists = await redis.exists(`session:${sessionId}`);

      if (!sessionExists) {
        await redis.del(key);
        cleanedCount++;
        console.log(`🧹 Cleaned up orphaned buffer: ${key}`);
      }
    }

    if (cleanedCount > 0) {
      console.log(`🧹 Cleaned up ${cleanedCount} expired/orphaned sessions`);
    }

    return cleanedCount;
  } catch (error) {
    console.error("Error cleaning up expired sessions:", error);
    return 0;
  }
}

/**
 * Get session metadata
 */
export async function getSessionMetadata(
  sessionId: string
): Promise<any | null> {
  try {
    const key = `session:${sessionId}`;
    const data = await redis.hgetall(key);

    if (!data || Object.keys(data).length === 0) {
      return null;
    }

    return {
      studentId: data.studentId,
      startTime: parseInt(data.startTime),
      lastActivity: parseInt(data.lastActivity),
      socketId: data.socketId,
      metadata: data.metadata ? JSON.parse(data.metadata) : {},
      endTime: data.endTime ? parseInt(data.endTime) : null,
      status: data.status || "active",
    };
  } catch (error) {
    console.error(`Error getting session metadata for ${sessionId}:`, error);
    return null;
  }
}

/**
 * Update session last activity timestamp
 */
export async function updateSessionActivity(sessionId: string): Promise<void> {
  try {
    const key = `session:${sessionId}`;
    await redis.hset(key, "lastActivity", Date.now().toString());
  } catch (error) {
    console.error(`Error updating session activity for ${sessionId}:`, error);
  }
}

/**
 * Get metrics for a session
 */
export async function getSessionMetrics(
  sessionId: string
): Promise<{ eventCount: number } | null> {
  try {
    const key = `metrics:${sessionId}`;
    const eventCount = await redis.hget(key, "eventCount");

    if (!eventCount) {
      return null;
    }

    return {
      eventCount: parseInt(eventCount),
    };
  } catch (error) {
    console.error(`Error getting session metrics for ${sessionId}:`, error);
    return null;
  }
}
