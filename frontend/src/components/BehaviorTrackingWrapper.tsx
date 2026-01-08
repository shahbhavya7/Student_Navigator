"use client";

import { BehaviorTrackingProvider } from "./BehaviorTrackingProvider";
import { ReactNode, useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";

interface BehaviorTrackingWrapperProps {
  children: ReactNode;
}

export function BehaviorTrackingWrapper({
  children,
}: BehaviorTrackingWrapperProps) {
  const [sessionId, setSessionId] = useState<string>("");
  const [studentId, setStudentId] = useState<string>("");

  useEffect(() => {
    // Generate or retrieve session ID
    let currentSessionId = sessionStorage.getItem("sessionId");
    if (!currentSessionId) {
      currentSessionId = uuidv4();
      sessionStorage.setItem("sessionId", currentSessionId);
    }
    setSessionId(currentSessionId);

    // Get or create student ID (in production, this would come from auth)
    let currentStudentId = localStorage.getItem("studentId");
    if (!currentStudentId) {
      currentStudentId = `demo-student-${uuidv4()}`;
      localStorage.setItem("studentId", currentStudentId);
    }
    setStudentId(currentStudentId);
  }, []);

  const isTrackingEnabled =
    process.env.NEXT_PUBLIC_TRACKING_ENABLED !== "false";

  // Always render provider, use placeholder IDs until real ones are available
  const effectiveSessionId = sessionId || "initializing";
  const effectiveStudentId = studentId || "initializing";
  const shouldTrack = isTrackingEnabled && sessionId && studentId;

  return (
    <BehaviorTrackingProvider
      sessionId={effectiveSessionId}
      studentId={effectiveStudentId}
      enabled={shouldTrack}
    >
      {children}
    </BehaviorTrackingProvider>
  );
}
