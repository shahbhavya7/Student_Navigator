"use client";

import React, { createContext, useContext, ReactNode } from "react";
import {
  useBehaviorTracker,
  UseBehaviorTrackerReturn,
} from "@/hooks/useBehaviorTracker";
import { BehaviorEventType } from "@/types/behavior";

interface BehaviorTrackingContextType extends UseBehaviorTrackerReturn {
  sessionId: string;
  studentId: string;
}

const BehaviorTrackingContext =
  createContext<BehaviorTrackingContextType | null>(null);

export function useBehaviorTracking() {
  const context = useContext(BehaviorTrackingContext);
  if (!context) {
    throw new Error(
      "useBehaviorTracking must be used within BehaviorTrackingProvider"
    );
  }
  return context;
}

interface BehaviorTrackingProviderProps {
  children: ReactNode;
  sessionId: string;
  studentId: string;
  enabled?: boolean;
}

export function BehaviorTrackingProvider({
  children,
  sessionId,
  studentId,
  enabled = true,
}: BehaviorTrackingProviderProps) {
  const tracker = useBehaviorTracker({
    sessionId,
    studentId,
    enabled,
    samplingRate: parseInt(process.env.NEXT_PUBLIC_SAMPLING_RATE || "100"),
    batchSize: parseInt(process.env.NEXT_PUBLIC_BATCH_SIZE || "10"),
  });

  const value: BehaviorTrackingContextType = {
    ...tracker,
    sessionId,
    studentId,
  };

  return (
    <BehaviorTrackingContext.Provider value={value}>
      {children}
      {enabled && <TrackingStatusIndicator />}
    </BehaviorTrackingContext.Provider>
  );
}

function TrackingStatusIndicator() {
  const { isTracking, eventCount } = useBehaviorTracking();

  if (!isTracking) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-3 py-2 rounded-lg text-xs opacity-50 hover:opacity-100 transition-opacity">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
        <span>Tracking: {eventCount} events</span>
      </div>
    </div>
  );
}
