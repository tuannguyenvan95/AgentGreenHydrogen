import React from 'react';
import {
  X,
  FileCheck,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  Hash,
  Activity,
  Flame,
  Wind,
} from 'lucide-react';
import { HydrogenPolicyData } from '../config/genlayer';
import { formatPurity, formatCarbonIntensity, STATUS_LABELS } from '../utils/formatters';

interface QualityInspectorModalProps {
  isOpen: boolean;
  policy: HydrogenPolicyData | null;
  onClose: () => void;
}

export const QualityInspectorModal: React.FC<QualityInspectorModalProps> = ({
  isOpen,
  policy,
  onClose,
}) => {
  if (!isOpen || !policy) return null;

  const statusMeta = STATUS_LABELS[policy.status] || STATUS_LABELS[0];
  const isFull = policy.verdict === 'GREEN_HYDROGEN_CERTIFIED_FULL';
  const isPartial = policy.verdict === 'PARTIAL_CARBON_INTENSITY_PENALTY';
  const isRejected = policy.verdict === 'GRAY_HYDROGEN_REJECTED';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-h2dark-800 border border-h2dark-700 rounded-2xl p-6 sm:p-8 shadow-console my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-h2dark-700/80 mb-6">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                isFull
                  ? 'bg-puregreen-emerald/15 text-puregreen-emerald border border-puregreen-emerald/40'
                  : isPartial
                  ? 'bg-penalty-amber/15 text-penalty-amber border border-penalty-amber/40'
                  : isRejected
                  ? 'bg-graybreach-crimson/15 text-graybreach-crimson border border-graybreach-crimson/40'
                  : 'bg-cryo-cyan/15 text-cryo-cyan border border-cryo-cyan/40'
              }`}
            >
              {isFull ? (
                <ShieldCheck className="w-5 h-5" />
              ) : isPartial ? (
                <AlertTriangle className="w-5 h-5" />
              ) : (
                <ShieldAlert className="w-5 h-5" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-heading font-bold text-lg text-slate-100">
                  On-Chain AI Quality Adjudication
                </h2>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${statusMeta.bg} ${statusMeta.color} border ${statusMeta.border}`}
                >
                  {statusMeta.label}
                </span>
              </div>
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

        {/* Adjudication Verdict Highlight */}
        <div
          className={`p-4 rounded-xl border mb-6 ${
            isFull
              ? 'bg-puregreen-emerald/10 border-puregreen-emerald/40 text-puregreen-emerald'
              : isPartial
              ? 'bg-penalty-amber/10 border-penalty-amber/40 text-penalty-amber'
              : isRejected
              ? 'bg-graybreach-crimson/10 border-graybreach-crimson/40 text-graybreach-crimson'
              : 'bg-cryo-cyan/10 border-cryo-cyan/40 text-cryo-cyan'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono uppercase tracking-wider font-semibold">
              Consensus Adjudication Verdict
            </span>
            <span className="text-xs font-mono font-bold">
              Confidence: {policy.confidence}%
            </span>
          </div>
          <div className="text-base sm:text-lg font-heading font-bold tracking-tight">
            {policy.verdict || 'AWAITING_TELEMETRY'}
          </div>
          <p className="text-xs text-slate-300 font-mono mt-2 leading-relaxed">
            {policy.reason || 'Pending AI Hydrogen Jury consensus verification.'}
          </p>
        </div>

        {/* Metric Comparison Table */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {/* Purity Comparison */}
          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
              <span className="flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-puregreen-emerald" />
                Gas Chromatography Purity
              </span>
              <span>Req: {formatPurity(policy.min_purity_bps)}</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-mono font-bold text-slate-100">
                {formatPurity(policy.measured_purity_bps)}
              </span>
              <span className="text-xs font-mono text-slate-400">
                ({policy.measured_purity_bps} bps)
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-2 mt-3 overflow-hidden border border-h2dark-700">
              <div
                className={`h-full transition-all ${
                  policy.measured_purity_bps >= policy.min_purity_bps
                    ? 'bg-puregreen-emerald'
                    : 'bg-graybreach-crimson'
                }`}
                style={{
                  width: `${Math.min(100, (policy.measured_purity_bps / 10000) * 100)}%`,
                }}
              ></div>
            </div>
            <span className="text-[10px] text-slate-500 font-mono mt-1 block">
              ISO 14687 Fuel Cell Threshold: ≥ 99.97% (9997 bps)
            </span>
          </div>

          {/* Carbon Intensity Comparison */}
          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
              <span className="flex items-center gap-1.5">
                <Wind className="w-3.5 h-3.5 text-cryo-cyan" />
                Carbon Intensity (LCA)
              </span>
              <span>Limit: {formatCarbonIntensity(policy.max_carbon_intensity_g_co2)}</span>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-mono font-bold text-slate-100">
                {formatCarbonIntensity(policy.measured_carbon_intensity_g)}
              </span>
              <span className="text-xs font-mono text-slate-400">
                ({policy.measured_carbon_intensity_g}g CO₂e/kg)
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-2 mt-3 overflow-hidden border border-h2dark-700">
              <div
                className={`h-full transition-all ${
                  policy.measured_carbon_intensity_g <= policy.max_carbon_intensity_g_co2
                    ? 'bg-puregreen-emerald'
                    : policy.measured_carbon_intensity_g <= policy.max_carbon_intensity_g_co2 * 2
                    ? 'bg-penalty-amber'
                    : 'bg-graybreach-crimson'
                }`}
                style={{
                  width: `${Math.min(
                    100,
                    (policy.measured_carbon_intensity_g / (policy.max_carbon_intensity_g_co2 * 2.5 || 5000)) * 100
                  )}%`,
                }}
              ></div>
            </div>
            <span className="text-[10px] text-slate-500 font-mono mt-1 block">
              EU RED III Standard: ≤ 2.0 kg CO₂e / kg H₂
            </span>
          </div>
        </div>

        {/* Cryptographic Evidence Snapshot */}
        <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700 space-y-3 mb-6">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1.5">
              <Hash className="w-3.5 h-3.5 text-cryo-cyan" />
              Telemetry SHA-256 Digest
            </span>
            <span className="text-[10px] font-mono text-puregreen-emerald bg-puregreen-emerald/10 px-2 py-0.5 rounded border border-puregreen-emerald/30">
              IMMUTABLE SNAPSHOT
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-h2dark-900 border border-h2dark-750 font-mono text-xs text-slate-300 break-all select-all">
            {policy.evidence_hash || 'No evidence hash committed yet.'}
          </div>

          {policy.chromatography_feed_url && (
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs font-mono text-slate-400">Audited Laboratory URL:</span>
              <a
                href={policy.chromatography_feed_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-mono text-cryo-cyan hover:underline flex items-center gap-1 truncate max-w-xs"
              >
                <span>{policy.chromatography_feed_url}</span>
                <ExternalLink className="w-3 h-3 shrink-0" />
              </a>
            </div>
          )}
        </div>

        {/* Modal Action */}
        <div className="flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-xl bg-h2dark-750 hover:bg-h2dark-700 text-xs font-mono text-slate-200 transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
