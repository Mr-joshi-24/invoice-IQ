import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  X, 
  ArrowRight,
  ShieldCheck,
  FileCheck2
} from 'lucide-react';
import { uploadDocuments } from '../api';

export default function Upload() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles) => {
    const validExtensions = ['pdf', 'png', 'jpg', 'jpeg'];
    const valid = newFiles.filter((f) => {
      const ext = f.name.split('.').pop().toLowerCase();
      return validExtensions.includes(ext);
    });

    if (valid.length < newFiles.length) {
      setError('Some files were ignored because only PDF, PNG, and JPG/JPEG are supported.');
    } else {
      setError(null);
    }

    setFiles((prev) => [...prev, ...valid]);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadSubmit = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setProgress(15);
    setError(null);

    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const result = await uploadDocuments(formData, (progressEvent) => {
        const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
        setProgress(percent);
      });
      setUploadResult(result);
      setFiles([]);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload document(s).');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Upload Documents</h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload PDF invoices or high-resolution images. Files are parsed via PaddleOCR and analyzed for anomaly patterns.
        </p>
      </div>

      {/* Success Notification Banner */}
      {uploadResult && (
        <div className="p-5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold">Successfully uploaded {uploadResult.length} document(s)!</p>
              <p className="text-xs text-emerald-400/80 mt-0.5">
                Background processing pipeline triggered. Real-time extraction and anomaly scoring underway.
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/documents')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-sm transition-colors"
          >
            <span>View Documents</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Error Callout */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
        className="p-12 rounded-2xl border-2 border-dashed border-slate-700 hover:border-brand-500 bg-slate-950/60 hover:bg-slate-900/40 transition-all cursor-pointer flex flex-col items-center justify-center text-center group"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
          className="hidden"
        />
        <div className="w-16 h-16 rounded-2xl bg-brand-500/10 group-hover:bg-brand-500/20 text-brand-400 flex items-center justify-center mb-4 transition-colors">
          <UploadCloud className="w-8 h-8" />
        </div>
        <h3 className="text-base font-bold text-slate-100 group-hover:text-brand-300 transition-colors">
          Drop invoice files here, or <span className="text-brand-400 underline">browse</span>
        </h3>
        <p className="text-xs text-slate-400 mt-2">
          Supports multi-page PDF, PNG, JPG, JPEG (Up to 15 MB per file)
        </p>
        <div className="flex items-center gap-4 mt-6 text-xs text-slate-400">
          <span className="flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5 text-brand-400" /> Magic-byte verification</span>
          <span>•</span>
          <span className="flex items-center gap-1"><FileCheck2 className="w-3.5 h-3.5 text-emerald-400" /> OCR deskew & auto-contrast</span>
        </div>
      </div>

      {/* Queued Files List */}
      {files.length > 0 && (
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-slate-200">
              Queued Documents ({files.length})
            </h4>
            <button
              onClick={() => setFiles([])}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Clear Queue
            </button>
          </div>

          <div className="divide-y divide-slate-800/80 max-h-60 overflow-y-auto">
            {files.map((file, idx) => (
              <div key={idx} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3 truncate">
                  <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
                    <FileText className="w-4 h-4 text-brand-400" />
                  </div>
                  <div className="truncate">
                    <p className="font-semibold text-slate-200 truncate">{file.name}</p>
                    <p className="text-[11px] text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(idx)}
                  className="p-1 rounded-md text-slate-400 hover:text-rose-400 hover:bg-slate-900 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="space-y-1.5 pt-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Uploading and initializing pipeline...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-brand-500 transition-all duration-200"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Upload Action Button */}
          <div className="pt-2 flex justify-end">
            <button
              onClick={handleUploadSubmit}
              disabled={uploading}
              className="px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-brand-600/20 transition-all flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4" />
              <span>{uploading ? 'Processing Ingestion...' : `Upload ${files.length} Document(s)`}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

