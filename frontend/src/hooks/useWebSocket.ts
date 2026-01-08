'use client';

import { useEffect, useState } from 'react';
import wsClient from '@/services/websocket';
import { Notification } from '@/types';

export const useWebSocket = (studentId?: string, sessionId?: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    if (studentId && sessionId) {
      const socket = wsClient.connect(studentId, sessionId);
      
      socket.on('connect', () => setIsConnected(true));
      socket.on('disconnect', () => setIsConnected(false));

      // Connect to notifications namespace
      wsClient.connectNotifications(studentId);

      // Listen for notifications
      const handleNotification = (event: CustomEvent<Notification>) => {
        setNotifications((prev) => [...prev, event.detail]);
      };

      window.addEventListener('agent-notification', handleNotification as EventListener);

      return () => {
        window.removeEventListener('agent-notification', handleNotification as EventListener);
        wsClient.disconnect();
      };
    }
  }, [studentId, sessionId]);

  const trackBehavior = (eventType: string, eventData: any) => {
    if (sessionId) {
      wsClient.trackBehavior(sessionId, eventType, eventData);
    }
  };

  const clearNotifications = () => {
    setNotifications([]);
  };

  return {
    isConnected,
    notifications,
    trackBehavior,
    clearNotifications,
  };
};
