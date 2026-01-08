// Behavior Event Type Enumerations
export enum BehaviorEventType {
  TASK_SWITCH = "TASK_SWITCH",
  TYPING_PATTERN = "TYPING_PATTERN",
  SCROLL_BEHAVIOR = "SCROLL_BEHAVIOR",
  MOUSE_MOVEMENT = "MOUSE_MOVEMENT",
  FOCUS_CHANGE = "FOCUS_CHANGE",
  NAVIGATION = "NAVIGATION",
  IDLE_TIME = "IDLE_TIME",
  QUIZ_ERROR = "QUIZ_ERROR",
  CONTENT_INTERACTION = "CONTENT_INTERACTION",
  TIME_TRACKING = "TIME_TRACKING",
}

export enum EventPriority {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL",
}

// Core Interfaces
export interface RawBehaviorEvent {
  sessionId: string;
  studentId: string;
  eventType: BehaviorEventType;
  eventData: EventDataUnion;
  timestamp: number;
  metadata?: Record<string, any>;
}

export interface NormalizedBehaviorEvent extends RawBehaviorEvent {
  id: string;
  serverTimestamp: number;
  priority: EventPriority;
  isValid: boolean;
  computedMetrics?: Record<string, number>;
}

export interface AggregatedBehaviorData {
  sessionId: string;
  studentId: string;
  timeWindow: {
    start: number;
    end: number;
  };
  metrics: {
    taskSwitchingFreq: number;
    errorRate: number;
    procrastinationScore: number;
    browsingDriftScore: number;
    avgTimePerConcept: number;
    productivityScore: number;
    totalEvents: number;
    eventCounts: Record<BehaviorEventType, number>;
  };
  patterns: {
    avoidedTopics: string[];
    peakActivityHours: number[];
    typingConsistency: number;
  };
}

// Event Data Schemas
export interface TaskSwitchData {
  fromContext: string;
  toContext: string;
  switchDuration: number;
  frequency: number;
}

export interface TypingPatternData {
  keystrokes: number;
  wpm: number;
  pauseDuration: number;
  backspaceCount: number;
  correctionRate: number;
}

export interface ScrollBehaviorData {
  scrollDepth: number;
  scrollSpeed: number;
  direction: "up" | "down";
  pausePoints: number[];
}

export interface MouseMovementData {
  movementSpeed: number;
  clickCount: number;
  hoverDuration: number;
  idleTime: number;
}

export interface TimeTrackingData {
  conceptId: string;
  startTime: number;
  endTime: number;
  duration: number;
  interactionCount: number;
}

export interface QuizErrorData {
  questionId: string;
  attemptNumber: number;
  errorType: string;
  timeToError: number;
}

export interface FocusChangeData {
  isFocused: boolean;
  duration: number;
  reason: "tab_switch" | "window_blur" | "navigation";
}

export interface NavigationData {
  fromUrl: string;
  toUrl: string;
  duration: number;
  navigationType: "link" | "back" | "forward";
}

export interface IdleTimeData {
  idleDuration: number;
  startTime: number;
  endTime: number;
}

export interface ContentInteractionData {
  contentId: string;
  interactionType: "click" | "hover" | "scroll" | "read";
  duration: number;
  depth: number;
}

export type EventDataUnion =
  | TaskSwitchData
  | TypingPatternData
  | ScrollBehaviorData
  | MouseMovementData
  | TimeTrackingData
  | QuizErrorData
  | FocusChangeData
  | NavigationData
  | IdleTimeData
  | ContentInteractionData;

// Validation Functions
export function validateBehaviorEvent(event: any): boolean {
  if (!event || typeof event !== "object") return false;

  const required = [
    "sessionId",
    "studentId",
    "eventType",
    "eventData",
    "timestamp",
  ];
  for (const field of required) {
    if (!(field in event)) return false;
  }

  // Validate sessionId and studentId are non-empty strings
  if (typeof event.sessionId !== "string" || event.sessionId.trim() === "")
    return false;
  if (typeof event.studentId !== "string" || event.studentId.trim() === "")
    return false;

  // Validate eventType is valid enum value
  if (!Object.values(BehaviorEventType).includes(event.eventType)) return false;

  // Validate timestamp is a valid number and not in future
  if (
    typeof event.timestamp !== "number" ||
    event.timestamp > Date.now() + 1000
  )
    return false;

  // Validate eventData is an object
  if (!event.eventData || typeof event.eventData !== "object") return false;

  return true;
}

export function normalizeBehaviorEvent(
  raw: RawBehaviorEvent
): NormalizedBehaviorEvent {
  const id = `${raw.sessionId}_${raw.timestamp}_${Math.random()
    .toString(36)
    .substr(2, 9)}`;
  const serverTimestamp = Date.now();
  const priority = calculateEventPriority(raw);

  const normalized: NormalizedBehaviorEvent = {
    ...raw,
    id,
    serverTimestamp,
    priority,
    isValid: true,
    computedMetrics: computeEventMetrics(raw),
  };

  return normalized;
}

