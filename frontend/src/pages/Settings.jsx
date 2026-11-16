import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Save, CheckCircle2, Shield, Sliders, Info } from 'lucide-react';
import { getSettings, updateSettings } from '../api';

export default function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    getSettings()
      .then(setConfig)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      await updateSettings({
        confidence_threshold: parseFloat(config.confidence_threshold),
        anomaly_contamination: parseFloat(config.anomaly_contamination),
        max_upload_size_mb: parseInt(config.max_upload_size_mb, 10)
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Save settings failed:', err);
      alert('Failed to save settings: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-xs text-slate-400">Loading system settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">System Settings</h1>
        <p className="text-sm text-slate-400 mt-0.5">Configure document validation thresholds, anomaly detection sensitivity, and file constraints.</p>
      </div>

      {saveSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-2 text-xs font-semibold">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>System configuration updated successfully.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Confidence Threshold Configuration Card */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Sliders className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-bold">Document Confidence Threshold</h3>
          </div>
          <p className="text-xs text-slate-400">
            Documents with overall field extraction confidence below this score are automatically routed to the Human Review Center for manual audit.
          </p>
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Review Threshold</span>
              <span className="font-bold text-brand-400 text-sm">
                {Math.round((config?.confidence_threshold || 0.8) * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.95"
              step="0.05"
              value={config?.confidence_threshold || 0.8}
              onChange={(e) => setConfig({ ...config, confidence_threshold: parseFloat(e.target.value) })}
              className="w-full accent-brand-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>50% (Permissive)</span>
              <span>80% (Recommended)</span>
              <span>95% (Strict)</span>
            </div>
          </div>
        </div>

        {/* Anomaly Detection Sensitivity */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Shield className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold">Isolation Forest Anomaly Sensitivity</h3>
          </div>
          <p className="text-xs text-slate-400">
            Contamination hyperparameter representing the expected percentage of billing anomalies and outliers in your invoice flow.
          </p>
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Contamination Ratio</span>
              <span className="font-bold text-purple-400 text-sm">
                {((config?.anomaly_contamination || 0.05) * 100).toFixed(1)}%
              </span>
            </div>
            <input
              type="range"
              min="0.01"
              max="0.15"
              step="0.01"
              value={config?.anomaly_contamination || 0.05}
              onChange={(e) => setConfig({ ...config, anomaly_contamination: parseFloat(e.target.value) })}
              className="w-full accent-purple-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>1% (Low sensitivity)</span>
              <span>5% (Default balanced)</span>
              <span>15% (High sensitivity)</span>
            </div>
          </div>
        </div>

        {/* File Ingestion Constraints */}
        <div className="p-6 rounded-xl bg-slate-950/80 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-slate-200">
            <Info className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold">File Ingestion Constraints</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-medium">Max Upload Size (MB)</label>
              <input
                type="number"
                min="1"
                max="50"
                value={config?.max_upload_size_mb || 15}
                onChange={(e) => setConfig({ ...config, max_upload_size_mb: parseInt(e.target.value, 10) })}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 font-medium">Supported Formats</label>
              <input
                type="text"
                disabled
                value={(config?.allowed_extensions || ['pdf', 'png', 'jpg', 'jpeg']).join(', ').toUpperCase()}
                className="w-full px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400 cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-600/20 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

