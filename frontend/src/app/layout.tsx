import type { Metadata } from "next";
import "./globals.css";
import { BehaviorTrackingWrapper } from "@/components/BehaviorTrackingWrapper";

export const metadata: Metadata = {
  title: "Adaptive Student Navigator",
  description:
    "Intelligent personalized learning platform with real-time cognitive load tracking",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <BehaviorTrackingWrapper>{children}</BehaviorTrackingWrapper>
      </body>
    </html>
  );
}
