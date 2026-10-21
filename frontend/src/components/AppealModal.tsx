import React, { useState } from 'react';
import { X, Scale, AlertTriangle, ShieldCheck, ExternalLink, Send } from 'lucide-react';
import { HydrogenPolicyData } from '../config/genlayer';
import { formatGen } from '../utils/formatters';

interface AppealModalProps {
  isOpen: boolean;
  policy: HydrogenPolicyData | null;
  onClose: () => void;
  onSubmitAppeal: (data: {
    policyId: string;
    reason: string;
    supplementalUrl: string;
    bondWei: string;
  }) => Promise<void>;
  isSubmitting: boolean;
}

export const AppealModal: React.FC<AppealModalProps> = ({
  isOpen,
  policy,
  onClose,
  onSubmitAppeal,
  isSubmitting,
}) => {
  const [reason, setReason] = useState('');
  const [supplementalUrl, setSupplementalUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !policy) return null;

  // 10% dispute bond
  let bondWei = '1';
  let bondDisplay = '0.1';
  try {
    const escrowBig = BigInt(policy.escrow_amount || '0');
    const b = (escrowBig * 10n) / 100n;
    bondWei = b > 0n ? b.toString() : '1';
    bondDisplay = formatGen(bondWei);
  } catch {
    // fallback
  }

  const appealPresets = [
    {
      title: 'Fraunhofer ISE — Battery Storage Hourly Smoothing',
      desc: 'Proves BESS discharged 100% offshore wind during wind lull (1800 g CO₂e/kg)',
      url: 'https://fraunhofer.de/energy/antwerp_corrected_audit.json',
    },
    {
      title: 'TÜV SÜD — Independent Gas Chromatography Recalibration',
      desc: 'Spectrometry sensor recalibration confirms 99.98% fuel cell purity',
      url: 'https://tuvsud.com/api/v2/certifications/recalibrated_spectrometry.json',
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanReason = reason.trim();
    if (cleanReason.length < 10) {
      setError('Please provide a rigorous dispute justification (minimum 10 characters).');
      return;
    }

    const cleanUrl = supplementalUrl.trim();
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      setError('Supplemental report must be a valid accredited HTTP/HTTPS endpoint.');
      return;
    }

    try {
      await onSubmitAppeal({
        policyId: policy.policy_id,
        reason: cleanReason,
        supplementalUrl: cleanUrl,
        bondWei,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Appeal filing failed.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-xl bg-h2dark-800 border border-purple-500/40 rounded-2xl p-6 sm:p-8 shadow-console my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-h2dark-700/80 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading font-bold text-lg text-slate-100">
                Appeal Clean Energy Quality Verdict
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Cooling-Off Window (24 Blocks / ~72s) · 10% Staked Bond
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

        {/* Bond Requirement Alert */}
        <div className="mb-6 p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
          <div className="text-xs font-mono text-slate-300">
            <span className="font-bold text-purple-300 block mb-1">
              Required Appeal Bond: {bondDisplay} GEN (10% of Escrow)
            </span>
            <p className="text-slate-400">
              The bond is fully refunded if your appeal is upheld by the Supreme Appellate Magistrate. If dismissed, the bond is forfeited to the counterparty.
            </p>
          </div>
        </div>

        {/* Supplemental Presets */}
        <div className="mb-6">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 block mb-2">
            Select Accredited Supplemental Evidence
          </span>
          <div className="space-y-2">
            {appealPresets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setSupplementalUrl(p.url);
                  setError(null);
                }}
                className="w-full text-left p-3 rounded-xl bg-h2dark-850 border border-h2dark-700 hover:border-purple-400/50 transition-all"
              >
                <div className="font-semibold text-xs text-purple-300">{p.title}</div>
                <div className="text-[11px] text-slate-400 font-mono mt-0.5">{p.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mb-6 p-3 rounded-xl bg-graybreach-crimson/15 border border-graybreach-crimson/40 text-graybreach-crimson text-xs font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              Supplemental Audit Report URL <span className="text-graybreach-crimson">*</span>
            </label>
            <input
              type="url"
              required
              placeholder="https://fraunhofer.de/energy/antwerp_corrected_audit.json"
              value={supplementalUrl}
              onChange={(e) => setSupplementalUrl(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-purple-400 focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              Dispute Justification & Environmental Rationale <span className="text-graybreach-crimson">*</span>
            </label>
            <textarea
              required
              rows={3}
              placeholder="Specify chemical chromatography recalibration or hourly renewable energy attribution proof..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-purple-400 focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-600"
            ></textarea>
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
              disabled={isSubmitting || !supplementalUrl.trim() || reason.trim().length < 10}
              className="px-6 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-100 font-heading font-semibold text-xs transition-all disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Staking Bond...' : `Stake ${bondDisplay} GEN & Appeal`}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
