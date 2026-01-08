import redis from "../config/redis";
import { io } from "../websocket/server";
import Redis from "ioredis";

interface AgentEvent {
  type: string;
  agent?: string;
  student_id?: string;
  session_id?: string;
  data?: any;
  intervention?: any;
  learning_path_id?: string;
  adjustments?: any[];
  timestamp: number;
}

class RedisPubSubHandler {
  private subscriber: Redis;
  private isSubscribed = false;

  constructor() {
    this.subscriber = redis.duplicate();
  }

  /**
   * Initialize pub/sub subscriptions
   */
  async initialize(): Promise<void> {
    if (this.isSubscribed) {
      console.log("⚠️ Already subscribed to Redis pub/sub channels");
      return;
    }

    try {
      // Subscribe to agent channels
      await this.subscriber.subscribe(
        "interventions",
        "curriculum_updates",
        "agent:clr",
        "agent:performance",
        "agent:engagement",
        "agent:curriculum",
        "agent:motivation"
      );

      this.isSubscribed = true;

      // Set up message handlers
      this.subscriber.on("message", (channel: string, message: string) => {
        this.handleMessage(channel, message);
      });

      console.log("📡 Subscribed to Redis pub/sub channels for agent events");
    } catch (error) {
      console.error("Error initializing Redis pub/sub:", error);
      throw error;
    }
  }

  /**
   * Handle incoming pub/sub messages
   */
  private handleMessage(channel: string, message: string): void {
    try {
      const event: AgentEvent = JSON.parse(message);

      console.log(`📨 Received ${event.type} on ${channel}`);

      // Route to appropriate handler
      switch (channel) {
        case "interventions":
          this.handleIntervention(event);
          break;
        case "curriculum_updates":
          this.handleCurriculumUpdate(event);
          break;
        default:
          // Log other agent events
          console.log(`🤖 Agent event [${channel}]: ${event.type}`);
      }
    } catch (error) {
      console.error(`Error parsing message from ${channel}:`, error);
    }
  }

  /**
   * Handle intervention events from Python agents
   */
  private handleIntervention(event: AgentEvent): void {
    try {
      const { student_id, intervention } = event;

      if (!student_id || !intervention) {
        console.error("Invalid intervention event:", event);
        return;
      }

      console.log(
        `🚨 Delivering intervention to student ${student_id}: ${intervention.type}`
      );

      // Send intervention via WebSocket notifications namespace
      const notificationsNs = io.of("/notifications");
      notificationsNs.to(`student:${student_id}`).emit("notification", {
        type: "intervention",
        priority: intervention.priority || "medium",
        message: intervention.message,
        metadata: {
          intervention_id: intervention.intervention_id,
          intervention_type: intervention.type,
          timestamp: intervention.timestamp,
        },
      });

      // Also log to main namespace for debugging
      io.to(`student:${student_id}`).emit("agent:intervention", intervention);
    } catch (error) {
      console.error("Error handling intervention:", error);
    }
  }

  /**
   * Handle curriculum update events
   */
  private async handleCurriculumUpdate(event: AgentEvent): Promise<void> {
    try {
      const { student_id, learning_path_id, adjustments } = event;

      if (!student_id || !learning_path_id) {
        console.error("Invalid curriculum update event:", event);
        return;
      }

      console.log(
        `📚 Curriculum updated for student ${student_id}, path ${learning_path_id}`
      );

      // Send notification to student
      const notificationsNs = io.of("/notifications");
      notificationsNs.to(`student:${student_id}`).emit("notification", {
        type: "curriculum_update",
        priority: "medium",
        message: "Your learning path has been adjusted based on your progress",
        metadata: {
          learning_path_id,
          adjustments,
          timestamp: event.timestamp,
        },
      });

      // TODO: Update learning path in PostgreSQL if needed
      // This would typically involve calling a service to persist changes
    } catch (error) {
      console.error("Error handling curriculum update:", error);
    }
  }

  /**
   * Publish event to Redis for Python backend consumption
   */
  async publishEvent(channel: string, event: any): Promise<void> {
    try {
      await redis.publish(channel, JSON.stringify(event));
      console.log(`📤 Published event to ${channel}: ${event.type}`);
    } catch (error) {
      console.error(`Error publishing to ${channel}:`, error);
    }
  }

  /**
   * Cleanup subscriptions
   */
  async cleanup(): Promise<void> {
    if (this.isSubscribed) {
      await this.subscriber.unsubscribe();
      await this.subscriber.quit();
      this.isSubscribed = false;
      console.log("🔌 Redis pub/sub subscriptions closed");
    }
  }
}

// Export singleton instance
export const redisPubSub = new RedisPubSubHandler();
