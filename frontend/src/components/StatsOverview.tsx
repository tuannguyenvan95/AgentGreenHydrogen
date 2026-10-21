import React from 'react';
import { Shield, Zap, CheckCircle2, TrendingUp, Layers, Wind } from 'lucide-react';
import { formatGen } from '../utils/formatters';
import { HydrogenStats } from '../config/genlayer';

interface StatsOverviewProps {
  stats: HydrogenStats | null;
  totalPolicies: number;
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({ stats, totalPolicies }) => {
  const subsidiesLocked = stats?.total_subsidies_locked ? formatGen(stats.total_subsidies_locked) : '0.000';
  const settledCount = stats?.total_policies_settled ?? 0;
  const policyCount = stats?.total_policies ?? totalPolicies ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {/* Total Subsidies Locked */}
      <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-5 shadow-console relative overflow-hidden group hover:border-cryo-cyan/50 transition-all">
        <div className="absolute top-0 right-0 w-24 h-24 bg-cryo-cyan/5 rounded-bl-full pointer-events-none group-hover:bg-cryo-cyan/10 transition-all"></div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
            Total Subsidies Locked
          </span>
          <div className="w-8 h-8 rounded-lg bg-cryo-cyan/10 border border-cryo-cyan/30 flex items-center justify-center text-cryo-cyan shadow-cryo-glow">
            <Zap className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-bold text-slate-100 tracking-tight">
            {subsidiesLocked}
          </span>
          <span className="text-xs font-mono font-semibold text-cryo-cyan">GEN</span>
        </div>
        <div className="mt-2 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-puregreen-emerald"></span>
          <span>EU RED III & Climate Escrow Pool</span>
        </div>
      </div>

      {/* Active Escrow Policies */}
      <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-5 shadow-console relative overflow-hidden group hover:border-puregreen-emerald/50 transition-all">
        <div className="absolute top-0 right-0 w-24 h-24 bg-puregreen-emerald/5 rounded-bl-full pointer-events-none group-hover:bg-puregreen-emerald/10 transition-all"></div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
            Electrolyzer Policies
          </span>
          <div className="w-8 h-8 rounded-lg bg-puregreen-emerald/10 border border-puregreen-emerald/30 flex items-center justify-center text-puregreen-emerald shadow-green-glow">
            <Layers className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-bold text-slate-100 tracking-tight">
            {policyCount}
          </span>
          <span className="text-xs font-mono text-slate-400">Contracts</span>
        </div>
        <div className="mt-2 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-cryo-cyan"></span>
          <span>Parametric ISO 14687 verification</span>
        </div>
      </div>

      {/* Settled Facilities */}
      <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-5 shadow-console relative overflow-hidden group hover:border-solar-lime/50 transition-all">
        <div className="absolute top-0 right-0 w-24 h-24 bg-solar-lime/5 rounded-bl-full pointer-events-none group-hover:bg-solar-lime/10 transition-all"></div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
            Settled Policies
          </span>
          <div className="w-8 h-8 rounded-lg bg-solar-lime/10 border border-solar-lime/30 flex items-center justify-center text-solar-lime">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-bold text-slate-100 tracking-tight">
            {settledCount}
          </span>
          <span className="text-xs font-mono text-slate-400">Completed</span>
        </div>
        <div className="mt-2 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-solar-lime"></span>
          <span>Verdicts finalized by GenVM</span>
        </div>
      </div>

      {/* Renewable Energy Standard */}
      <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-5 shadow-console relative overflow-hidden group hover:border-purple-400/50 transition-all">
        <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-bl-full pointer-events-none group-hover:bg-purple-500/10 transition-all"></div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
            Quality Threshold
          </span>
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Shield className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-mono font-bold text-slate-100 tracking-tight">
            ≥ 99.97%
          </span>
          <span className="text-xs font-mono text-slate-400">Purity</span>
        </div>
        <div className="mt-2 text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
          <Wind className="w-3.5 h-3.5 text-puregreen-emerald" />
          <span>≤ 2.0 kg CO₂e / kg H₂ limit</span>
        </div>
      </div>
    </div>
  );
};
