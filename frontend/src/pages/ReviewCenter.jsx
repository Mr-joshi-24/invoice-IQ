import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  CheckCircle2, 
  XCircle, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  ChevronLeft, 
  ChevronRight,
  ShieldAlert, 
  AlertTriangle, 
  FileText, 
  Sparkles,
  ArrowLeft
} from 'lucide-react';
import { getDocument, submitReview, getPagePreviewUrl } from '../api';

export default function ReviewCenter() {
  const [searchParams] = useSearchParams();
  const documentId = searchParams.get('id');
  const navigate = useNavigate();

  const [document, setDocument] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [activeHoverField, setActiveHoverField] = useState(null);

  // Form states and dirty tracking
  const [formValues, setFormValues] = useState({
    vendor_name: '',
    invoice_number: '',
    invoice_date: '',
    gstin: '',
    subtotal: '',
    tax_amount: '',
    total_amount: ''
  });
  const [initialValues, setInitialValues] = useState({});
  const [reviewerNotes, setReviewerNotes] = useState('');

  const fetchDocument = async () => {
    if (!documentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const doc = await getDocument(documentId);
      setDocument(doc);

      // Populate form values and initial baseline for dirty checking
      const initial = {
        vendor_name: '',
        invoice_number: '',
        invoice_date: '',
        gstin: '',
        subtotal: '',
        tax_amount: '',
        total_amount: ''
      };
      (doc.extracted_fields || []).forEach((f) => {
        initial[f.field_name] = f.extracted_value || '';
      });
      setFormValues(initial);
      setInitialValues(initial);
    } catch (err) {
      console.error('Failed to load document for review:', err);
      setDocument(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [documentId]);

  const handleInputChange = (field, value) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
  };

  const handleReviewAction = async (action) => {
    setSubmitting(true);
    try {
      // Calculate only fields that the reviewer actually modified
      const dirtyFields = {};
      Object.keys(formValues).forEach((key) => {
        const initialVal = (initialValues[key] || '').trim();
        const currentVal = (formValues[key] || '').trim();
        if (currentVal !== initialVal) {
          dirtyFields[key] = currentVal;
        }
      });

      await submitReview(documentId, {
        reviewer_id: 'lead_auditor',
        review_action: action,
        corrected_fields: dirtyFields,
        reviewer_notes: reviewerNotes
      });
      navigate('/documents');
    } catch (err) {
      console.error('Failed to submit review:', err);
      alert('Review submission failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  if (!documentId) {
    return (
      <div className="p-12 text-center text-slate-400">
        <FileText className="w-12 h-12 mx-auto mb-3 text-slate-400 opacity-60" />
        <h3 className="text-base font-bold text-slate-200">No Document Selected for Review</h3>
        <p className="text-xs text-slate-400 mt-1">Please select an invoice from the documents list to review.</p>
        <button
          onClick={() => navigate('/documents')}
          className="mt-4 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-sm inline-flex items-center gap-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Browse Documents</span>
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-400">Loading document review canvas...</p>
        </div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="p-12 text-center text-slate-400 max-w-md mx-auto">
        <AlertTriangle className="w-12 h-12 mx-auto mb-3 text-amber-400 opacity-80" />
        <h3 className="text-base font-bold text-slate-200">Document Not Found</h3>
        <p className="text-xs text-slate-400 mt-1">
          The requested document ID (<code className="text-slate-300 font-mono text-[11px]">{documentId}</code>) could not be located or has been deleted.
        </p>
        <button
          onClick={() => navigate('/documents')}
          className="mt-4 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 shadow-sm inline-flex items-center gap-2"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Documents</span>
        </button>
      </div>
    );
  }

  const fieldsList = [
    { key: 'vendor_name', label: 'Vendor Name', type: 'text' },
    { key: 'invoice_number', label: 'Invoice Number', type: 'text' },
    { key: 'invoice_date', label: 'Invoice Date', type: 'text' },
    { key: 'gstin', label: 'GSTIN (Indian Tax ID)', type: 'text' },
    { key: 'subtotal', label: 'Subtotal Amount', type: 'number' },
    { key: 'tax_amount', label: 'Tax Amount', type: 'number' },
    { key: 'total_amount', label: 'Total Amount', type: 'number' }
  ];

  const totalPages = document?.page_count || 1;

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col lg:flex-row overflow-hidden bg-slate-900">
      {/* LEFT COLUMN: Document Canvas & Bounding Boxes (55% width) */}
      <div className="lg:w-[55%] flex flex-col border-r border-slate-800 bg-slate-950/90 relative">
        {/* Canvas Toolbar */}
        <div className="h-12 px-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 text-xs">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-200 truncate max-w-[200px]" title={document.original_filename}>
              {document.original_filename}
            </span>
            <span className="text-[11px] text-slate-400">
              Page {currentPage} of {totalPages}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-30"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-30"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <span className="h-4 w-[1px] bg-slate-800 mx-1"></span>
            <button
              onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-[11px] font-mono text-slate-400 w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1.0)}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Interactive Viewer Viewport */}
        <div className="flex-1 overflow-auto p-6 flex items-center justify-center bg-slate-950">
          <div 
            className="relative shadow-2xl rounded-lg border border-slate-800 transition-transform origin-top duration-150 inline-block bg-white"
            style={{ transform: `scale(${zoom})` }}
          >
            {/* Rendered Preview Image */}
            <img
              src={getPagePreviewUrl(documentId, currentPage)}
              alt="Document Preview Page"
              className="max-w-[650px] object-contain block pointer-events-none select-none"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />

            {/* Normalized Bounding Box Overlays */}
            {(document.extracted_fields || [])
              .filter((f) => f.bounding_box && f.page_number === currentPage)
              .map((f) => {
                const b = f.bounding_box;
                const isHovered = activeHoverField === f.field_name;
                const style = {
                  left: `${b.x1 * 100}%`,
                  top: `${b.y1 * 100}%`,
                  width: `${(b.x2 - b.x1) * 100}%`,
                  height: `${(b.y2 - b.y1) * 100}%`
                };
                return (
                  <div
                    key={f.id || f.field_name}
                    style={style}
                    onMouseEnter={() => setActiveHoverField(f.field_name)}
                    onMouseLeave={() => setActiveHoverField(null)}
                    className={`absolute rounded transition-all cursor-pointer ${
                      isHovered
                        ? 'border-2 border-brand-500 bg-brand-500/25 ring-2 ring-brand-400/50 z-10'
                        : 'border border-blue-500/50 bg-blue-500/10 hover:border-brand-400 hover:bg-brand-500/20'
                    }`}
                  >
                    {isHovered && (
                      <span className="absolute -top-5 left-0 px-1.5 py-0.5 rounded text-[9px] font-bold bg-brand-600 text-white whitespace-nowrap shadow-sm">
                        {f.field_name.replace('_', ' ')}: {f.extracted_value}
                      </span>
                    )}
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Extracted Fields & Review Actions (45% width) */}
      <div className="lg:w-[45%] flex flex-col bg-slate-900 overflow-y-auto">
        <div className="p-6 space-y-6">
          {/* Header Summary Card */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Document Status</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  document.processing_status === 'PROCESSED'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                }`}>
                  {document.processing_status}
                </span>
                <span className="text-xs text-slate-400">
                  Confidence: <strong className="text-slate-100">{Math.round((document.overall_confidence || 0) * 100)}%</strong>
                </span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[11px] text-slate-400 block">Uploaded</span>
              <span className="text-xs font-medium text-slate-300">
                {document.created_at ? new Date(document.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>

          {/* Anomaly Alert Callout */}
          {document.anomaly_result?.is_anomalous && (
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 space-y-1">
              <div className="flex items-center gap-2 font-semibold text-xs text-purple-200">
                <ShieldAlert className="w-4 h-4 text-purple-400" />
                <span>Financial Anomaly Detected (Score: {document.anomaly_result.anomaly_score})</span>
              </div>
              <p className="text-xs text-purple-300/90 leading-relaxed">
                {document.anomaly_result.explanation}
              </p>
            </div>
          )}

          {/* Validation Checks Status List */}
          {document.validation_results && document.validation_results.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Automated Integrity Checks
              </h4>
              <div className="space-y-1.5">
                {document.validation_results.map((v) => (
                  <div key={v.id || v.rule_name} className="flex items-start gap-2.5 text-xs">
                    {v.status === 'PASSED' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                    ) : v.status === 'WARNING' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-rose-400 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <span className="font-semibold text-slate-200">{v.rule_name}: </span>
                      <span className="text-slate-400">{v.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Editable Invoice Fields Form */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Extracted Invoice Fields
              </h4>
              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-brand-400" />
                Hover field to highlight OCR region
              </span>
            </div>

            <div className="space-y-3">
              {fieldsList.map((item) => {
                const fieldMeta = (document.extracted_fields || []).find((f) => f.field_name === item.key);
                const confPercent = fieldMeta ? Math.round(fieldMeta.confidence_score * 100) : 0;
                const method = fieldMeta?.extraction_method || 'HYBRID';
                const isHovered = activeHoverField === item.key;
                const isModified = (formValues[item.key] || '').trim() !== (initialValues[item.key] || '').trim();

                return (
                  <div
                    key={item.key}
                    onMouseEnter={() => setActiveHoverField(item.key)}
                    onMouseLeave={() => setActiveHoverField(null)}
                    className={`p-3 rounded-lg border transition-all ${
                      isHovered
                        ? 'border-brand-500 bg-brand-500/5'
                        : isModified
                        ? 'border-brand-500/50 bg-slate-950/80 ring-1 ring-brand-500/20'
                        : 'border-slate-800 bg-slate-950/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-semibold text-slate-300">
                          {item.label}
                        </label>
                        {isModified && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold uppercase">
                            Modified
                          </span>
                        )}
                        {fieldMeta?.is_corrected && !isModified && (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-bold uppercase">
                            Verified
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                          {method}
                        </span>
                        <span className={`text-[10px] font-semibold ${
                          confPercent >= 85 ? 'text-emerald-400' : confPercent >= 70 ? 'text-amber-400' : 'text-rose-400'
                        }`}>
                          {confPercent}% Conf
                        </span>
                      </div>
                    </div>
                    <input
                      type={item.type}
                      value={formValues[item.key] || ''}
                      onChange={(e) => handleInputChange(item.key, e.target.value)}
                      className="w-full px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-brand-500 font-medium"
                    />
                    {fieldMeta?.original_value && fieldMeta.original_value !== fieldMeta.extracted_value && (
                      <p className="text-[10px] text-slate-400 mt-1 italic">
                        Raw OCR Value: &ldquo;{fieldMeta.original_value}&rdquo;
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Reviewer Notes Input */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Auditor Notes</label>
            <textarea
              rows={2}
              value={reviewerNotes}
              onChange={(e) => setReviewerNotes(e.target.value)}
              placeholder="Add optional notes explaining your approval or correction rationale..."
              className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* Review Action Controls */}
          <div className="pt-2 flex items-center gap-3">
            <button
              onClick={() => handleReviewAction('REJECTED')}
              disabled={submitting}
              className="flex-1 py-2.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 text-xs font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" />
              <span>Reject Document</span>
            </button>
            <button
              onClick={() => handleReviewAction('APPROVED')}
              disabled={submitting}
              className="flex-1 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Approve & Save Corrections</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
