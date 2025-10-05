// file: apps/web/components/admin/AlertPanel.tsx
// version: 1.0.0
// date: 2025-09-23
// author: Gemini

import { FiAlertTriangle, FiCheckCircle, FiXCircle } from "react-icons/fi";

const alerts = [
    { type: 'error', message: 'Drone #AD-007 disconnected unexpectedly.' },
    { type: 'warning', message: 'Product "Aero-1" low on stock (3 remaining).' },
    { type: 'error', message: 'Payment failed for order #8821. User notified.' },
    { type: 'info', message: 'Drone #AD-004 completed maintenance cycle.' },
]

const alertIcons = {
    error: <FiXCircle className="text-red-500" />,
    warning: <FiAlertTriangle className="text-yellow-500" />,
    info: <FiCheckCircle className="text-blue-500" />,
}

export function AlertPanel() {
    return (
        <div className="mt-8">
            <h3 className="font-semibold mb-4">System Alerts</h3>
            <div className="space-y-3 p-4 border rounded-lg max-h-72 overflow-y-auto">
                {alerts.map((alert, index) => (
                    <div key={index} className="flex items-start gap-3 p-2 rounded-md bg-foreground/5">
                        <span className="mt-1">{alertIcons[alert.type]}</span>
                        <p className="text-sm">{alert.message}</p>
                    </div>
                ))}
            </div>
        </div>
    )
}

