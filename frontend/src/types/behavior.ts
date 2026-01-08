// Behavior Event Type Enumerations (matching backend)
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

// Tracked Event Interface
export interface TrackedEvent {
  id: string;
  sessionId: string;
  studentId: string;
  eventType: BehaviorEventType;
  eventData: any;
  timestamp: number;
  metadata?: Record<string, any>;
}

// Tracking Configuration
export interface TrackingConfig {
  enabled: boolean;
  samplingRate: number; // Max events per second
  batchSize: number; // Events to batch before sending
  batchInterval: number; // Milliseconds between batch sends
}

// Behavior Metrics
export interface BehaviorMetrics {
  cognitiveLoadScore: number;
  taskSwitchingFreq: number;
  errorRate: number;
  procrastinationScore: number;
  browsingDriftScore: number;
  timePerConcept: number;
  productivityScore: number;
}

// Real-time Tracking Status
export interface TrackingStatus {
  isTracking: boolean;
  isConnected: boolean;
  eventCount: number;
  queueSize: number;
  lastEventTime: number | null;
}

// Event Data Types (matching backend schemas)
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
