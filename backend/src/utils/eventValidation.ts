import { z } from "zod";
import { BehaviorEventType } from "../models/BehaviorEvent";

// Base event schema
const baseEventSchema = z.object({
  sessionId: z.string().min(1),
  studentId: z.string().min(1),
  eventType: z.nativeEnum(BehaviorEventType),
  timestamp: z.number().positive(),
  metadata: z.record(z.any()).optional(),
});

// Event data schemas
const taskSwitchDataSchema = z.object({
  fromContext: z.string(),
  toContext: z.string(),
  switchDuration: z.number().nonnegative(),
  frequency: z.number().nonnegative(),
});

const typingPatternDataSchema = z.object({
  keystrokes: z.number().nonnegative(),
  wpm: z.number().nonnegative(),
  pauseDuration: z.number().nonnegative(),
  backspaceCount: z.number().nonnegative(),
  correctionRate: z.number().min(0).max(1),
});

const scrollBehaviorDataSchema = z.object({
  scrollDepth: z.number().min(0).max(100),
  scrollSpeed: z.number().nonnegative(),
  direction: z.enum(["up", "down"]),
  pausePoints: z.array(z.number()),
});

const mouseMovementDataSchema = z.object({
  movementSpeed: z.number().nonnegative(),
  clickCount: z.number().nonnegative(),
  hoverDuration: z.number().nonnegative(),
  idleTime: z.number().nonnegative(),
});

const timeTrackingDataSchema = z.object({
  conceptId: z.string(),
  startTime: z.number().positive(),
  endTime: z.number().positive(),
  duration: z.number().nonnegative(),
  interactionCount: z.number().nonnegative(),
});

const quizErrorDataSchema = z.object({
  questionId: z.string(),
  attemptNumber: z.number().positive(),
  errorType: z.string(),
  timeToError: z.number().nonnegative(),
});

const focusChangeDataSchema = z.object({
  isFocused: z.boolean(),
  duration: z.number().nonnegative(),
  reason: z.enum(["tab_switch", "window_blur", "navigation"]),
});

const navigationDataSchema = z.object({
  fromUrl: z.string(),
  toUrl: z.string(),
  duration: z.number().nonnegative(),
  navigationType: z.enum(["link", "back", "forward"]),
});

const idleTimeDataSchema = z.object({
  idleDuration: z.number().nonnegative(),
  startTime: z.number().positive(),
  endTime: z.number().positive(),
});

const contentInteractionDataSchema = z.object({
  contentId: z.string(),
  interactionType: z.enum(["click", "hover", "scroll", "read"]),
  duration: z.number().nonnegative(),
  depth: z.number().nonnegative(),
});

/**
 * Validate event data based on event type
 */
export function validateEventData(
  eventType: BehaviorEventType,
  eventData: any
): boolean {
  try {
    switch (eventType) {
      case BehaviorEventType.TASK_SWITCH:
        taskSwitchDataSchema.parse(eventData);
        break;
      case BehaviorEventType.TYPING_PATTERN:
        typingPatternDataSchema.parse(eventData);
        break;
      case BehaviorEventType.SCROLL_BEHAVIOR:
        scrollBehaviorDataSchema.parse(eventData);
        break;
      case BehaviorEventType.MOUSE_MOVEMENT:
        mouseMovementDataSchema.parse(eventData);
        break;
      case BehaviorEventType.TIME_TRACKING:
        timeTrackingDataSchema.parse(eventData);
        break;
      case BehaviorEventType.QUIZ_ERROR:
        quizErrorDataSchema.parse(eventData);
        break;
      case BehaviorEventType.FOCUS_CHANGE:
        focusChangeDataSchema.parse(eventData);
        break;
      case BehaviorEventType.NAVIGATION:
        navigationDataSchema.parse(eventData);
        break;
      case BehaviorEventType.IDLE_TIME:
        idleTimeDataSchema.parse(eventData);
        break;
      case BehaviorEventType.CONTENT_INTERACTION:
        contentInteractionDataSchema.parse(eventData);
        break;
      default:
        return false;
    }
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Validate complete behavior event
 */
export function validateCompleteEvent(event: any): {
  valid: boolean;
  errors?: string[];
} {
  try {
    // Validate base structure
    baseEventSchema.parse(event);

    // Validate event data
    if (!event.eventData || typeof event.eventData !== "object") {
      return {
        valid: false,
        errors: ["eventData is required and must be an object"],
      };
    }

    const eventDataValid = validateEventData(event.eventType, event.eventData);
    if (!eventDataValid) {
      return {
        valid: false,
        errors: ["Invalid eventData structure for event type"],
      };
    }

    return { valid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { valid: false, errors: error.errors.map((e) => e.message) };
    }
    return { valid: false, errors: ["Unknown validation error"] };
  }
}

/**
 * Validate business logic rules
 */
export function validateBusinessRules(event: any): {
  valid: boolean;
  errors?: string[];
} {
  const errors: string[] = [];

  // Timestamp should not be in the future (allow 1 second tolerance)
  if (event.timestamp > Date.now() + 1000) {
    errors.push("Timestamp cannot be in the future");
  }

  // Timestamp should not be too old (e.g., more than 24 hours)
  if (event.timestamp < Date.now() - 86400000) {
    errors.push("Timestamp is too old (>24 hours)");
  }

  // Event type specific validations
  if (event.eventType === BehaviorEventType.TIME_TRACKING) {
    const data = event.eventData;
    if (data.endTime < data.startTime) {
      errors.push("endTime must be after startTime");
    }
    if (data.duration !== data.endTime - data.startTime) {
      errors.push("duration must equal endTime - startTime");
    }
  }

  if (event.eventType === BehaviorEventType.TYPING_PATTERN) {
    const data = event.eventData;
    if (data.wpm > 300) {
      errors.push("WPM value is unrealistically high");
    }
    if (data.correctionRate < 0 || data.correctionRate > 1) {
      errors.push("correctionRate must be between 0 and 1");
    }
  }

  if (event.eventType === BehaviorEventType.IDLE_TIME) {
    const data = event.eventData;
    if (data.endTime < data.startTime) {
      errors.push("endTime must be after startTime");
    }
    if (data.idleDuration > 3600000) {
      errors.push("idleDuration should not exceed 1 hour");
    }
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors : undefined,
  };
}
