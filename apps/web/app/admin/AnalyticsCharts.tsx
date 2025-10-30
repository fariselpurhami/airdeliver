// apps/web/components/admin/AnalyticsCharts.tsx

'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

const salesData = [
  { name: 'Aero-1', sales: 4000 },
  { name: 'Sky-Sailor', sales: 3000 },
  { name: 'Nimbus-3000', sales: 2000 },
  { name: 'Hornet-X', sales: 2780 },
];

const deliveryData = [
    { name: 'Mon', avgTime: 12.5 },
    { name: 'Tue', avgTime: 11.2 },
    { name: 'Wed', avgTime: 14.8 },
    { name: 'Thu', avgTime: 10.5 },
    { name: 'Fri', avgTime: 15.1 },
]

export function AnalyticsCharts() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
      <div>
        <h3 className="font-semibold mb-4">Top Selling Products</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={salesData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--foreground) / 0.1)' }}/>
            <Legend />
            <Bar dataKey="sales" fill="hsl(var(--foreground))" />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h3 className="font-semibold mb-4">Average Delivery Time (minutes)</h3>
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={deliveryData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--background))', border: '1px solid hsl(var(--foreground) / 0.1)' }}/>
                <Legend />
                <Line type="monotone" dataKey="avgTime" stroke="hsl(var(--foreground))" />
            </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
