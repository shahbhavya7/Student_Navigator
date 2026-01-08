import prisma from "../config/database";
import redis, { getBehaviorEvents } from "../config/redis";
import {
  NormalizedBehaviorEvent,
  EventAggregator,
  AggregatedBehaviorData,
} from "../models/BehaviorEvent";

export class BehaviorBatchProcessor {
  private intervalId: NodeJS.Timeout | null = null;
  private isProcessing = false;
  private batchInterval: number;
  private maxEventsPerBatch: number;

  constructor(batchInterval: number = 30000, maxEventsPerBatch: number = 1000) {
    this.batchInterval = batchInterval;
    this.maxEventsPerBatch = maxEventsPerBatch;
  }

  /**
   * Start the batch processor
   */
  start(): void {
    if (this.intervalId) {
      console.warn("⚠️ Batch processor already running");
      return;
    }

    console.log(
      `🚀 Starting batch processor (interval: ${this.batchInterval}ms)`
    );

    // Run immediately on start
    this.processAllSessions().catch((error) => {
      console.error("Error in initial batch processing:", error);
    });

    // Then run on interval
    this.intervalId = setInterval(() => {
      this.processAllSessions().catch((error) => {
        console.error("Error in batch processing:", error);
      });
    }, this.batchInterval);
  }

  /**
   * Stop the batch processor gracefully
   */
  async stop(): Promise<void> {
    if (!this.intervalId) {
      console.warn("⚠️ Batch processor not running");
      return;
    }

    console.log("⏳ Stopping batch processor...");
    clearInterval(this.intervalId);
    this.intervalId = null;

    // Wait for current processing to complete
    while (this.isProcessing) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Final flush of all remaining events
    console.log("🔄 Final flush of remaining events...");
    await this.processAllSessions();

    console.log("✅ Batch processor stopped");
  }

