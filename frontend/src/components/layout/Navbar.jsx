import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { UploadCloud, CheckCircle2, ShieldAlert } from 'lucide-react';

const titleMap = {
  '/': 'Executive Dashboard',
  '/upload': 'Upload Invoices & Receipts',
  '/documents': 'Processed Documents',
  '/review': 'Human Review Center',
  '/analytics': 'Platform Analytics',
  '/model': 'Model Evaluation & Benchmarks',
  '/settings': 'System Configuration'
};

export default function Navbar() {
  const location = useLocation();
  const currentTitle = titleMap[location.pathname] || 'Invoice IQ';

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
      <div>
        <h2 className="text-lg font-bold text-slate-100 tracking-tight">{currentTitle}</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Quick Upload Action */}
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-sm transition-colors"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Document</span>
        </Link>

        {/* Live Backend Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs font-medium text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>FastAPI Online</span>
        </div>
      </div>
    </header>
  );
}

