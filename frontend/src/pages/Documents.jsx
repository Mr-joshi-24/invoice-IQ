import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Search, 
  Filter, 
  Download, 
  RefreshCw, 
  ExternalLink, 
  ChevronLeft, 
  ChevronRight,
  ShieldAlert,
  FileSpreadsheet,
  FileCode
} from 'lucide-react';
import { getDocuments, reprocessDocument, getExportUrl } from '../api';

const statusFilters = ['ALL', 'PROCESSED', 'NEEDS_REVIEW', 'FAILED', 'PENDING'];

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [status, setStatus] = useState('ALL');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [reprocessingId, setReprocessingId] = useState(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments({
        page,
        limit: 10,
        status: status !== 'ALL' ? status : undefined,
        search: search.trim() || undefined
      });
      setDocs(data.items || []);
      setTotal(data.total || 0);
      setPages(data.pages || 1);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [page, status]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchDocs();
  };

  const handleReprocess = async (docId) => {
    setReprocessingId(docId);
    try {
      await reprocessDocument(docId);
      // Wait a moment and refresh
      setTimeout(() => {
        fetchDocs();
        setReprocessingId(null);
      }, 1500);
    } catch (err) {
      console.error('Reprocess failed:', err);
      setReprocessingId(null);
    }
  };

  const statusColors = {
    PROCESSED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    NEEDS_REVIEW: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    FAILED: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    PENDING: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    PROCESSING: 'bg-blue-500/10 text-blue-400 border-blue-500/20'
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Invoice Documents</h1>
          <p className="text-sm text-slate-400 mt-0.5">Explore, filter, review, and export all ingested financial records.</p>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2">
          <a
            href={getExportUrl('csv', status !== 'ALL' ? status : '')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
            <span>Export CSV</span>
          </a>
          <a
            href={getExportUrl('json', status !== 'ALL' ? status : '')}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <FileCode className="w-3.5 h-3.5 text-brand-400" />
            <span>Export JSON</span>
          </a>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Status Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
          {statusFilters.map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatus(st);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                status === st
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search vendor, invoice #..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-brand-500"
          />
        </form>
      </div>

      {/* Documents Data Table */}
      <div className="rounded-xl bg-slate-950/80 border border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900/60 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 font-semibold">Document</th>
                <th className="py-3 px-4 font-semibold">Vendor</th>
                <th className="py-3 px-4 font-semibold">Invoice #</th>
                <th className="py-3 px-4 font-semibold">Date</th>
                <th className="py-3 px-4 font-semibold">Total Amount</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Confidence</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
                      <span>Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : docs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No documents matching the current query.
                  </td>
                </tr>
              ) : (
                docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="py-3.5 px-4 font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        <span className="truncate max-w-[170px]" title={doc.original_filename}>
                          {doc.original_filename}
                        </span>
                        {doc.is_anomalous && (
                          <span title="Anomalous transaction flagged">
                            <ShieldAlert className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 truncate max-w-[140px]" title={doc.vendor_name || ''}>
                      {doc.vendor_name || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {doc.invoice_number || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {doc.invoice_date || '—'}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-100">
                      {doc.total_amount ? `INR ${doc.total_amount}` : '—'}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${statusColors[doc.processing_status] || 'bg-slate-800 text-slate-300'}`}>
                        {doc.processing_status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-slate-300">
                      {doc.overall_confidence !== null ? (
                        <div className="flex items-center gap-2">
                          <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className={`h-full ${
                                doc.overall_confidence >= 0.85
                                  ? 'bg-emerald-500'
                                  : doc.overall_confidence >= 0.70
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.round(doc.overall_confidence * 100)}%` }}
                            ></div>
                          </div>
                          <span className="text-[11px]">{Math.round(doc.overall_confidence * 100)}%</span>
                        </div>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button
                          onClick={() => handleReprocess(doc.id)}
                          disabled={reprocessingId === doc.id}
                          title="Reprocess Document"
                          className="text-slate-400 hover:text-slate-200 transition-colors"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${reprocessingId === doc.id ? 'animate-spin' : ''}`} />
                        </button>
                        <Link
                          to={`/review?id=${doc.id}`}
                          className="inline-flex items-center gap-1 font-semibold text-brand-400 hover:text-brand-300 transition-colors"
                        >
                          <span>Review</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <strong className="text-slate-200">{docs.length}</strong> of <strong className="text-slate-200">{total}</strong> total documents
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-md bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2">
              Page <strong className="text-slate-200">{page}</strong> of <strong className="text-slate-200">{pages}</strong>
            </span>
            <button
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page >= pages}
              className="p-1.5 rounded-md bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