  /**
   * Process all sessions with buffered events
   */
  private async processAllSessions(): Promise<void> {
    if (this.isProcessing) {
      console.log("⏭️ Skipping batch processing - already in progress");
      return;
    }

    this.isProcessing = true;
    const startTime = Date.now();

    try {
      // Get all session IDs with buffered events
      const sessionIds = await this.getActiveSessionIds();

      if (sessionIds.length === 0) {
        return;
      }

      console.log(`📊 Processing ${sessionIds.length} sessions...`);

      let totalProcessed = 0;
      let totalFailed = 0;

      // Process each session
      for (const sessionId of sessionIds) {
        try {
          const processed = await this.processBatch(sessionId);
          totalProcessed += processed;
        } catch (error) {
          totalFailed++;
          console.error(`Error processing session ${sessionId}:`, error);
        }
      }

      // Check for sessions marked for immediate flush
      await this.processPendingFlushSessions();

      const duration = Date.now() - startTime;
      console.log(
        `✅ Batch processing complete: ${totalProcessed} events in ${duration}ms (${totalFailed} failed sessions)`
      );
    } catch (error) {
      console.error("Error in processAllSessions:", error);
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Get all active session IDs with buffered events
   */
  private async getActiveSessionIds(): Promise<string[]> {
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
   * Process sessions marked for immediate flush
   */
  private async processPendingFlushSessions(): Promise<void> {
    try {
      const pendingSessions = await redis.smembers("sessions:pending_flush");

      for (const sessionId of pendingSessions) {
        await this.processBatch(sessionId);
        await redis.srem("sessions:pending_flush", sessionId);
      }
    } catch (error) {
      console.error("Error processing pending flush sessions:", error);
    }
  }

  /**
   * Process a single session's buffered events
   */
  async processBatch(sessionId: string): Promise<number> {
    try {
      // Retrieve events from Redis
      const rawEvents = await getBehaviorEvents(sessionId);

      if (rawEvents.length === 0) {
        return 0;
      }

      // Limit batch size
      const eventsToProcess = rawEvents.slice(0, this.maxEventsPerBatch);

      // Parse events
      const events: NormalizedBehaviorEvent[] = eventsToProcess;

      if (events.length === 0) {
        return 0;
      }

      // Get student ID from first event
      const studentId = events[0].studentId;

      // Aggregate events
      const aggregator = new EventAggregator();
      aggregator.addEvents(events);
      const aggregatedData = aggregator.aggregate(sessionId, studentId);

      // Prepare database operations
      await this.persistAggregatedData(aggregatedData);

      // Update session statistics
      await this.updateSessionStatistics(sessionId, events);

      // Clean up Redis
      await this.cleanupProcessedEvents(sessionId, eventsToProcess.length);

      console.log(
        `✅ Processed ${events.length} events for session ${sessionId}`
      );

      return events.length;
    } catch (error) {
      console.error(`Error processing batch for session ${sessionId}:`, error);
      throw error;
    }
  }

  /**
   * Persist aggregated data to PostgreSQL
   */
  private async persistAggregatedData(
    data: AggregatedBehaviorData
  ): Promise<void> {
    const maxRetries = 3;
    let attempt = 0;

    while (attempt < maxRetries) {
      try {
        // Check if session exists
        const session = await prisma.session.findUnique({
          where: { id: data.sessionId },
        });

        if (!session) {
          console.warn(`Session ${data.sessionId} not found, skipping persist`);
          return;
        }

        // Calculate cognitive load score
        const cognitiveLoadScore = this.calculateCognitiveLoadScore(data);

        // Create cognitive metric record
        await prisma.cognitiveMetric.create({
          data: {
            studentId: data.studentId,
            sessionId: data.sessionId,
            timestamp: new Date(data.timeWindow.end),
            cognitiveLoadScore,
            taskSwitchingFreq: data.metrics.taskSwitchingFreq,
            errorRate: data.metrics.errorRate,
            procrastinationScore: data.metrics.procrastinationScore,
            browsingDriftScore: data.metrics.browsingDriftScore,
            timePerConcept: data.metrics.avgTimePerConcept / 1000, // Convert to seconds
            productivityScore: data.metrics.productivityScore,
            avoidanceBehavior: data.patterns.avoidedTopics,
            moodScore: null, // To be implemented with sentiment analysis
          },
        });

        return; // Success
      } catch (error: any) {
        attempt++;

        if (error.code === "P2002") {
          // Unique constraint violation - this is OK, data already exists
          console.log(
            `Cognitive metric already exists for session ${data.sessionId}`
          );
          return;
        }

        if (attempt >= maxRetries) {
          console.error(
            `Failed to persist data after ${maxRetries} attempts:`,
            error
          );
          throw error;
        }

        // Exponential backoff
        const delay = Math.pow(2, attempt) * 1000;
        console.log(`Retry attempt ${attempt} after ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  /**
   * Calculate cognitive load score from aggregated data
   */
  private calculateCognitiveLoadScore(data: AggregatedBehaviorData): number {
    // Weighted algorithm combining behavioral signals
    const weights = {
      taskSwitching: 0.25,
      errorRate: 0.2,
      procrastination: 0.2,
      browsingDrift: 0.15,
      timePerConcept: 0.1,
      productivity: 0.1,
    };

    // Normalize values to 0-100 scale
    const normalizedTaskSwitching = Math.min(
      data.metrics.taskSwitchingFreq * 10,
      100
    );
    const normalizedErrorRate = data.metrics.errorRate * 100;
    const normalizedProcrastination = Math.min(
      data.metrics.procrastinationScore,
      100
    );
    const normalizedBrowsingDrift = data.metrics.browsingDriftScore * 100;

    // Time per concept: longer is worse (indicates struggling)
    const normalizedTimePerConcept = Math.min(
      (data.metrics.avgTimePerConcept / 60000) * 20,
      100
    );

    // Productivity: inverse (lower productivity = higher load)
    const normalizedProductivity = 100 - data.metrics.productivityScore;

    // Calculate weighted score
    const cognitiveLoad =
      normalizedTaskSwitching * weights.taskSwitching +
      normalizedErrorRate * weights.errorRate +
      normalizedProcrastination * weights.procrastination +
      normalizedBrowsingDrift * weights.browsingDrift +
      normalizedTimePerConcept * weights.timePerConcept +
      normalizedProductivity * weights.productivity;

    return Math.min(Math.max(cognitiveLoad, 0), 100);
  }

  /**
   * Update session statistics
   */
  private async updateSessionStatistics(
    sessionId: string,
    events: NormalizedBehaviorEvent[]
  ): Promise<void> {
    try {
      const timestamps = events.map((e) => e.timestamp);
      const duration = Math.max(...timestamps) - Math.min(...timestamps);

      await prisma.session.update({
        where: { id: sessionId },
        data: {
          durationSeconds: Math.floor(duration / 1000),
          endTime: new Date(Math.max(...timestamps)),
        },
      });
    } catch (error: any) {
      // Session might not exist yet - this is OK
      if (error.code !== "P2025") {
        console.error("Error updating session statistics:", error);
      }
    }
  }

  /**
   * Clean up processed events from Redis
   */
  private async cleanupProcessedEvents(
    sessionId: string,
    count: number
  ): Promise<void> {
    try {
      const key = `behavior:${sessionId}`;

      // Remove processed events from the list (lpop to match lpush)
      for (let i = 0; i < count; i++) {
        await redis.lpop(key);
      }

      // Check if list is empty and delete key if so
      const remaining = await redis.llen(key);
      if (remaining === 0) {
        await redis.del(key);
      }

      // Log cleanup
      console.log(
        `🧹 Cleaned up ${count} events from Redis for session ${sessionId}`
      );
    } catch (error) {
      console.error("Error cleaning up processed events:", error);
    }
  }

  /**
   * Get processor status
   */
  getStatus(): {
    isRunning: boolean;
    isProcessing: boolean;
    batchInterval: number;
    maxEventsPerBatch: number;
  } {
    return {
      isRunning: this.intervalId !== null,
      isProcessing: this.isProcessing,
      batchInterval: this.batchInterval,
      maxEventsPerBatch: this.maxEventsPerBatch,
    };
  }
}

// Export singleton instance
export const batchProcessor = new BehaviorBatchProcessor(
  parseInt(process.env.BATCH_PROCESSOR_INTERVAL || "30000"),
  parseInt(process.env.MAX_EVENTS_PER_BATCH || "1000")
);
