import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  UploadCloud, 
  FileText, 
  CheckSquare, 
  BarChart3, 
  Cpu, 
  Settings, 
  FileCheck2,
  ShieldCheck
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Upload Invoice', to: '/upload', icon: UploadCloud },
  { name: 'Documents', to: '/documents', icon: FileText },
  { name: 'Review Center', to: '/review', icon: CheckSquare },
  { name: 'Analytics', to: '/analytics', icon: BarChart3 },
  { name: 'Model Evaluation', to: '/model', icon: Cpu },
  { name: 'Settings', to: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Logo Header */}
      <div className="h-16 flex items-center px-5 border-b border-slate-800/80 gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-brand-500/20 ring-1 ring-white/20">
          <FileCheck2 className="w-5 h-5 text-white" />
        </div>
        <div className="overflow-hidden">
          <h1 className="font-bold text-base text-white tracking-tight flex items-center gap-1.5">
            Invoice <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded bg-brand-500/25 text-brand-300 border border-brand-500/40">IQ</span>
          </h1>
          <p className="text-[10px] text-slate-400 font-medium tracking-tight whitespace-nowrap">Extract. Validate. Understand.</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
        <div className="px-3 mb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Platform Navigation
        </div>
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20 font-semibold'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer System Status Badge */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/60">
        <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex items-center gap-3">
          <div className="relative">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping absolute inset-0 opacity-75"></span>
          </div>
          <div className="overflow-hidden">
            <p className="text-xs font-semibold text-slate-200">Invoice IQ Engine</p>
            <p className="text-[11px] text-slate-400 truncate">OCR & Anomaly Active</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
