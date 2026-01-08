"use client";

import { useBehaviorTracking } from "@/components/BehaviorTrackingProvider";
import { useEffect, useState } from "react";

export default function Home() {
  const { isTracking, eventCount } = useBehaviorTracking();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">
          Adaptive Student Navigator
        </h1>

        <div className="mb-8 text-center">
          <p className="text-lg mb-4">
            Intelligent personalized learning platform with real-time cognitive
            load tracking
          </p>
          {mounted && (
            <div className="text-sm opacity-70">
              <p className={isTracking ? "text-green-500" : "text-gray-500"}>
                {isTracking ? "✓ Tracking Active" : "⚠ Tracking Inactive"} |{" "}
                {eventCount} events captured
              </p>
            </div>
          )}
        </div>

        <div className="grid text-center lg:grid-cols-3 lg:text-left gap-4">
          <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
            <h2 className="mb-3 text-2xl font-semibold">Real-time Tracking</h2>
            <p className="m-0 text-sm opacity-50">
              Monitor cognitive load and behavioral patterns in real-time
            </p>
          </div>

          <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
            <h2 className="mb-3 text-2xl font-semibold">Adaptive Learning</h2>
            <p className="m-0 text-sm opacity-50">
              AI-powered curriculum that adapts to your learning style
            </p>
          </div>

          <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
            <h2 className="mb-3 text-2xl font-semibold">Smart Interventions</h2>
            <p className="m-0 text-sm opacity-50">
              Intelligent agents provide timely support and guidance
            </p>
          </div>
        </div>

        <div className="mt-8 flex justify-center gap-4">
          <div
            className="load-indicator low w-4 h-4 rounded-full"
            title="Low cognitive load"
          ></div>
          <div
            className="load-indicator medium w-4 h-4 rounded-full"
            title="Medium cognitive load"
          ></div>
          <div
            className="load-indicator high w-4 h-4 rounded-full"
            title="High cognitive load"
          ></div>
        </div>

        <div className="mt-8 text-center text-sm opacity-50">
          {mounted && (
            <p>
              {isTracking
                ? "System Status: Behavioral Tracking Active - Monitoring user interactions"
                : "System Status: Ready for Phase 2 Implementation"}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
