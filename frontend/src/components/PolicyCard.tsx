import React, { useState, useEffect } from 'react';
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
  Lock,
  UserCheck,
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

  const cleanWallet = (walletAddress || '').toLowerCase().trim();
  const cleanSponsor = policy.sponsor.toLowerCase().trim();
  const cleanPlant = policy.electrolyzer_plant.toLowerCase().trim();
  const cleanAppellant = (policy.dispute_initiator || '').toLowerCase().trim();

  const isPlant = cleanWallet !== '' && cleanWallet === cleanPlant;
  const isSponsor = cleanWallet !== '' && cleanWallet === cleanSponsor;
  const isAppellant = cleanWallet !== '' && cleanWallet === cleanAppellant;

  // Determine user role tag
  let userRoleBadge = 'OBSERVER';
  let userRoleStyle = 'bg-slate-800 text-slate-400 border-slate-700';
  if (isSponsor) {
    userRoleBadge = 'YOU: SPONSOR FUND';
    userRoleStyle = 'bg-cryo-cyan/20 text-cryo-cyan border-cryo-cyan/40 shadow-cryo-glow';
  } else if (isPlant) {
    userRoleBadge = 'YOU: ELECTROLYZER FACILITY';
    userRoleStyle = 'bg-puregreen-emerald/20 text-puregreen-emerald border-puregreen-emerald/40 shadow-green-glow';
  } else if (isAppellant) {
    userRoleBadge = 'YOU: APPELLANT';
    userRoleStyle = 'bg-purple-500/20 text-purple-300 border-purple-500/40';
  }

  // Live cooling-off countdown
  const [secondsRemaining, setSecondsRemaining] = useState<number>(0);

  useEffect(() => {
    if (policy.status === STATUS_AWAITING_PAYOUT && Number(policy.audit_completed_time) > 0) {
      const calculateRemaining = () => {
        const auditTime = Number(policy.audit_completed_time);
        const now = Math.floor(Date.now() / 1000);
        // GenVM consensus cooling off is 72 seconds
        const expiry = auditTime + 72;
        const diff = expiry - now;
        setSecondsRemaining(diff > 0 ? diff : 0);
      };
      calculateRemaining();
      const interval = setInterval(calculateRemaining, 1000);
      return () => clearInterval(interval);
    } else {
      setSecondsRemaining(0);
    }
  }, [policy.status, policy.audit_completed_time]);

  const coolingOffActive = policy.status === STATUS_AWAITING_PAYOUT && secondsRemaining > 0;
  const coolingOffExpired = policy.status === STATUS_AWAITING_PAYOUT && secondsRemaining === 0;

  return (
    <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-6 shadow-console hover:border-h2dark-600 transition-all flex flex-col justify-between relative group">
      {/* Top Header */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
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

        {/* Dynamic User Role Banner */}
        <div className="mb-4 flex items-center justify-between p-2 rounded-lg bg-h2dark-850 border border-h2dark-750">
          <span className="text-[10px] font-mono uppercase text-slate-500 flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5" />
            Your Permissions
          </span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${userRoleStyle}`}>
            {userRoleBadge}
          </span>
        </div>

        {/* Stakeholder Addresses with Role Highlights */}
        <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-h2dark-850 border border-h2dark-750 text-xs font-mono mb-4">
          <div className={`p-1.5 rounded ${isSponsor ? 'bg-cryo-cyan/10 border border-cryo-cyan/30' : ''}`}>
            <span className="text-[10px] text-slate-500 block uppercase">
              Sponsor Fund {isSponsor && '★'}
            </span>
            <span className="text-slate-300 font-semibold truncate block" title={policy.sponsor}>
              {formatAddress(policy.sponsor)}
            </span>
          </div>
          <div className={`p-1.5 rounded ${isPlant ? 'bg-puregreen-emerald/10 border border-puregreen-emerald/30' : ''}`}>
            <span className="text-[10px] text-slate-500 block uppercase">
              Electrolyzer {isPlant && '★'}
            </span>
            <span className="text-cryo-cyan font-semibold truncate block" title={policy.electrolyzer_plant}>
              {formatAddress(policy.electrolyzer_plant)}
            </span>
          </div>
        </div>

        {/* Cooling-off Countdown Bar (When in Status 2) */}
        {policy.status === STATUS_AWAITING_PAYOUT && (
          <div className="mb-4 p-3 rounded-xl bg-purple-500/10 border border-purple-500/30">
            <div className="flex items-center justify-between text-xs font-mono mb-1.5">
              <span className="flex items-center gap-1.5 text-purple-300 font-bold">
                <Clock className="w-3.5 h-3.5 animate-spin" />
                Cooling-Off Challenge Window
              </span>
              <span className={`font-bold ${secondsRemaining > 0 ? 'text-solar-lime' : 'text-puregreen-emerald'}`}>
                {secondsRemaining > 0 ? `${secondsRemaining}s remaining` : 'WINDOW CONCLUDED'}
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-1.5 overflow-hidden border border-purple-500/20">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-solar-lime transition-all duration-1000"
                style={{ width: `${Math.max(0, Math.min(100, (secondsRemaining / 72) * 100))}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1.5">
              <span>24 blocks dispute window</span>
              <span>{coolingOffActive ? 'Appeals accepted' : 'Ready for final settlement'}</span>
            </div>
          </div>
        )}

        {/* Chemical Purity & LCA Carbon Gauges */}
        <div className="space-y-3 mb-4">
          {/* Purity */}
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
            <div className="w-full bg-h2dark-900 rounded-full h-2 overflow-hidden border border-h2dark-750">
              <div
                className={`h-full transition-all ${
                  policy.measured_purity_bps >= policy.min_purity_bps
                    ? 'bg-puregreen-emerald shadow-green-glow'
                    : policy.measured_purity_bps > 0
                    ? 'bg-graybreach-crimson'
                    : 'bg-slate-700'
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
            <span className="text-[10px] font-mono text-slate-500 mt-0.5 block">
              ISO 14687:2019 Type I Grade D Standard
            </span>
          </div>

          {/* Carbon Intensity */}
          <div>
            <div className="flex items-center justify-between text-xs font-mono mb-1">
              <span className="text-slate-400 flex items-center gap-1">
                <Wind className="w-3 h-3 text-cryo-cyan" />
                Carbon Footprint
              </span>
              <span className="text-slate-200 font-bold">
                {policy.measured_carbon_intensity_g > 0
                  ? formatCarbonIntensity(policy.measured_carbon_intensity_g)
                  : `Limit ≤ ${formatCarbonIntensity(policy.max_carbon_intensity_g_co2)}`}
              </span>
            </div>
            <div className="w-full bg-h2dark-900 rounded-full h-2 overflow-hidden border border-h2dark-750">
              <div
                className={`h-full transition-all ${
                  policy.measured_carbon_intensity_g <= policy.max_carbon_intensity_g_co2
                    ? 'bg-puregreen-emerald shadow-green-glow'
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
            <span className="text-[10px] font-mono text-slate-500 mt-0.5 block">
              EU RED III Standard: ≤ 2.0 kg CO₂e / kg H₂
            </span>
          </div>
        </div>

        {/* AI Rationale Snippet */}
        <p className="text-xs text-slate-400 font-mono mb-4 line-clamp-2 italic bg-h2dark-850/50 p-2 rounded-lg border border-h2dark-750">
          "{policy.reason || 'Pending production telemetry from registered testing agency.'}"
        </p>
      </div>

      {/* Action Buttons (Strictly Gated by Role & Lifecycle State) */}
      <div className="pt-4 border-t border-h2dark-700/80 flex flex-wrap items-center gap-2">
        {/* Status 0 or 8: Submit Telemetry */}
        {(policy.status === STATUS_POLICY_OPEN || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onOpenSubmitTelemetry(policy)}
            disabled={isProcessing || !isPlant}
            title={!isPlant ? 'Role Violation: Only the designated Electrolyzer Plant can submit telemetry.' : 'Submit live laboratory chromatography'}
            className={`flex-1 px-3 py-2.5 rounded-xl text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5 ${
              isPlant
                ? 'bg-yellow-400/20 hover:bg-yellow-400/30 text-yellow-400 border border-yellow-400/40'
                : 'bg-h2dark-850 text-slate-500 border border-h2dark-750 cursor-not-allowed opacity-60'
            }`}
          >
            {isPlant ? <Activity className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
            <span>{isPlant ? 'Submit Telemetry' : 'Plant Telemetry Only'}</span>
          </button>
        )}

        {/* Status 1 or 8: Run AI Quality Adjudication */}
        {(policy.status === STATUS_TELEMETRY_SUBMITTED || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onAdjudicate(policy.policy_id)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2.5 rounded-xl bg-cryo-cyan hover:bg-cryo-deep text-h2dark-950 text-xs font-heading font-semibold transition-all shadow-cryo-glow flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Adjudicate Quality (AI Jury)</span>
          </button>
        )}

        {/* Inspect Evidence Button */}
        {policy.measured_purity_bps > 0 && (
          <button
            onClick={() => onOpenInspector(policy)}
            className="px-3 py-2.5 rounded-xl bg-h2dark-850 hover:bg-h2dark-750 text-slate-300 border border-h2dark-700 text-xs font-mono transition-all flex items-center justify-center gap-1.5"
            title="Inspect Chromatography & Consensus Proof"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Inspect</span>
          </button>
        )}

        {/* Status 2: Appeal within cooling off */}
        {policy.status === STATUS_AWAITING_PAYOUT && coolingOffActive && (
          <button
            onClick={() => onOpenAppeal(policy)}
            disabled={isProcessing || (!isSponsor && !isPlant)}
            title={!isSponsor && !isPlant ? 'Only Sponsor or Plant can appeal this policy' : 'File dispute with 10% staked bond'}
            className={`flex-1 px-3 py-2.5 rounded-xl text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5 ${
              isSponsor || isPlant
                ? 'bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40'
                : 'bg-h2dark-850 text-slate-500 border border-h2dark-750 cursor-not-allowed opacity-60'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Appeal Verdict ({secondsRemaining}s)</span>
          </button>
        )}

        {/* Status 2: Finalize settlement when cooling-off concluded */}
        {policy.status === STATUS_AWAITING_PAYOUT && coolingOffExpired && (
          <button
            onClick={() => onFinalize(policy.policy_id)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2.5 rounded-xl bg-puregreen-emerald hover:bg-puregreen-dark text-h2dark-950 text-xs font-heading font-semibold transition-all shadow-green-glow flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <CheckCircle className="w-3.5 h-3.5" />
            <span>Finalize Settlement Payout</span>
          </button>
        )}

        {/* Status 6: Appellate Review Adjudication */}
        {policy.status === STATUS_DISPUTED && (
          <button
            onClick={() => onAdjudicateAppeal(policy.policy_id)}
            disabled={isProcessing}
            className="flex-1 px-3 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-100 text-xs font-heading font-semibold transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Judge Appellate Review</span>
          </button>
        )}

        {/* Reclaim expired button (Only Sponsor) */}
        {(policy.status === STATUS_POLICY_OPEN || policy.status === STATUS_UNRESOLVED) && (
          <button
            onClick={() => onReclaim(policy.policy_id)}
            disabled={isProcessing || !isSponsor}
            className={`px-2.5 py-2.5 rounded-xl text-xs font-mono transition-all ${
              isSponsor
                ? 'bg-h2dark-850 hover:bg-h2dark-750 text-slate-300 border border-h2dark-700'
                : 'bg-h2dark-850 text-slate-600 border border-h2dark-750 cursor-not-allowed opacity-40'
            }`}
            title={isSponsor ? 'Sponsor Fund: Reclaim Escrow if coverage duration expired' : 'Only Sponsor Fund can reclaim escrow'}
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};
