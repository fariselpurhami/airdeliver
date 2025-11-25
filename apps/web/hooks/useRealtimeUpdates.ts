// apps/web/hooks/useRealtimeUpdates.ts

import { useEffect, useState, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { WebSocketNotification, TelemetryPayload } from '@/types';

interface RealtimeUpdatesOptions {
    onNotification?: (notification: WebSocketNotification) => void;
}

interface RealtimeUpdates {
    latestTelemetry: TelemetryPayload | null;
    isConnected: boolean;
    sendMessage: (message: Record<string, any>) => void;
}

export function useRealtimeUpdates(
    droneIdToTrack: string | null = null,
    options: RealtimeUpdatesOptions = {}
): RealtimeUpdates {
    const { data: session, status } = useSession();
    const [latestTelemetry, setLatestTelemetry] = useState<TelemetryPayload | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
    const savedOnNotification = useRef(options.onNotification);
    const savedDroneId = useRef(droneIdToTrack);

    useEffect(() => {
        savedOnNotification.current = options.onNotification;
    }, [options.onNotification]);

    useEffect(() => {
        savedDroneId.current = droneIdToTrack;
    }, [droneIdToTrack]);

    const getSocketUrl = useCallback(() => {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
        const wsProtocol = isSecure ? 'wss:' : 'ws:';
        const hostUrl = apiBase.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '');

        return `${wsProtocol}//${hostUrl}/ws/notifications`;
    }, []);

    const connectWebSocket = useCallback(() => {
        if (status !== 'authenticated' || !session?.accessToken) {
            return;
        }

        if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
            return;
        }

        try {
            const baseUrl = getSocketUrl();
            const wsUri = `${baseUrl}?token=${session.accessToken}`;

            console.log('🔌 [WS] Initiating connection...');
            ws.current = new WebSocket(wsUri);

            ws.current.onopen = () => {
                console.log('🟢 [WS] Connected');
                setIsConnected(true);
             
                if (reconnectTimer.current) {
                    clearTimeout(reconnectTimer.current);
                    reconnectTimer.current = null;
                }
            };

            ws.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);

                    if (message.type === 'telemetry_update') {
                        const targetId = savedDroneId.current;

                        if (!targetId || message.drone_id === targetId) {
                            setLatestTelemetry(message.payload);
                        }
                    } else if (message.type === 'notification') {
    
                        if (savedOnNotification.current) {
                            savedOnNotification.current(message.payload as WebSocketNotification);
                        }
                    }
                } catch (error) {
                    console.warn('[WS] Parse error:', error);
                }
            };

            ws.current.onerror = (error) => {
                console.error('🔴 [WS] Connection Error', error);
              
            };

            ws.current.onclose = (event) => {
                console.log('🟡 [WS] Closed');
                setIsConnected(false);
                ws.current = null; 

                if (status === 'authenticated' && !reconnectTimer.current) {
                    reconnectTimer.current = setTimeout(() => {
                        console.log('🔄 [WS] Attempting reconnect...');
                        connectWebSocket();
                    }, 5000);
                }
            };

        } catch (error) {
            console.error('🔥 [WS] Critical Setup Error:', error);
            if (!reconnectTimer.current) {
                reconnectTimer.current = setTimeout(connectWebSocket, 5000);
            }
        }
    }, [session?.accessToken, status, getSocketUrl]); 

    useEffect(() => {
        if (status === 'authenticated') {
            connectWebSocket();
        }

        const intervalId = setInterval(() => {
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);

        return () => {
            clearInterval(intervalId);
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
            if (ws.current) {
              
                ws.current.onclose = null; 
                ws.current.onmessage = null;
                ws.current.onerror = null;
                ws.current.close();
                ws.current = null;
            }
            setIsConnected(false);
        };
    }, [connectWebSocket, status]); 

    const sendMessage = useCallback((message: Record<string, any>) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            try {
                ws.current.send(JSON.stringify(message));
            } catch (error) {
                console.error('[WS] Send failed:', error);
            }
        } else {
            console.warn('[WS] Cannot send message: Socket not open');
        }
    }, []);

    return { latestTelemetry, isConnected, sendMessage };
}
