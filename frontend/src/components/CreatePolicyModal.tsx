import React, { useState } from 'react';
import { X, Flame, Shield, AlertCircle, Info, Sparkles } from 'lucide-react';

interface CreatePolicyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    electrolyzerPlant: string;
    facilityId: string;
    minPurityBps: number;
    maxCarbonIntensityG: number;
    durationBlocks: number;
    escrowGen: string;
  }) => Promise<void>;
  isSubmitting: boolean;
}

export const CreatePolicyModal: React.FC<CreatePolicyModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
}) => {
  const [electrolyzerPlant, setElectrolyzerPlant] = useState('');
  const [facilityId, setFacilityId] = useState('');
  const [minPurityBps, setMinPurityBps] = useState(9997); // 99.97%
  const [maxCarbonIntensityG, setMaxCarbonIntensityG] = useState(2000); // 2000g CO2e / kg H2
  const [durationBlocks, setDurationBlocks] = useState(6000); // ~5 hours coverage
  const [escrowGen, setEscrowGen] = useState('1.5');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: {
    plant: string;
    fac: string;
    purity: number;
    carbon: number;
    blocks: number;
    gen: string;
  }) => {
    setElectrolyzerPlant(preset.plant);
    setFacilityId(preset.fac);
    setMinPurityBps(preset.purity);
    setMaxCarbonIntensityG(preset.carbon);
    setDurationBlocks(preset.blocks);
    setEscrowGen(preset.gen);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanPlant = electrolyzerPlant.trim().toLowerCase();
    if (!cleanPlant.startsWith('0x') || cleanPlant.length !== 42) {
      setError('Please provide a valid 42-character Ethereum-style electrolyzer address.');
      return;
    }

    if (facilityId.trim().length < 4) {
      setError('Facility ID must be at least 4 characters long.');
      return;
    }

    const genVal = parseFloat(escrowGen);
    if (isNaN(genVal) || genVal <= 0) {
      setError('Subsidy escrow deposit must be greater than 0 GEN.');
      return;
    }

    try {
      await onSubmit({
        electrolyzerPlant: cleanPlant,
        facilityId: facilityId.trim(),
        minPurityBps,
        maxCarbonIntensityG,
        durationBlocks,
        escrowGen,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to initialize hydrogen subsidy policy.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-xl bg-h2dark-800 border border-cryo-cyan/40 rounded-2xl p-6 sm:p-8 shadow-cryo-glow my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-h2dark-700/80 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cryo-cyan/10 border border-cryo-cyan/30 flex items-center justify-center text-cryo-cyan shadow-cryo-glow">
              <Flame className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading font-bold text-lg text-slate-100">
                Deposit Hydrogen Subsidy Escrow
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Clean Energy Fund / EU RED III Parametric Escrow
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

        {/* Quick Presets */}
        <div className="mb-6">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-2">
            <Sparkles className="w-3.5 h-3.5 text-solar-lime" />
            Quick Clean Hydrogen Facility Presets
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() =>
                handleApplyPreset({
                  plant: '0x2222222222222222222222222222222222222222',
                  fac: 'ROTTERDAM-PEM-OFFSHORE-01',
                  purity: 9997,
                  carbon: 2000,
                  blocks: 6000,
                  gen: '2.0',
                })
              }
              className="text-left p-2.5 rounded-xl bg-h2dark-850 border border-h2dark-700 hover:border-puregreen-emerald/50 transition-all text-xs"
            >
              <div className="font-semibold text-puregreen-emerald">Rotterdam Offshore H₂</div>
              <div className="text-[11px] text-slate-400 font-mono">100% Wind · 2.0 GEN · 99.97%</div>
            </button>
            <button
              type="button"
              onClick={() =>
                handleApplyPreset({
                  plant: '0x3333333333333333333333333333333333333333',
                  fac: 'HAMBURG-SOLAR-ELECTROLYZER',
                  purity: 9998,
                  carbon: 1500,
                  blocks: 4800,
                  gen: '1.5',
                })
              }
              className="text-left p-2.5 rounded-xl bg-h2dark-850 border border-h2dark-700 hover:border-cryo-cyan/50 transition-all text-xs"
            >
              <div className="font-semibold text-cryo-cyan">Hamburg Solar Hub</div>
              <div className="text-[11px] text-slate-400 font-mono">Solar PV · 1.5 GEN · 99.98%</div>
            </button>
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
              Electrolyzer Plant Address <span className="text-graybreach-crimson">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="0x..."
              value={electrolyzerPlant}
              onChange={(e) => setElectrolyzerPlant(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-300 mb-1.5">
              Facility Identifier / Plant Code <span className="text-graybreach-crimson">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. ROTTERDAM-ELECTROLYZER-H2-01"
              value={facilityId}
              onChange={(e) => setFacilityId(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-600"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">
                Min Purity (Basis Points)
              </label>
              <input
                type="number"
                required
                min={9000}
                max={10000}
                value={minPurityBps}
                onChange={(e) => setMinPurityBps(parseInt(e.target.value) || 9997)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100"
              />
              <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                9997 = 99.97% (ISO 14687 Grade D fuel cell)
              </span>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">
                Max Carbon Intensity (g CO₂/kg)
              </label>
              <input
                type="number"
                required
                min={0}
                max={10000}
                value={maxCarbonIntensityG}
                onChange={(e) => setMaxCarbonIntensityG(parseInt(e.target.value) || 2000)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100"
              />
              <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                2000g = 2.0 kg CO₂e / kg H₂ EU threshold
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">
                Subsidy Deposit (GEN) <span className="text-graybreach-crimson">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.01"
                required
                value={escrowGen}
                onChange={(e) => setEscrowGen(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100"
              />
              <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                Locked in GenLayer Intelligent Escrow
              </span>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1.5">
                Coverage Window (Blocks)
              </label>
              <input
                type="number"
                required
                min={100}
                max={100000}
                value={durationBlocks}
                onChange={(e) => setDurationBlocks(parseInt(e.target.value) || 6000)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100"
              />
              <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                6000 blocks ≈ 5 hours (3s / block)
              </span>
            </div>
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
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-xl bg-cryo-cyan hover:bg-cryo-deep text-h2dark-950 font-heading font-semibold text-xs transition-all shadow-cryo-glow disabled:opacity-50"
            >
              {isSubmitting ? 'Locking Escrow...' : `Lock ${escrowGen} GEN Subsidy`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
