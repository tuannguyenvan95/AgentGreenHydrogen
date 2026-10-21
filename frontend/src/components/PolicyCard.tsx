import React, { useState } from 'react';
import {
  ShieldCheck,
  Activity,
  Flame,
  Wind,
  Clock,
  ExternalLink,
  ChevronRight,
  Eye,
  Scale,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import {
  HydrogenPolicyData,
  STATUS_POLICY_OPEN,
  STATUS_TELEMETRY_SUBMITTED,
  STATUS_AWAITING_PAYOUT,
  STATUS_SETTLED_CERTIFIED_FULL,
  STATUS_SETTLED_PARTIAL,
  STATUS_SETTLED_REJECTED,
  STATUS_DISPUTED,
  STATUS_EXPIRED_RECLAIMED,
  STATUS_UNRESOLVED,
} from '../config/genlayer';
import {
  formatGen,
  formatAddress,
  formatPurity,
  formatCarbonIntensity,
  formatTimestamp,
  STATUS_LABELS,
} from '../utils/formatters';

interface PolicyCardProps {
  policy: HydrogenPolicyData;
  walletAddress: string | null;
  onOpenSubmitTelemetry: (policy: HydrogenPolicyData) => void;
  onOpenInspector: (policy: HydrogenPolicyData) => void;
  onOpenAppeal: (policy: HydrogenPolicyData) => void;
  onAdjudicate: (policyId: string) => Promise<void>;
  onAdjudicateAppeal: (policyId: string) => Promise<void>;
  onFinalize: (policyId: string) => Promise<void>;
  onReclaim: (policyId: string) => Promise<void>;
  isProcessing: boolean;
}

export const PolicyCard: React.FC<PolicyCardProps> = ({
  policy,
  walletAddress,
  onOpenSubmitTelemetry,
  onOpenInspector,
  onOpenAppeal,
  onAdjudicate,
  onAdjudicateAppeal,
  onFinalize,
  onReclaim,
  isProcessing,
}) => {
  const statusMeta = STATUS_LABELS[policy.status] || STATUS_LABELS[0];
  const escrowDisplay = formatGen(policy.escrow_amount);
  const isPlant = walletAddress && walletAddress.toLowerCase() === policy.electrolyzer_plant.toLowerCase();
  const isSponsor = walletAddress && walletAddress.toLowerCase() === policy.sponsor.toLowerCase();

  const isFull = policy.verdict === 'GREEN_HYDROGEN_CERTIFIED_FULL';
  const isPartial = policy.verdict === 'PARTIAL_CARBON_INTENSITY_PENALTY';
  const isRejected = policy.verdict === 'GRAY_HYDROGEN_REJECTED';

  return (
    <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-6 shadow-console hover:border-h2dark-600 transition-all flex flex-col justify-between">
      {/* Top Card Info */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-cryo-cyan">
                POLICY #{policy.policy_id}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${statusMeta.bg} ${statusMeta.color} border ${statusMeta.border}`}
              >
                {statusMeta.label}
              </span>
            </div>
            <h4 className="font-heading font-bold text-base text-slate-100 mt-1 flex items-center gap-1.5">
              {policy.facility_id}
            </h4>
          </div>

          <div className="text-right">
            <span className="text-[10px] font-mono text-slate-400 block uppercase">Subsidy Escrow</span>
            <div className="text-lg font-mono font-bold text-puregreen-emerald">
              {escrowDisplay} <span className="text-xs text-slate-400 font-semibold">GEN</span>
            </div>
          </div>
        </div>

        {/* Stakeholder Addresses */}
        <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-h2dark-850 border border-h2dark-750 text-xs font-mono mb-4">
          <div>
            <span className="text-[10px] text-slate-500 block uppercase">Climate Sponsor</span>
            <span className="text-slate-300 font-semibold" title={policy.sponsor}>
              {formatAddress(policy.sponsor)}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 block uppercase">Electrolyzer Plant</span>
            <span className="text-cryo-cyan font-semibold" title={policy.electrolyzer_plant}>
              {formatAddress(policy.electrolyzer_plant)}
            </span>
          </div>
        </div>

        {/* Primary Metrics: Purity & Carbon Intensity */}
        <div className="space-y-3 mb-4">
          {/* Purity Indicator */}
          <div>
            <div className="flex items-center justify-between text-xs font-mono mb-1">
              <span className="text-slate-400 flex items-center gap-1">
                <Flame className="w-3 h-3 text-puregreen-emerald" />
                H₂ Purity
              </span>
              <span className="text-slate-200 font-bold">
                {policy.measured_purity_bps > 0
                  ? formatPurity(policy.measured_purity_bps)
                  : `Target ≥ ${formatPurity(policy.min_purity_bps)}`}
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-1.5 overflow-hidden border border-h2dark-750">
              <div
                className={`h-full ${
                  policy.measured_purity_bps >= policy.min_purity_bps
                    ? 'bg-puregreen-emerald'
                    : policy.measured_purity_bps > 0
                    ? 'bg-graybreach-crimson'
                    : 'bg-slate-600'
                }`}
                style={{
                  width: `${
                    policy.measured_purity_bps > 0
                      ? Math.min(100, (policy.measured_purity_bps / 10000) * 100)
                      : 0
                  }%`,
                }}
              ></div>
            </div>
          </div>

          {/* Carbon Intensity Indicator */}
          <div>
            <div className="flex items-center justify-between text-xs font-mono mb-1">
              <span className="text-slate-400 flex items-center gap-1">
                <Wind className="w-3 h-3 text-cryo-cyan" />
                Carbon Intensity
              </span>
              <span className="text-slate-200 font-bold">
                {policy.measured_carbon_intensity_g > 0
                  ? formatCarbonIntensity(policy.measured_carbon_intensity_g)
                  : `Limit ≤ ${formatCarbonIntensity(policy.max_carbon_intensity_g_co2)}`}
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-1.5 overflow-hidden border border-h2dark-750">
              <div
                className={`h-full ${
                  policy.measured_carbon_intensity_g <= policy.max_carbon_intensity_g_co2
                    ? 'bg-puregreen-emerald'
                    : policy.measured_carbon_intensity_g <= policy.max_carbon_intensity_g_co2 * 2
                    ? 'bg-penalty-amber'
                    : 'bg-graybreach-crimson'
                }`}
                style={{
                  width: `${
                    policy.measured_carbon_intensity_g > 0
                      ? Math.min(
                          100,
                          (policy.measured_carbon_intensity_g /
                            (policy.max_carbon_intensity_g_co2 * 2.5 || 5000)) *
                            100
                        )
                      : 0
                  }%`,
                }}
              ></div>
            </div>
          </div>
        </div>

        {/* Reason / Verdict snippet */}
        <p className="text-xs text-slate-400 font-mono mb-4 line-clamp-2 italic">
          "{policy.reason || 'No telemetry processed yet.'}"
        </p>
      </div>

      {/* Card Action Buttons */}
      <div className="pt-4 border-t border-h2dark-700/80 flex flex-wrap items-center gap-2">
        {/* Status 0 or 8: Submit Telemetry */}
        {(policy.status === STATUS_POLICY_OPEN || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onOpenSubmitTelemetry(policy)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2 rounded-xl bg-yellow-400/20 hover:bg-yellow-400/30 text-yellow-400 border border-yellow-400/40 text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Submit Telemetry</span>
          </button>
        )}

        {/* Status 1 or 8: Run AI Quality Adjudication */}
        {(policy.status === STATUS_TELEMETRY_SUBMITTED || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onAdjudicate(policy.policy_id)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2 rounded-xl bg-cryo-cyan hover:bg-cryo-deep text-h2dark-950 text-xs font-heading font-semibold transition-all shadow-cryo-glow flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Adjudicate Quality</span>
          </button>
        )}

        {/* Inspect Evidence Button */}
        {policy.measured_purity_bps > 0 && (
          <button
            onClick={() => onOpenInspector(policy)}
            className="px-3 py-2 rounded-xl bg-h2dark-850 hover:bg-h2dark-750 text-slate-300 border border-h2dark-700 text-xs font-mono transition-all flex items-center justify-center gap-1.5"
            title="Inspect Chromatography & Consensus Evidence"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Inspect</span>
          </button>
        )}

        {/* Status 2: Appeal Verdict within cooling off */}
        {policy.status === STATUS_AWAITING_PAYOUT && (
          <>
            <button
              onClick={() => onOpenAppeal(policy)}
              disabled={isProcessing}
              className="flex-1 px-3 py-2 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5"
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Appeal (72s)</span>
            </button>
            <button
              onClick={() => onFinalize(policy.policy_id)}
              disabled={isProcessing}
              className="flex-1 px-3 py-2 rounded-xl bg-puregreen-emerald hover:bg-puregreen-dark text-h2dark-950 text-xs font-heading font-semibold transition-all shadow-green-glow flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Finalize Payout</span>
            </button>
          </>
        )}

        {/* Status 6: Adjudicate Appeal */}
        {policy.status === STATUS_DISPUTED && (
          <button
            onClick={() => onAdjudicateAppeal(policy.policy_id)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-100 text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Judge Appellate Review</span>
          </button>
        )}

        {/* Reclaim expired button */}
        {(policy.status === STATUS_POLICY_OPEN || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onReclaim(policy.policy_id)}
            disabled={isProcessing}
            className="px-2.5 py-2 rounded-xl bg-h2dark-850 hover:bg-h2dark-750 text-slate-400 hover:text-slate-200 border border-h2dark-700 text-xs font-mono transition-all"
            title="Reclaim Escrow if coverage duration expired"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
