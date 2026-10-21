import React, { useState } from 'react';
import { X, Send, Activity, ShieldCheck, AlertCircle, FileText, Globe } from 'lucide-react';
import { HydrogenPolicyData } from '../config/genlayer';

interface SubmitTelemetryModalProps {
  isOpen: boolean;
  policy: HydrogenPolicyData | null;
  onClose: () => void;
  onSubmit: (policyId: string, feedUrl: string) => Promise<void>;
  isSubmitting: boolean;
}

export const SubmitTelemetryModal: React.FC<SubmitTelemetryModalProps> = ({
  isOpen,
  policy,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const [feedUrl, setFeedUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !policy) return null;

  const presets = [
    {
      title: 'TÜV SÜD — ISO 14687 Certified Green H₂',
      desc: '99.98% purity, 1.25 kg CO₂e/kg, 100% offshore wind',
      url: 'https://tuvsud.com/api/v2/certifications/h2_purity_rotterdam01.json',
      color: 'border-puregreen-emerald/50 text-puregreen-emerald',
    },
    {
      title: 'DNV — Partial Grid Mixing (50% Penalty)',
      desc: '99.97% purity, 3.20 kg CO₂e/kg, 18% peaking fossil mix',
      url: 'https://dnv.com/reports/texas_h2_carbon_intensity.json',
      color: 'border-penalty-amber/50 text-penalty-amber',
    },
    {
      title: 'Bureau Veritas — Gray H₂ SMR Detected',
      desc: '98.50% purity, 9.50 kg CO₂e/kg fossil methane breach',
      url: 'https://bureauveritas.com/h2/bavaria_chromatography.json',
      color: 'border-graybreach-crimson/50 text-graybreach-crimson',
    },
    {
      title: 'Unaccredited Domain (Rejection Demo)',
      desc: 'Fails whitelist check: Reverts on-chain',
      url: 'https://my-unverified-energy-blog.com/h2_report.json',
      color: 'border-slate-600 text-slate-400',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const clean = feedUrl.trim();
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      setError('Telemetry endpoint must be a valid HTTP/HTTPS URL.');
      return;
    }

    try {
      await onSubmit(policy.policy_id, clean);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Telemetry submission failed.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-xl bg-h2dark-800 border border-yellow-400/40 rounded-2xl p-6 sm:p-8 shadow-console my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-h2dark-700/80 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-yellow-400/10 border border-yellow-400/30 flex items-center justify-center text-yellow-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading font-bold text-lg text-slate-100">
                Submit Production Telemetry
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Policy #{policy.policy_id} · Facility: {policy.facility_id}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-h2dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Accredited Auditor Notice */}
        <div className="mb-5 p-3 rounded-xl bg-h2dark-850 border border-h2dark-700 text-xs font-mono text-slate-400 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-cryo-cyan shrink-0 mt-0.5" />
          <div>
            <span className="text-slate-200 font-semibold block mb-0.5">
              Accredited Hydrogen Testing Whitelist
            </span>
            <span>
              Endpoints must originate from registered testing agencies: TÜV SÜD, DNV, Bureau Veritas, NREL, CertifHy, DOE, or Fraunhofer.
            </span>
          </div>
        </div>

        {/* Preset Endpoints */}
        <div className="mb-6">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-2">
            Select Live Laboratory Report Preset
          </span>
          <div className="space-y-2">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setFeedUrl(p.url);
                  setError(null);
                }}
                className="w-full text-left p-3 rounded-xl bg-h2dark-850 border border-h2dark-700 hover:border-cryo-cyan/50 transition-all flex items-center justify-between group"
              >
                <div>
                  <div className={`font-semibold text-xs ${p.color}`}>{p.title}</div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">{p.desc}</div>
                </div>
                <Globe className="w-4 h-4 text-slate-500 group-hover:text-cryo-cyan shrink-0 ml-2" />
              </button>
            ))}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mb-6 p-3 rounded-xl bg-graybreach-crimson/15 border border-graybreach-crimson/40 text-graybreach-crimson text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              Gas Chromatography / Hourly Renewable Telemetry URL <span className="text-graybreach-crimson">*</span>
            </label>
            <input
              type="url"
              required
              placeholder="https://tuvsud.com/api/v2/certifications/h2_purity.json"
              value={feedUrl}
              onChange={(e) => setFeedUrl(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-yellow-400 focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-600"
            />
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-h2dark-700/80 mt-6">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl bg-h2dark-850 hover:bg-h2dark-750 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !feedUrl.trim()}
              className="px-6 py-2.5 rounded-xl bg-yellow-400 hover:bg-yellow-500 text-h2dark-950 font-heading font-semibold text-xs transition-all disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Transmitting...' : 'Submit Telemetry'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
