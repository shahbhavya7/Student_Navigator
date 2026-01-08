// Student types
export interface Student {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  createdAt: string;
  updatedAt: string;
}

// Learning Path types
export interface LearningPath {
  id: string;
  studentId: string;
  title: string;
  description?: string;
  difficulty: 'easy' | 'medium' | 'hard';
  status: 'active' | 'completed' | 'paused';
  currentModuleId?: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
}

// Content Module types
export interface ContentModule {
  id: string;
  learningPathId: string;
  title: string;
  content: string;
  moduleType: 'lesson' | 'quiz' | 'exercise' | 'recap';
  difficulty: 'easy' | 'medium' | 'hard';
  estimatedMinutes: number;
  orderIndex: number;
  prerequisites: string[];
  createdAt: string;
  updatedAt: string;
}

// Quiz Result types
export interface QuizResult {
  id: string;
  studentId: string;
  moduleId: string;
  score: number;
  totalQuestions: number;
  correctAnswers: number;
  timeSpentSeconds: number;
  answers: any;
  completedAt: string;
}

// Cognitive Metric types
export interface CognitiveMetric {
  id: string;
  studentId: string;
  sessionId: string;
  timestamp: string;
  cognitiveLoadScore: number;
  taskSwitchingFreq: number;
  errorRate: number;
  procrastinationScore: number;
  browsingDriftScore: number;
  timePerConcept: number;
  productivityScore: number;
  avoidanceBehavior: any;
  moodScore?: number;
}

// Session types
export interface Session {
  id: string;
  studentId: string;
  startTime: string;
  endTime?: string;
  durationSeconds?: number;
  deviceInfo?: any;
}

// Path History types
export interface PathHistory {
  id: string;
  learningPathId: string;
  changeType: 'difficulty_adjusted' | 'module_reordered' | 'module_added' | 'module_removed';
  previousState: any;
  newState: any;
  reason: string;
  timestamp: string;
}

// WebSocket event types
export interface BehaviorEvent {
  sessionId: string;
  eventType: string;
  eventData: any;
  timestamp: number;
}

export interface Notification {
  id: string;
  type: 'intervention' | 'suggestion' | 'alert' | 'achievement';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high';
  timestamp: number;
  data?: any;
}

// API Response types
export interface HealthCheckResponse {
  status: 'ok' | 'error';
  timestamp: string;
  services: {
    postgres: string;
    redis: string;
  };
}
