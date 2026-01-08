"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import wsClient from "@/services/websocket";
import { BehaviorEventType, TrackedEvent } from "@/types/behavior";
import {
  throttle,
  debounce,
  calculateTypingSpeed,
  generateEventId,
} from "@/utils/behaviorHelpers";

export interface UseBehaviorTrackerOptions {
  sessionId: string;
  studentId: string;
  enabled?: boolean;
  samplingRate?: number; // Max events per second
  batchSize?: number; // Events to batch before sending
}

export interface UseBehaviorTrackerReturn {
  isTracking: boolean;
  startTracking: () => void;
  stopTracking: () => void;
  trackCustomEvent: (eventType: BehaviorEventType, data: any) => void;
  eventCount: number;
}

export function useBehaviorTracker(
  options: UseBehaviorTrackerOptions
): UseBehaviorTrackerReturn {
  const {
    sessionId,
    studentId,
    enabled = true,
    samplingRate = 100,
    batchSize = 10,
  } = options;

  const [isTracking, setIsTracking] = useState(false);
  const [eventCount, setEventCount] = useState(0);

  const eventQueue = useRef<TrackedEvent[]>([]);
  const batchIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const cleanupFunctionsRef = useRef<Array<() => void>>([]);

  const router = useRouter();
  const pathname = usePathname();

  // Track previous pathname for navigation events
  const prevPathnameRef = useRef<string>(pathname);
  const navigationStartTimeRef = useRef<number>(Date.now());

  // Tracking state refs
  const typingStateRef = useRef({
    keystrokes: 0,
    startTime: 0,
    lastKeystroke: 0,
    backspaceCount: 0,
    totalChars: 0,
  });

  const scrollStateRef = useRef({
    lastScrollY: 0,
    lastScrollTime: 0,
    pausePoints: [] as number[],
  });

  const mouseStateRef = useRef({
    lastMoveTime: 0,
    clickCount: 0,
    lastPosition: { x: 0, y: 0 },
  });

  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const idleStartTimeRef = useRef<number | null>(null);

  const focusStateRef = useRef({
    lastFocusChange: Date.now(),
    isFocused: true,
  });

  const conceptVisibilityRef = useRef<
    Map<string, { startTime: number; interactionCount: number }>
  >(new Map());

  /**
   * Queue an event for batching
   */
  const queueEvent = useCallback(
    (eventType: BehaviorEventType, eventData: any) => {
      const event: TrackedEvent = {
        id: generateEventId(),
        sessionId,
        studentId,
        eventType,
        eventData,
        timestamp: Date.now(),
        metadata: {
          pathname,
          userAgent:
            typeof navigator !== "undefined" ? navigator.userAgent : "",
        },
      };

      eventQueue.current.push(event);
      setEventCount((prev) => prev + 1);

      // Send batch if reached batch size
      if (eventQueue.current.length >= batchSize) {
        sendBatch();
      }
    },
    [sessionId, studentId, pathname, batchSize]
  );

  /**
   * Send batched events to server
   */
  const sendBatch = useCallback(() => {
    if (eventQueue.current.length === 0) return;

    // Check if WebSocket is connected before sending
    const socket = wsClient.getSocket();
    if (!socket?.connected) {
      console.warn("WebSocket not connected, retaining events in queue");
      return; // Keep events in queue for next retry
    }

    const events = [...eventQueue.current];
    eventQueue.current = [];

    try {
      wsClient.sendBehaviorBatch(events);
    } catch (error) {
      console.error("Error sending behavior batch:", error);
      // Re-queue events on failure
      eventQueue.current.unshift(...events);
    }
  }, []);

  /**
   * Task switching detection
   */
  const setupTaskSwitchingTracking = useCallback(() => {
    let lastContext = pathname;

    const handleVisibilityChange = () => {
      const isVisible = document.visibilityState === "visible";
      const now = Date.now();

      if (!isVisible) {
        queueEvent(BehaviorEventType.TASK_SWITCH, {
          fromContext: lastContext,
          toContext: "hidden",
          switchDuration: now - focusStateRef.current.lastFocusChange,
          frequency: 1,
        });
      } else {
        queueEvent(BehaviorEventType.TASK_SWITCH, {
          fromContext: "hidden",
          toContext: pathname,
          switchDuration: now - focusStateRef.current.lastFocusChange,
          frequency: 1,
        });
      }

      focusStateRef.current.lastFocusChange = now;
      lastContext = pathname;
    };

    const handleBlur = () => {
      queueEvent(BehaviorEventType.FOCUS_CHANGE, {
        isFocused: false,
        duration: Date.now() - focusStateRef.current.lastFocusChange,
        reason: "window_blur",
      });
      focusStateRef.current.isFocused = false;
      focusStateRef.current.lastFocusChange = Date.now();
    };

    const handleFocus = () => {
      queueEvent(BehaviorEventType.FOCUS_CHANGE, {
        isFocused: true,
        duration: Date.now() - focusStateRef.current.lastFocusChange,
        reason: "window_blur",
      });
      focusStateRef.current.isFocused = true;
      focusStateRef.current.lastFocusChange = Date.now();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);

    cleanupFunctionsRef.current.push(() => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
    });
  }, [pathname, queueEvent]);

  /**
   * Typing pattern tracking
   */
  const setupTypingTracking = useCallback(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (!["INPUT", "TEXTAREA"].includes(target.tagName)) return;

      const now = Date.now();
      const state = typingStateRef.current;

      if (state.startTime === 0) {
        state.startTime = now;
      }

      state.keystrokes++;
      state.totalChars++;

      if (e.key === "Backspace" || e.key === "Delete") {
        state.backspaceCount++;
        state.totalChars = Math.max(0, state.totalChars - 1);
      }

      const pauseDuration = now - state.lastKeystroke;
      state.lastKeystroke = now;

      // Send typing pattern event every 20 keystrokes or after 3 seconds of pause
      if (state.keystrokes >= 20 || pauseDuration > 3000) {
        const duration = now - state.startTime;
        const wpm = calculateTypingSpeed(state.keystrokes, duration);
        const correctionRate =
          state.totalChars > 0 ? state.backspaceCount / state.totalChars : 0;

        queueEvent(BehaviorEventType.TYPING_PATTERN, {
          keystrokes: state.keystrokes,
          wpm,
          pauseDuration,
          backspaceCount: state.backspaceCount,
          correctionRate,
        });

        // Reset state
        state.keystrokes = 0;
        state.backspaceCount = 0;
        state.startTime = now;
        state.totalChars = 0;
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    cleanupFunctionsRef.current.push(() => {
      document.removeEventListener("keydown", handleKeyDown);
    });
  }, [queueEvent]);

  /**
   * Scroll behavior tracking
   */
  const setupScrollTracking = useCallback(() => {
    const handleScroll = throttle(() => {
      const now = Date.now();
      const scrollY = window.scrollY;
      const state = scrollStateRef.current;

      const scrollSpeed =
        Math.abs(scrollY - state.lastScrollY) /
        (now - state.lastScrollTime || 1);
      const direction = scrollY > state.lastScrollY ? "down" : "up";
      const scrollDepth =
        ((scrollY + window.innerHeight) /
          document.documentElement.scrollHeight) *
        100;

      // Detect pause points (scroll stopped for >2 seconds)
      if (now - state.lastScrollTime > 2000 && state.lastScrollY !== 0) {
        state.pausePoints.push(state.lastScrollY);
      }

      queueEvent(BehaviorEventType.SCROLL_BEHAVIOR, {
        scrollDepth: Math.min(scrollDepth, 100),
        scrollSpeed,
        direction,
        pausePoints: [...state.pausePoints],
      });

      state.lastScrollY = scrollY;
      state.lastScrollTime = now;
    }, 100);

    window.addEventListener("scroll", handleScroll, { passive: true });

    cleanupFunctionsRef.current.push(() => {
      window.removeEventListener("scroll", handleScroll);
    });
  }, [queueEvent]);

  /**
   * Mouse movement and interaction tracking
   */
  const setupMouseTracking = useCallback(() => {
    const handleMouseMove = throttle((e: MouseEvent) => {
      const now = Date.now();
      const state = mouseStateRef.current;

      const dx = e.clientX - state.lastPosition.x;
      const dy = e.clientY - state.lastPosition.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const timeDelta = now - state.lastMoveTime;
      const movementSpeed = timeDelta > 0 ? distance / timeDelta : 0;

      state.lastPosition = { x: e.clientX, y: e.clientY };
      state.lastMoveTime = now;

      // Reset idle timer on movement
      resetIdleTimer();
    }, 200);

    const handleClick = () => {
      mouseStateRef.current.clickCount++;
      resetIdleTimer();
    };

    // Send mouse metrics every 10 seconds
    const mouseMetricsInterval = setInterval(() => {
      const state = mouseStateRef.current;
      const idleTime = idleStartTimeRef.current
        ? Date.now() - idleStartTimeRef.current
        : 0;

      queueEvent(BehaviorEventType.MOUSE_MOVEMENT, {
        movementSpeed: 0, // Average would be calculated server-side
        clickCount: state.clickCount,
        hoverDuration: 0,
        idleTime,
      });

      state.clickCount = 0;
    }, 10000);

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("click", handleClick);

    cleanupFunctionsRef.current.push(() => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("click", handleClick);
      clearInterval(mouseMetricsInterval);
    });
  }, [queueEvent]);

  /**
   * Idle time detection
   */
  const resetIdleTimer = useCallback(() => {
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
    }

    // If was idle, send idle event
    if (idleStartTimeRef.current) {
      const idleDuration = Date.now() - idleStartTimeRef.current;
      queueEvent(BehaviorEventType.IDLE_TIME, {
        idleDuration,
        startTime: idleStartTimeRef.current,
        endTime: Date.now(),
      });
      idleStartTimeRef.current = null;
    }

    // Set new idle timer (60 seconds)
    idleTimerRef.current = setTimeout(() => {
      idleStartTimeRef.current = Date.now();
    }, 60000);
  }, [queueEvent]);

  /**
   * Time-per-concept tracking using Intersection Observer
   */
  const setupTimeTracking = useCallback(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const conceptId = entry.target.getAttribute("data-concept-id");
          if (!conceptId) return;

          if (entry.isIntersecting) {
            // Concept entered viewport
            conceptVisibilityRef.current.set(conceptId, {
              startTime: Date.now(),
              interactionCount: 0,
            });
          } else {
            // Concept left viewport
            const tracking = conceptVisibilityRef.current.get(conceptId);
            if (tracking) {
              const endTime = Date.now();
              const duration = endTime - tracking.startTime;

              queueEvent(BehaviorEventType.TIME_TRACKING, {
                conceptId,
                startTime: tracking.startTime,
                endTime,
                duration,
                interactionCount: tracking.interactionCount,
              });

              conceptVisibilityRef.current.delete(conceptId);
            }
          }
        });
      },
      { threshold: 0.5 }
    );

    // Observe all elements with data-concept-id
    const conceptElements = document.querySelectorAll("[data-concept-id]");
    conceptElements.forEach((el) => observer.observe(el));

    cleanupFunctionsRef.current.push(() => {
      observer.disconnect();

      // Send final events for all tracked concepts
      conceptVisibilityRef.current.forEach((tracking, conceptId) => {
        const endTime = Date.now();
        queueEvent(BehaviorEventType.TIME_TRACKING, {
          conceptId,
          startTime: tracking.startTime,
          endTime,
          duration: endTime - tracking.startTime,
          interactionCount: tracking.interactionCount,
        });
      });
      conceptVisibilityRef.current.clear();
    });
  }, [queueEvent]);

  /**
   * Navigation tracking
   */
  const setupNavigationTracking = useCallback(() => {
    // Just add cleanup function - actual tracking is in useEffect below
    cleanupFunctionsRef.current.push(() => {
      // Final navigation event if URL changed
      if (prevPathnameRef.current !== pathname) {
        queueEvent(BehaviorEventType.NAVIGATION, {
          fromUrl: prevPathnameRef.current,
          toUrl: pathname,
          duration: Date.now() - navigationStartTimeRef.current,
          navigationType: "link",
        });
      }
    });
  }, [pathname, queueEvent]);

  // Track pathname changes for navigation events
  useEffect(() => {
    if (!isTracking) return;

    // Don't track initial mount
    if (
      prevPathnameRef.current === pathname &&
      navigationStartTimeRef.current === Date.now()
    ) {
      return;
    }

    // Track navigation when pathname changes
    if (prevPathnameRef.current !== pathname) {
      const now = Date.now();
      const duration = now - navigationStartTimeRef.current;

      queueEvent(BehaviorEventType.NAVIGATION, {
        fromUrl: prevPathnameRef.current,
        toUrl: pathname,
        duration,
        navigationType: "link",
      });

      prevPathnameRef.current = pathname;
      navigationStartTimeRef.current = now;
    }
  }, [pathname, isTracking, queueEvent]);

  /**
   * Track custom event
   */
  const trackCustomEvent = useCallback(
    (eventType: BehaviorEventType, data: any) => {
      queueEvent(eventType, data);
    },
    [queueEvent]
  );

  /**
   * Start tracking
   */
  const startTracking = useCallback(() => {
    if (isTracking) return;

    setIsTracking(true);

    // Initialize WebSocket connection
    wsClient.connect(studentId, sessionId);

    // Send session start event
    wsClient.getSocket()?.emit("session:start", {
      sessionId,
      studentId,
      metadata: {
        pathname,
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "",
      },
    });

    // Set up all trackers
    setupTaskSwitchingTracking();
    setupTypingTracking();
    setupScrollTracking();
    setupMouseTracking();
    setupTimeTracking();
    setupNavigationTracking();

    // Initialize idle timer
    resetIdleTimer();

    // Start batch send interval (every 5 seconds)
    batchIntervalRef.current = setInterval(sendBatch, 5000);

    console.log("✅ Behavior tracking started");
  }, [
    isTracking,
    sessionId,
    studentId,
    pathname,
    setupTaskSwitchingTracking,
    setupTypingTracking,
    setupScrollTracking,
    setupMouseTracking,
    setupTimeTracking,
    setupNavigationTracking,
    resetIdleTimer,
    sendBatch,
  ]);

  /**
   * Stop tracking
   */
  const stopTracking = useCallback(() => {
    if (!isTracking) return;

    setIsTracking(false);

    // Clear batch interval
    if (batchIntervalRef.current) {
      clearInterval(batchIntervalRef.current);
      batchIntervalRef.current = null;
    }

    // Clear idle timer
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
      idleTimerRef.current = null;
    }

    // Run all cleanup functions
    cleanupFunctionsRef.current.forEach((cleanup) => cleanup());
    cleanupFunctionsRef.current = [];

    // Send final batch
    sendBatch();

    // Send session end event
    wsClient.getSocket()?.emit("session:end", { sessionId });

    console.log("🛑 Behavior tracking stopped");
  }, [isTracking, sessionId, sendBatch]);

  // Auto-start if enabled
  useEffect(() => {
    if (enabled && !isTracking) {
      startTracking();
    }

    return () => {
      if (isTracking) {
        stopTracking();
      }
    };
  }, [enabled]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTracking();
    };
  }, []);

  return {
    isTracking,
    startTracking,
    stopTracking,
    trackCustomEvent,
    eventCount,
  };
}
