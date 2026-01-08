import {
  NormalizedBehaviorEvent,
  BehaviorEventType,
  EventAggregator,
} from "../models/BehaviorEvent";

/**
 * Calculate cognitive load score from behavioral events
 */
export function calculateCognitiveLoadScore(
  events: NormalizedBehaviorEvent[]
): number {
  if (events.length === 0) return 0;

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const taskSwitching = aggregator.calculateTaskSwitchingFreq();
  const errorRate = aggregator.calculateErrorRate();
  const procrastination = aggregator.calculateProcrastinationScore();
  const browsingDrift = aggregator.calculateBrowsingDriftScore();
  const productivity = aggregator.calculateProductivityScore();

  // Weighted algorithm
  const weights = {
    taskSwitching: 0.25,
    errorRate: 0.2,
    procrastination: 0.2,
    browsingDrift: 0.15,
    productivity: 0.2,
  };

  const normalizedTaskSwitching = Math.min(taskSwitching * 10, 100);
  const normalizedErrorRate = errorRate * 100;
  const normalizedProcrastination = Math.min(procrastination, 100);
  const normalizedBrowsingDrift = browsingDrift * 100;
  const normalizedProductivity = 100 - productivity;

  const cognitiveLoad =
    normalizedTaskSwitching * weights.taskSwitching +
    normalizedErrorRate * weights.errorRate +
    normalizedProcrastination * weights.procrastination +
    normalizedBrowsingDrift * weights.browsingDrift +
    normalizedProductivity * weights.productivity;

  return Math.min(Math.max(cognitiveLoad, 0), 100);
}

/**
 * Detect procrastination pattern from events
 */
export function detectProcrastinationPattern(
  events: NormalizedBehaviorEvent[]
): boolean {
  if (events.length < 10) return false;

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const procrastinationScore = aggregator.calculateProcrastinationScore();

  // Threshold for procrastination detection
  return procrastinationScore > 60;
}

/**
 * Identify topics being avoided
 */
export function identifyAvoidedTopics(
  events: NormalizedBehaviorEvent[],
  contentModules?: Array<{ id: string; title: string }>
): string[] {
  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  return aggregator.identifyAvoidedTopics();
}

/**
 * Calculate engagement score
 */
export function calculateEngagementScore(
  events: NormalizedBehaviorEvent[]
): number {
  if (events.length === 0) return 0;

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const productivity = aggregator.calculateProductivityScore();
  const avgTimePerConcept = aggregator.calculateAvgTimePerConcept();
  const procrastination = aggregator.calculateProcrastinationScore();

  // Engagement = high productivity + sustained focus - procrastination
  const engagementScore =
    productivity * 0.5 +
    Math.min((avgTimePerConcept / 60000) * 20, 50) * 0.3 -
    procrastination * 0.2;

  return Math.min(Math.max(engagementScore, 0), 100);
}

/**
 * Detect burnout signals
 */
export function detectBurnoutSignals(
  events: NormalizedBehaviorEvent[]
): boolean {
  if (events.length < 20) return false;

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const cognitiveLoad = calculateCognitiveLoadScore(events);
  const errorRate = aggregator.calculateErrorRate();
  const taskSwitching = aggregator.calculateTaskSwitchingFreq();
  const productivity = aggregator.calculateProductivityScore();

  // Burnout indicators:
  // 1. Very high cognitive load (>80)
  // 2. High error rate (>0.4)
  // 3. Excessive task switching (>8 per minute)
  // 4. Low productivity (<30)

  const burnoutScore =
    (cognitiveLoad > 80 ? 1 : 0) +
    (errorRate > 0.4 ? 1 : 0) +
    (taskSwitching > 8 ? 1 : 0) +
    (productivity < 30 ? 1 : 0);

  return burnoutScore >= 3;
}

/**
 * Analyze behavioral trends over time using sliding window
 */
