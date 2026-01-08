/**
 * Throttle function execution
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0;
  let timeoutId: NodeJS.Timeout | null = null;

  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now();

    if (now - lastCall >= delay) {
      lastCall = now;
      fn.apply(this, args);
    } else {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(
        () => {
          lastCall = Date.now();
          fn.apply(this, args);
        },
        delay - (now - lastCall)
      );
    }
  };
}

/**
 * Debounce function execution
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout | null = null;

  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) clearTimeout(timeoutId);

    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

/**
 * Calculate typing speed in words per minute
 */
export function calculateTypingSpeed(
  keystrokes: number,
  durationMs: number
): number {
  if (durationMs === 0) return 0;

  // Average word length is 5 characters
  const words = keystrokes / 5;
  const minutes = durationMs / 60000;

  return Math.round(words / Math.max(minutes, 0.01));
}

/**
 * Detect scroll pattern from scroll events
 */
export function detectScrollPattern(
  scrollEvents: Array<{
    scrollSpeed: number;
    direction: "up" | "down";
    scrollDepth: number;
  }>
): "skimming" | "reading" | "searching" {
  if (scrollEvents.length < 3) return "reading";

  const avgSpeed =
    scrollEvents.reduce((sum, e) => sum + e.scrollSpeed, 0) /
    scrollEvents.length;
  const directionChanges = scrollEvents
    .slice(1)
    .filter((e, i) => e.direction !== scrollEvents[i].direction).length;

  // Fast scrolling = skimming
  if (avgSpeed > 100) return "skimming";

  // Many direction changes = searching
  if (directionChanges > scrollEvents.length * 0.3) return "searching";

  return "reading";
}

/**
 * Check if current time is night time
 */
export function isNightTime(): boolean {
  const hour = new Date().getHours();
  return hour >= 22 || hour < 6;
}

/**
 * Get time of day category
 */
export function getTimeOfDay(): "morning" | "afternoon" | "evening" | "night" {
  const hour = new Date().getHours();

  if (hour >= 6 && hour < 12) return "morning";
  if (hour >= 12 && hour < 17) return "afternoon";
  if (hour >= 17 && hour < 22) return "evening";
  return "night";
}

/**
 * Generate unique event ID
 */
export function generateEventId(): string {
  return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Calculate cognitive load color based on score
 */
export function getCognitiveLoadColor(score: number): string {
  if (score < 40) return "#10b981"; // green
  if (score < 70) return "#f59e0b"; // yellow
  return "#ef4444"; // red
}

/**
 * Get cognitive load level
 */
export function getCognitiveLoadLevel(
  score: number
): "low" | "medium" | "high" {
  if (score < 40) return "low";
  if (score < 70) return "medium";
  return "high";
}

/**
 * Format duration in milliseconds to human readable
 */
export function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

/**
 * Calculate engagement level from metrics
 */
export function calculateEngagementLevel(metrics: {
  timePerConcept: number;
  clickCount: number;
  scrollDepth: number;
}): "low" | "medium" | "high" {
  let score = 0;

  // Time per concept: 30s-2min is good
  if (metrics.timePerConcept > 30000 && metrics.timePerConcept < 120000) {
    score += 1;
  }

  // Click count: >5 indicates engagement
  if (metrics.clickCount > 5) {
    score += 1;
  }

  // Scroll depth: >70% indicates thorough reading
  if (metrics.scrollDepth > 70) {
    score += 1;
  }

  if (score >= 2) return "high";
  if (score === 1) return "medium";
  return "low";
}

/**
 * Detect if user is procrastinating
 */
export function detectProcrastination(metrics: {
  idleTime: number;
  taskSwitches: number;
  navigationCount: number;
  timespan: number;
}): boolean {
  const idleRatio = metrics.idleTime / metrics.timespan;
  const switchFrequency = metrics.taskSwitches / (metrics.timespan / 60000); // per minute

  // High idle time OR frequent switching OR excessive navigation
  return idleRatio > 0.3 || switchFrequency > 3 || metrics.navigationCount > 10;
}

/**
 * Sanitize event data (remove sensitive information)
 */
export function sanitizeEventData(data: any): any {
  const sanitized = { ...data };

  // Remove potentially sensitive fields
  const sensitiveFields = ["password", "email", "token", "key"];

  function removeSensitiveFields(obj: any): any {
    if (typeof obj !== "object" || obj === null) return obj;

    const cleaned: any = Array.isArray(obj) ? [] : {};

    for (const key in obj) {
      if (sensitiveFields.some((field) => key.toLowerCase().includes(field))) {
        continue; // Skip sensitive fields
      }

      if (typeof obj[key] === "object") {
        cleaned[key] = removeSensitiveFields(obj[key]);
      } else {
        cleaned[key] = obj[key];
      }
    }

    return cleaned;
  }

  return removeSensitiveFields(sanitized);
}

/**
 * Validate event structure before sending
 */
export function validateEvent(event: any): boolean {
  if (!event || typeof event !== "object") return false;

  const required = [
    "sessionId",
    "studentId",
    "eventType",
    "eventData",
    "timestamp",
  ];
  return required.every((field) => field in event);
}

/**
 * Get battery status (if available) - useful for productivity tracking
 */
export async function getBatteryStatus(): Promise<{
  level: number;
  charging: boolean;
} | null> {
  if ("getBattery" in navigator) {
    try {
      const battery = await (navigator as any).getBattery();
      return {
        level: battery.level * 100,
        charging: battery.charging,
      };
    } catch (error) {
      return null;
    }
  }
  return null;
}

/**
 * Get network information (if available)
 */
export function getNetworkInfo(): {
  effectiveType: string;
  downlink: number;
} | null {
  const connection =
    (navigator as any).connection ||
    (navigator as any).mozConnection ||
    (navigator as any).webkitConnection;

  if (connection) {
    return {
      effectiveType: connection.effectiveType || "unknown",
      downlink: connection.downlink || 0,
    };
  }

  return null;
}
