import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  ShieldAlert, 
  TrendingUp, 
  ArrowUpRight,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { getAnalyticsOverview, getDocuments } from '../api';

export default function Dashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [recentDocs, setRecentDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [overviewData, docsData] = await Promise.all([
        getAnalyticsOverview(),
        getDocuments({ page: 1, limit: 5 })
      ]);
      setAnalytics(overviewData);
      setRecentDocs(docsData.items || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400">Loading document intelligence metrics...</p>
        </div>
      </div>
    );
  }

  const kpis = [
    {
      title: 'Total Documents',
      value: analytics?.total_documents || 0,
      icon: FileText,
      color: 'from-blue-500 to-brand-600',
      textColor: 'text-blue-400'
    },
    {
      title: 'Successfully Processed',
      value: analytics?.processed || 0,
      icon: CheckCircle2,
      color: 'from-emerald-500 to-teal-600',
      textColor: 'text-emerald-400'
    },
    {
      title: 'Pending Review',
      value: analytics?.pending_review || 0,
      icon: Clock,
      color: 'from-amber-500 to-orange-600',
      textColor: 'text-amber-400'
    },
    {
      title: 'Failed Processing',
      value: analytics?.failed || 0,
      icon: AlertTriangle,
      color: 'from-rose-500 to-red-600',
      textColor: 'text-rose-400'
    },
    {
      title: 'Anomalies Detected',
      value: analytics?.anomalies_detected || 0,
      icon: ShieldAlert,
      color: 'from-purple-500 to-indigo-600',
      textColor: 'text-purple-400'
    },
    {
      title: 'Processing Success Rate',
      value: analytics?.total_documents > 0 ? `${analytics?.success_rate || 0}%` : 'N/A',
      icon: TrendingUp,
      color: 'from-brand-500 to-cyan-600',
      textColor: 'text-brand-400'
    }
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Banner Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Executive Document Processing</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time pipeline monitoring, automated extraction, and anomaly alerts.</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Live Data</span>
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.title}
              className="p-5 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-slate-700 transition-all shadow-sm"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-slate-400">{kpi.title}</span>
                <div className={`w-7 h-7 rounded-lg bg-gradient-to-tr ${kpi.color} flex items-center justify-center text-white shadow-sm`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-100 tracking-tight">{kpi.value}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Processing Volume Area Chart */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-950/80 border border-slate-800/80">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-bold text-slate-100">Document Processing Activity (7 Days)</h3>
              <p className="text-xs text-slate-400">Daily throughput of processed vs reviewed documents</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics?.recent_activity || []}>
                <defs>
                  <linearGradient id="colorProcessed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorReview" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} allowDecimals={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }}
                />
                <Area type="monotone" dataKey="processed" stroke="#10b981" fillOpacity={1} fill="url(#colorProcessed)" name="Processed" />
                <Area type="monotone" dataKey="needs_review" stroke="#f59e0b" fillOpacity={1} fill="url(#colorReview)" name="Needs Review" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Status Distribution Donut Chart */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800/80 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-100">Status Distribution</h3>
            <p className="text-xs text-slate-400">Current document processing portfolio</p>
          </div>
          <div className="h-48 my-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={analytics?.status_distribution || []}
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {(analytics?.status_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.5rem', color: '#f8fafc' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/60">
            {(analytics?.status_distribution || []).map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                <span className="text-xs text-slate-300">{item.name}: <strong className="text-slate-100">{item.value}</strong></span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Two Column Grid: Recent Documents & Recent Anomaly Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Uploaded Invoices Table */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-950/80 border border-slate-800/80">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-100">Recent Invoices</h3>
              <p className="text-xs text-slate-400">Latest documents processed by the pipeline</p>
            </div>
            <Link
              to="/documents"
              className="text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 font-medium">Document</th>
                  <th className="py-2.5 font-medium">Vendor</th>
                  <th className="py-2.5 font-medium">Total</th>
                  <th className="py-2.5 font-medium">Status</th>
                  <th className="py-2.5 font-medium">Confidence</th>
                  <th className="py-2.5 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recentDocs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-400">
                      No invoices uploaded yet. <Link to="/upload" className="text-brand-400 hover:underline">Upload your first invoice</Link>.
                    </td>
                  </tr>
                ) : (
                  recentDocs.map((doc) => {
                    const statusColors = {
                      PROCESSED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
                      NEEDS_REVIEW: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                      FAILED: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                      PENDING: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
                      PROCESSING: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                    };
                    return (
                      <tr key={doc.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3 font-medium text-slate-200 truncate max-w-[180px]">
                          {doc.original_filename}
                        </td>
                        <td className="py-3 text-slate-300 truncate max-w-[140px]">
                          {doc.vendor_name || '—'}
                        </td>
                        <td className="py-3 font-semibold text-slate-100">
                          {doc.total_amount ? `INR ${doc.total_amount}` : '—'}
                        </td>
                        <td className="py-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusColors[doc.processing_status] || 'bg-slate-800 text-slate-300'}`}>
                            {doc.processing_status}
                          </span>
                        </td>
                        <td className="py-3 text-slate-300">
                          {doc.overall_confidence !== null ? `${Math.round(doc.overall_confidence * 100)}%` : '—'}
                        </td>
                        <td className="py-3 text-right">
                          <Link
                            to={`/review?id=${doc.id}`}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-400 hover:text-brand-300"
                          >
                            <span>Inspect</span>
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Anomaly Alerts Feed */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800/80 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-purple-400" />
                <span>Anomaly Feed</span>
              </h3>
              <p className="text-xs text-slate-400">Suspicious billing & tax patterns flagged</p>
            </div>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto">
            {(!analytics?.recent_anomalies || analytics.recent_anomalies.length === 0) ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No financial anomalies flagged by the Isolation Forest.
              </div>
            ) : (
              analytics.recent_anomalies.map((anom) => (
                <div key={anom.id} className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-purple-500/30 transition-colors">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-semibold text-slate-200 truncate max-w-[140px]">{anom.vendor}</span>
                    <span className="text-[10px] text-purple-400 font-mono">Score: {anom.anomaly_score}</span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{anom.explanation}</p>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 pt-1.5 border-t border-slate-800/60">
                    <span>{anom.total_amount ? `INR ${anom.total_amount}` : ''}</span>
                    <Link to={`/review?id=${anom.document_id}`} className="text-brand-400 hover:underline">
                      Review &rarr;
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

