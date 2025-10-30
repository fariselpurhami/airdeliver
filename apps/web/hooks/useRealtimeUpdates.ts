// apps/web/hooks/useRealtimeUpdates.ts

import { useEffect, useState, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';

interface TelemetryPayload {
    lat: number;
    lon: number;
    alt_m: number;
    ground_speed_m_s: number;
    battery_pct: number;
    mission_id?: string | null;
    flight_mode?: string | null;
    flags?: string[] | null;
}

interface RealtimeUpdatesOptions {
    onNotification?: (notification: WebSocketNotification) => void; 
}

interface WebSocketNotification {
    id?: number; 
    type: string;
    title: string;
    body: string;
    created_at?: string; 
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
    const { data: session } = useSession();
    const [latestTelemetry, setLatestTelemetry] = useState<TelemetryPayload | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
    const { onNotification } = options; 

    const connectWebSocket = useCallback(() => {
       
        if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
            console.log('WebSocket already connected or connecting.');
            return;
        }

        if (!session) {
             console.log('Skipping WebSocket connection: No session.');
             setIsConnected(false);
             return;
        }
       
        if (droneIdToTrack === undefined) { 
             console.log('Skipping WebSocket: droneIdToTrack is undefined');
             setIsConnected(false);
             return;
        }

        const wsHost = process.env.NEXT_PUBLIC_WS_HOST || 'localhost:8000'; 
        const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsPath = droneIdToTrack ? `/ws/drones/${droneIdToTrack}` : '/ws/ui';
        const wsUri = `${wsProtocol}://${wsHost}${wsPath}`;

        console.log(`Attempting to connect WebSocket: ${wsUri}`);
        ws.current = new WebSocket(wsUri);
        setIsConnected(false); 

        ws.current.onopen = () => {
            console.log('WebSocket Connected');
            setIsConnected(true);

            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
            
        };

        ws.current.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket Message:', message);

                if (message.type === 'telemetry_update' && message.drone_id === droneIdToTrack) {
                    setLatestTelemetry(message.payload);
                } else if (message.type === 'notification') {
                  
                    if (onNotification) {
                        onNotification(message.payload as WebSocketNotification);
                    } else {
                       
                        toast.info(message.payload.body, {
                            description: message.payload.title,
                        });
                    }
                } else if (message.type === 'pong') {
                    console.log('WebSocket Pong received');
                   
                }
                
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
                toast.error("Received invalid data from server.");
            }
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket Error:', error);
            setIsConnected(false);
           
             toast.error("WebSocket connection error.");
        };

        ws.current.onclose = (event) => {
            console.log('WebSocket Disconnected:', event.code, event.reason);
            setIsConnected(false);
            ws.current = null;
            
            if (!event.wasClean && reconnectTimer.current === null) 
                 console.log('Attempting WebSocket reconnect in 5 seconds...');
                 reconnectTimer.current = setTimeout(connectWebSocket, 5000); 
            }
        };

    }, [session, droneIdToTrack, onNotification]);

    useEffect(() => {
        connectWebSocket();

        const intervalId = setInterval(() => {
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                console.log('Sending WebSocket Ping');
                ws.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); 

        return () => {
            console.log('Cleaning up WebSocket connection.');
            clearInterval(intervalId);
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current); 
            }
            ws.current?.close(1000, "Component unmounted"); 
            ws.current = null;
            setIsConnected(false);
        };
    }, [connectWebSocket]); 

    const sendMessage = useCallback((message: Record<string, any>) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            try {
                 ws.current.send(JSON.stringify(message));
            } catch (error) {
                 console.error("Failed to send WebSocket message:", error);
                 toast.error("Failed to send message to server.");
            }
        } else {
            console.error("Cannot send message: WebSocket not connected.");
            toast.warning("Cannot send message: Not connected to server.");
        }
    }, []); 

    return { latestTelemetry, isConnected, sendMessage };
}
