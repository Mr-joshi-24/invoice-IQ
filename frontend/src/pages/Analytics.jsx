import React, { useEffect, useState } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { BarChart3, TrendingUp, ShieldCheck, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { getAnalyticsOverview } from '../api';

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAnalyticsOverview()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-400">Loading analytics insights...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Processing Analytics & Intelligence</h1>
        <p className="text-sm text-slate-400 mt-0.5">Comprehensive operational metrics, automated extraction accuracy, and anomaly detection stats.</p>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Pipeline Success Rate</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1">{data?.success_rate}%</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Automated routing without failure</span>
        </div>
        <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Mean Extraction Confidence</span>
          <p className="text-2xl font-bold text-brand-400 mt-1">
            {data?.average_confidence ? `${Math.round(data.average_confidence * 100)}%` : '—'}
          </p>
          <span className="text-[11px] text-slate-400 mt-1 block">Across all mandatory fields</span>
        </div>
        <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Anomalies Isolated</span>
          <p className="text-2xl font-bold text-purple-400 mt-1">{data?.anomalies_detected}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Flagged by Isolation Forest</span>
        </div>
        <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Human Reviews Required</span>
          <p className="text-2xl font-bold text-amber-400 mt-1">{data?.pending_review}</p>
          <span className="text-[11px] text-slate-400 mt-1 block">Awaiting audit resolution</span>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Throughput Bar Chart */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800">
          <h3 className="text-base font-bold text-slate-100 mb-1">Daily Document Throughput</h3>
          <p className="text-xs text-slate-400 mb-6">Volume processed over the last 7 calendar days</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.recent_activity || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }} />
                <Bar dataKey="processed" fill="#10b981" name="Processed" radius={[4, 4, 0, 0]} />
                <Bar dataKey="needs_review" fill="#f59e0b" name="Needs Review" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failed" fill="#ef4444" name="Failed" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Processing Efficiency Breakdown */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-100 mb-1">Portfolio Resolution Breakdown</h3>
            <p className="text-xs text-slate-400 mb-6">Distribution of documents across resolution outcomes</p>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data?.status_distribution || []}
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {(data?.status_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-800">
            {(data?.status_distribution || []).map((item) => (
              <div key={item.name} className="flex items-center gap-2 text-xs">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                <span className="text-slate-300 font-medium">{item.name}:</span>
                <span className="text-slate-100 font-bold">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

