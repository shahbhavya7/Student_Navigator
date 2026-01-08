import Redis from "ioredis";

const redis = new Redis(process.env.REDIS_URL || "redis://localhost:6379", {
  retryStrategy: (times) => {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  maxRetriesPerRequest: 3,
});

redis.on("connect", () => {
  console.log("✓ Redis connected successfully");
});

redis.on("error", (err) => {
  console.error("✗ Redis connection error:", err);
});

// Helper functions for cognitive load time-series data
export const recordCognitiveLoad = async (
  studentId: string,
  score: number,
  timestamp?: number
): Promise<void> => {
  const key = `clr:${studentId}`;
  const ts = timestamp || Date.now();

  try {
    // Store in a sorted set with timestamp as score
    await redis.zadd(key, ts, `${ts}:${score}`);
    // Set expiration to 30 days
    await redis.expire(key, 30 * 24 * 60 * 60);

    // Remove entries older than 30 days
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
    await redis.zremrangebyscore(key, 0, thirtyDaysAgo);
  } catch (error) {
    console.error("Error recording cognitive load:", error);
  }
};

export const getCognitiveLoadHistory = async (
  studentId: string,
  startTime: number,
  endTime: number
): Promise<Array<{ timestamp: number; score: number }>> => {
  const key = `clr:${studentId}`;

  try {
    // Query the sorted set by timestamp range
    const results = await redis.zrangebyscore(key, startTime, endTime);
    return results.map((item) => {
      const [timestamp, score] = item.split(":");
      return { timestamp: parseInt(timestamp), score: parseFloat(score) };
    });
  } catch (error) {
    console.error("Error getting cognitive load history:", error);
    return [];
  }
};

export const bufferBehaviorEvent = async (
  sessionId: string,
  event: any
): Promise<void> => {
  const key = `behavior:${sessionId}`;

  try {
    await redis.lpush(key, JSON.stringify(event));
    await redis.expire(key, 60 * 60); // 1 hour TTL
  } catch (error) {
    console.error("Error buffering behavior event:", error);
  }
};

export const getBehaviorEvents = async (sessionId: string): Promise<any[]> => {
  const key = `behavior:${sessionId}`;

  try {
    const events = await redis.lrange(key, 0, -1);
    return events.map((event) => JSON.parse(event));
  } catch (error) {
    console.error("Error getting behavior events:", error);
    return [];
  }
};

export default redis;