export function calculateEventPriority(
  event: RawBehaviorEvent | NormalizedBehaviorEvent
): EventPriority {
  switch (event.eventType) {
    case BehaviorEventType.QUIZ_ERROR:
      return EventPriority.CRITICAL;

    case BehaviorEventType.TASK_SWITCH:
    case BehaviorEventType.IDLE_TIME:
      return EventPriority.HIGH;

    case BehaviorEventType.TYPING_PATTERN:
    case BehaviorEventType.TIME_TRACKING:
    case BehaviorEventType.CONTENT_INTERACTION:
      return EventPriority.MEDIUM;

    default:
      return EventPriority.LOW;
  }
}

function computeEventMetrics(event: RawBehaviorEvent): Record<string, number> {
  const metrics: Record<string, number> = {};

  switch (event.eventType) {
    case BehaviorEventType.TYPING_PATTERN:
      const typingData = event.eventData as TypingPatternData;
      metrics.efficiency =
        typingData.wpm / Math.max(typingData.correctionRate + 1, 1);
      break;

    case BehaviorEventType.SCROLL_BEHAVIOR:
      const scrollData = event.eventData as ScrollBehaviorData;
      metrics.engagement = scrollData.scrollDepth / 100;
      break;

    case BehaviorEventType.TIME_TRACKING:
      const timeData = event.eventData as TimeTrackingData;
      metrics.focusScore = timeData.duration / (timeData.duration + 1000); // Normalize
      break;

    case BehaviorEventType.MOUSE_MOVEMENT:
      const mouseData = event.eventData as MouseMovementData;
      metrics.activity =
        mouseData.clickCount / Math.max(mouseData.idleTime / 1000, 1);
      break;
  }

  return metrics;
}

// Utility Classes
export class BehaviorEventBuilder {
  private event: Partial<RawBehaviorEvent> = {};

  withSessionId(sessionId: string): this {
    this.event.sessionId = sessionId;
    return this;
  }

  withStudentId(studentId: string): this {
    this.event.studentId = studentId;
    return this;
  }

  withEventType(eventType: BehaviorEventType): this {
    this.event.eventType = eventType;
    return this;
  }

  withEventData(eventData: EventDataUnion): this {
    this.event.eventData = eventData;
    return this;
  }

  withTimestamp(timestamp: number): this {
    this.event.timestamp = timestamp;
    return this;
  }

  withMetadata(metadata: Record<string, any>): this {
    this.event.metadata = metadata;
    return this;
  }

  build(): RawBehaviorEvent {
    if (!validateBehaviorEvent(this.event)) {
      throw new Error("Invalid behavior event");
    }
    return this.event as RawBehaviorEvent;
  }
}

export class EventAggregator {
  private events: NormalizedBehaviorEvent[] = [];

  addEvent(event: NormalizedBehaviorEvent): void {
    this.events.push(event);
  }

  addEvents(events: NormalizedBehaviorEvent[]): void {
    this.events.push(...events);
  }

  calculateTaskSwitchingFreq(timeWindowMs: number = 60000): number {
    const taskSwitches = this.events.filter(
      (e) => e.eventType === BehaviorEventType.TASK_SWITCH
    );
    if (taskSwitches.length === 0) return 0;

    const timeSpan =
      Math.max(...taskSwitches.map((e) => e.timestamp)) -
      Math.min(...taskSwitches.map((e) => e.timestamp));

    return (taskSwitches.length / Math.max(timeSpan, 1)) * timeWindowMs;
  }

  calculateErrorRate(): number {
    const quizErrors = this.events.filter(
      (e) => e.eventType === BehaviorEventType.QUIZ_ERROR
    );
    const quizInteractions = this.events.filter(
      (e) =>
        e.eventType === BehaviorEventType.QUIZ_ERROR ||
        (e.eventType === BehaviorEventType.CONTENT_INTERACTION &&
          (e.eventData as ContentInteractionData).contentId?.includes("quiz"))
    );

    if (quizInteractions.length === 0) return 0;
    return quizErrors.length / quizInteractions.length;
  }

  calculateProcrastinationScore(): number {
    const idleEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.IDLE_TIME
    );
    const taskSwitches = this.events.filter(
      (e) => e.eventType === BehaviorEventType.TASK_SWITCH
    );

    const totalIdleTime = idleEvents.reduce(
      (sum, e) => sum + ((e.eventData as IdleTimeData).idleDuration || 0),
      0
    );

    const switchFreq = this.calculateTaskSwitchingFreq();

    // Weighted score: 40% idle time, 40% task switching, 20% browsing drift
    const idleScore = Math.min(totalIdleTime / 60000, 1) * 40; // Normalize to 1 hour
    const switchScore = Math.min(switchFreq / 10, 1) * 40; // Normalize to 10 switches/min
    const driftScore = this.calculateBrowsingDriftScore() * 20;