export function analyzeBehavioralTrends(
  events: NormalizedBehaviorEvent[],
  windowSizeMs: number = 300000 // 5 minutes
): {
  trend: "improving" | "declining" | "stable";
  cognitiveLoadTrend: number[];
  engagementTrend: number[];
} {
  if (events.length < 10) {
    return {
      trend: "stable",
      cognitiveLoadTrend: [],
      engagementTrend: [],
    };
  }

  // Sort events by timestamp
  const sortedEvents = [...events].sort((a, b) => a.timestamp - b.timestamp);

  const windows: NormalizedBehaviorEvent[][] = [];
  const startTime = sortedEvents[0].timestamp;
  const endTime = sortedEvents[sortedEvents.length - 1].timestamp;

  // Create sliding windows
  for (let t = startTime; t <= endTime; t += windowSizeMs / 2) {
    const windowEvents = sortedEvents.filter(
      (e) => e.timestamp >= t && e.timestamp < t + windowSizeMs
    );
    if (windowEvents.length > 0) {
      windows.push(windowEvents);
    }
  }

  const cognitiveLoadTrend = windows.map((w) => calculateCognitiveLoadScore(w));
  const engagementTrend = windows.map((w) => calculateEngagementScore(w));

  // Calculate trend direction
  let trend: "improving" | "declining" | "stable" = "stable";

  if (cognitiveLoadTrend.length >= 2) {
    const recentLoad = cognitiveLoadTrend.slice(-2).reduce((a, b) => a + b) / 2;
    const earlierLoad =
      cognitiveLoadTrend.slice(0, 2).reduce((a, b) => a + b) / 2;
    const loadChange = recentLoad - earlierLoad;

    if (loadChange > 10) trend = "declining";
    else if (loadChange < -10) trend = "improving";
  }

  return {
    trend,
    cognitiveLoadTrend,
    engagementTrend,
  };
}

/**
 * Detect anomalies in behavioral patterns
 */
export function detectAnomalies(
  events: NormalizedBehaviorEvent[],
  historicalBaseline?: {
    avgCognitiveLoad: number;
    avgEngagement: number;
    avgTaskSwitching: number;
  }
): {
  hasAnomaly: boolean;
  anomalies: string[];
} {
  if (!historicalBaseline || events.length === 0) {
    return { hasAnomaly: false, anomalies: [] };
  }

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const currentCognitiveLoad = calculateCognitiveLoadScore(events);
  const currentEngagement = calculateEngagementScore(events);
  const currentTaskSwitching = aggregator.calculateTaskSwitchingFreq();

  const anomalies: string[] = [];

  // Detect significant deviations (>2 standard deviations)
  const THRESHOLD = 30; // 30% deviation

  if (
    Math.abs(currentCognitiveLoad - historicalBaseline.avgCognitiveLoad) >
    THRESHOLD
  ) {
    anomalies.push(
      `Cognitive load ${
        currentCognitiveLoad > historicalBaseline.avgCognitiveLoad
          ? "spike"
          : "drop"
      }`
    );
  }

  if (
    Math.abs(currentEngagement - historicalBaseline.avgEngagement) > THRESHOLD
  ) {
    anomalies.push(
      `Engagement ${
        currentEngagement > historicalBaseline.avgEngagement ? "surge" : "drop"
      }`
    );
  }

  if (
    Math.abs(currentTaskSwitching - historicalBaseline.avgTaskSwitching) > 5
  ) {
    anomalies.push("Unusual task switching pattern");
  }

  return {
    hasAnomaly: anomalies.length > 0,
    anomalies,
  };
}

/**
 * Generate insights summary from events
 */
export function generateInsightsSummary(events: NormalizedBehaviorEvent[]): {
  cognitiveLoad: number;
  engagement: number;
  productivity: number;
  warnings: string[];
  recommendations: string[];
} {
  if (events.length === 0) {
    return {
      cognitiveLoad: 0,
      engagement: 0,
      productivity: 0,
      warnings: [],
      recommendations: [],
    };
  }

  const aggregator = new EventAggregator();
  aggregator.addEvents(events);

  const cognitiveLoad = calculateCognitiveLoadScore(events);
  const engagement = calculateEngagementScore(events);
  const productivity = aggregator.calculateProductivityScore();
  const hasBurnout = detectBurnoutSignals(events);
  const hasProcrastination = detectProcrastinationPattern(events);

  const warnings: string[] = [];
  const recommendations: string[] = [];

  // Generate warnings
  if (hasBurnout) {
    warnings.push("Signs of cognitive overload detected");
    recommendations.push(
      "Consider taking a break or switching to lighter content"
    );
  }

  if (cognitiveLoad > 75) {
    warnings.push("High cognitive load detected");
    recommendations.push("Try breaking down tasks into smaller steps");
  }

  if (hasProcrastination) {
    warnings.push("Procrastination pattern detected");
    recommendations.push("Set small, achievable goals to build momentum");
  }

  if (engagement < 40) {
    warnings.push("Low engagement detected");
    recommendations.push("Content may not be matching your learning style");
  }

  if (productivity < 30) {
    warnings.push("Productivity below normal levels");
    recommendations.push(
      "Consider adjusting your study environment or schedule"
    );
  }

  return {
    cognitiveLoad,
    engagement,
    productivity,
    warnings,
    recommendations,
  };
}
