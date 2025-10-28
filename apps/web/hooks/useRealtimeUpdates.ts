// file: airdeliver/apps/web/hooks/useRealtimeUpdates.ts (Updated)
import { useEffect, useState, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { toast } from 'sonner';

// Define the structure of the telemetry data payload we expect
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

// --- 💡 1. إضافة Callback للـ Props ---
interface RealtimeUpdatesOptions {
    onNotification?: (notification: WebSocketNotification) => void; // Callback function
}
// Define the structure for notifications pushed via WebSocket
interface WebSocketNotification {
    id?: number; // Optional, might come from server
    type: string;
    title: string;
    body: string;
    created_at?: string; // Optional timestamp
}

// Define what the hook returns
interface RealtimeUpdates {
    latestTelemetry: TelemetryPayload | null;
    // notifications: WebSocketNotification[]; // Removed, handled by callback
    isConnected: boolean;
    sendMessage: (message: Record<string, any>) => void; // Function to send messages
}

// --- 💡 2. تعديل الـ Hook لاستقبال الـ Options ---
export function useRealtimeUpdates(
    droneIdToTrack: string | null = null,
    options: RealtimeUpdatesOptions = {} // Accept options object
): RealtimeUpdates {
    const { data: session } = useSession();
    const [latestTelemetry, setLatestTelemetry] = useState<TelemetryPayload | null>(null);
    const [isConnected, setIsConnected] = useState<boolean>(false);
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
    const { onNotification } = options; // Destructure the callback

    const connectWebSocket = useCallback(() => {
        // Prevent multiple connections
        if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
            console.log('WebSocket already connected or connecting.');
            return;
        }

        // Only connect if session is available
        if (!session) {
             console.log('Skipping WebSocket connection: No session.');
             setIsConnected(false);
             return;
        }
        // Check for undefined specifically if null means general
        if (droneIdToTrack === undefined) { 
             console.log('Skipping WebSocket: droneIdToTrack is undefined');
             setIsConnected(false);
             return;
        }

        // Construct WebSocket URI - use environment variable for host/port if available, otherwise default
        const wsHost = process.env.NEXT_PUBLIC_WS_HOST || 'localhost:8000'; // Example: NEXT_PUBLIC_WS_HOST=your-api.com
        const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        // Adjust URI based on whether we track a specific drone or connect generally
        const wsPath = droneIdToTrack ? `/ws/drones/${droneIdToTrack}` : '/ws/ui'; // Added /ws/ui for general UI connections
        const wsUri = `${wsProtocol}://${wsHost}${wsPath}`;

        console.log(`Attempting to connect WebSocket: ${wsUri}`);
        ws.current = new WebSocket(wsUri);
        setIsConnected(false); // Mark as connecting

        ws.current.onopen = () => {
            console.log('WebSocket Connected');
            setIsConnected(true);
            // Clear reconnect timer on successful connection
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current);
                reconnectTimer.current = null;
            }
            // Optional: Send UI handshake or authentication if needed
            // const handshake = { type: 'ui_connect', token: session.accessToken };
            // ws.current?.send(JSON.stringify(handshake));
        };

        ws.current.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket Message:', message);

                // --- Handle different message types ---
                if (message.type === 'telemetry_update' && message.drone_id === droneIdToTrack) {
                    setLatestTelemetry(message.payload);
                } else if (message.type === 'notification') {
                    // --- 💡 3. استدعاء الـ Callback ---
                    if (onNotification) {
                        onNotification(message.payload as WebSocketNotification);
                    } else {
                        // Default behavior: show toast if no callback provided
                        toast.info(message.payload.body, {
                            description: message.payload.title,
                        });
                    }
                } else if (message.type === 'pong') {
                    console.log('WebSocket Pong received');
                    // Can be used to confirm connection health
                }
                // Add handlers for other message types from the server if needed
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
                toast.error("Received invalid data from server.");
            }
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket Error:', error);
            setIsConnected(false);
            // Don't trigger reconnect immediately on error, onclose will handle it
             toast.error("WebSocket connection error.");
        };

        ws.current.onclose = (event) => {
            console.log('WebSocket Disconnected:', event.code, event.reason);
            setIsConnected(false);
            ws.current = null;
            // --- Reconnect Logic ---
            if (!event.wasClean && reconnectTimer.current === null) { // Only attempt reconnect if closed unexpectedly
                 console.log('Attempting WebSocket reconnect in 5 seconds...');
                 reconnectTimer.current = setTimeout(connectWebSocket, 5000); // Try again after 5s
            }
        };

    }, [session, droneIdToTrack, onNotification]); // Add onNotification to dependencies

    useEffect(() => {
        // Initiate connection when session becomes available or droneId changes
        connectWebSocket();

        // Keepalive Ping interval
        const intervalId = setInterval(() => {
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
                console.log('Sending WebSocket Ping');
                ws.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Send ping every 30 seconds

        // Cleanup function
        return () => {
            console.log('Cleaning up WebSocket connection.');
            clearInterval(intervalId);
            if (reconnectTimer.current) {
                clearTimeout(reconnectTimer.current); // Clear timer on unmount
            }
            ws.current?.close(1000, "Component unmounted"); // Close with normal code
            ws.current = null;
            setIsConnected(false);
        };
    }, [connectWebSocket]); // Run effect when connectWebSocket function reference changes

    // Function to allow components to send messages
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
    }, []); // No dependencies needed if ws.current is stable

    // Return the state and functions needed by components
    return { latestTelemetry, isConnected, sendMessage };
}