    return idleScore + switchScore + driftScore;
  }

  calculateBrowsingDriftScore(): number {
    const navEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.NAVIGATION
    );
    const rapidNavs = navEvents.filter(
      (e) => (e.eventData as NavigationData).duration < 5000 // Less than 5 seconds
    );

    if (navEvents.length === 0) return 0;
    return rapidNavs.length / navEvents.length;
  }

  calculateAvgTimePerConcept(): number {
    const timeEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.TIME_TRACKING
    );
    if (timeEvents.length === 0) return 0;

    const totalTime = timeEvents.reduce(
      (sum, e) => sum + ((e.eventData as TimeTrackingData).duration || 0),
      0
    );

    return totalTime / timeEvents.length;
  }

  calculateProductivityScore(): number {
    const currentHour = new Date().getHours();
    const isNightTime = currentHour >= 22 || currentHour < 6;

    const activeEvents = this.events.filter(
      (e) =>
        e.eventType === BehaviorEventType.TYPING_PATTERN ||
        e.eventType === BehaviorEventType.CONTENT_INTERACTION ||
        e.eventType === BehaviorEventType.TIME_TRACKING
    );

    const idleEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.IDLE_TIME
    );

    const activityRatio = activeEvents.length / Math.max(this.events.length, 1);
    const nightPenalty = isNightTime ? 0.8 : 1.0;

    return activityRatio * 100 * nightPenalty;
  }

  identifyAvoidedTopics(): string[] {
    const timeEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.TIME_TRACKING
    );
    const conceptDurations = new Map<string, number>();

    timeEvents.forEach((e) => {
      const data = e.eventData as TimeTrackingData;
      const current = conceptDurations.get(data.conceptId) || 0;
      conceptDurations.set(data.conceptId, current + data.duration);
    });

    // Find concepts with below-average engagement
    const avgDuration =
      Array.from(conceptDurations.values()).reduce((a, b) => a + b, 0) /
      Math.max(conceptDurations.size, 1);

    const avoided: string[] = [];
    conceptDurations.forEach((duration, conceptId) => {
      if (duration < avgDuration * 0.5) {
        // Less than 50% of average
        avoided.push(conceptId);
      }
    });

    return avoided;
  }

  getEventCounts(): Record<BehaviorEventType, number> {
    const counts = {} as Record<BehaviorEventType, number>;

    Object.values(BehaviorEventType).forEach((type) => {
      counts[type] = 0;
    });

    this.events.forEach((e) => {
      counts[e.eventType]++;
    });

    return counts;
  }

  aggregate(sessionId: string, studentId: string): AggregatedBehaviorData {
    const timestamps = this.events.map((e) => e.timestamp);
    const timeWindow = {
      start: Math.min(...timestamps, Date.now()),
      end: Math.max(...timestamps, Date.now()),
    };

    return {
      sessionId,
      studentId,
      timeWindow,
      metrics: {
        taskSwitchingFreq: this.calculateTaskSwitchingFreq(),
        errorRate: this.calculateErrorRate(),
        procrastinationScore: this.calculateProcrastinationScore(),
        browsingDriftScore: this.calculateBrowsingDriftScore(),
        avgTimePerConcept: this.calculateAvgTimePerConcept(),
        productivityScore: this.calculateProductivityScore(),
        totalEvents: this.events.length,
        eventCounts: this.getEventCounts(),
      },
      patterns: {
        avoidedTopics: this.identifyAvoidedTopics(),
        peakActivityHours: this.getPeakActivityHours(),
        typingConsistency: this.calculateTypingConsistency(),
      },
    };
  }

  private getPeakActivityHours(): number[] {
    const hourCounts = new Map<number, number>();

    this.events.forEach((e) => {
      const hour = new Date(e.timestamp).getHours();
      hourCounts.set(hour, (hourCounts.get(hour) || 0) + 1);
    });

    const avgCount =
      Array.from(hourCounts.values()).reduce((a, b) => a + b, 0) /
      Math.max(hourCounts.size, 1);

    const peakHours: number[] = [];
    hourCounts.forEach((count, hour) => {
      if (count > avgCount * 1.2) {
        // 20% above average
        peakHours.push(hour);
      }
    });

    return peakHours.sort((a, b) => a - b);
  }

  private calculateTypingConsistency(): number {
    const typingEvents = this.events.filter(
      (e) => e.eventType === BehaviorEventType.TYPING_PATTERN
    );
    if (typingEvents.length < 2) return 1;

    const wpms = typingEvents.map(
      (e) => (e.eventData as TypingPatternData).wpm
    );
    const avgWpm = wpms.reduce((a, b) => a + b, 0) / wpms.length;
    const variance =
      wpms.reduce((sum, wpm) => sum + Math.pow(wpm - avgWpm, 2), 0) /
      wpms.length;
    const stdDev = Math.sqrt(variance);

    // Lower standard deviation = higher consistency
    return Math.max(0, 1 - stdDev / avgWpm);
  }

  clear(): void {
    this.events = [];
  }
}
