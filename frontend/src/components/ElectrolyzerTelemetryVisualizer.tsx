import React, { useState } from 'react';
import {
  Activity,
  Wind,
  Sun,
  Zap,
  Gauge,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { HydrogenPolicyData } from '../config/genlayer';
import { formatPurity, formatCarbonIntensity } from '../utils/formatters';

interface VisualizerProps {
  activePolicy: HydrogenPolicyData | null;
}

export const ElectrolyzerTelemetryVisualizer: React.FC<VisualizerProps> = ({ activePolicy }) => {
  const [activeTab, setActiveTab] = useState<'chromatography' | 'renewable' | 'stack'>('chromatography');

  const purityBps = activePolicy?.measured_purity_bps || 9998;
  const carbonIntensityG = activePolicy?.measured_carbon_intensity_g || 1250;
  const isCertified = purityBps >= 9997 && carbonIntensityG <= 2000;

  return (
    <div className="bg-h2dark-800 border border-h2dark-700/80 rounded-2xl p-6 shadow-console mb-8">
      {/* Console Section Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-h2dark-700/80 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cryo-cyan/10 border border-cryo-cyan/30 flex items-center justify-center text-cryo-cyan shadow-cryo-glow">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading font-bold text-base text-slate-100">
                Parametric Electrolyzer Command Matrix
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cryo-cyan/15 text-cryo-cyan border border-cryo-cyan/30">
                LIVE ORACLE
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400">
              Facility: {activePolicy?.facility_id || 'DEMO-ELECTROLYZER-STACK-01'} · ISO 14687 Fuel Cell Telemetry
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-h2dark-850 p-1 rounded-xl border border-h2dark-750">
          <button
            onClick={() => setActiveTab('chromatography')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'chromatography'
                ? 'bg-cryo-cyan/20 text-cryo-cyan border border-cryo-cyan/40 shadow-cryo-glow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Gas Chromatography
          </button>
          <button
            onClick={() => setActiveTab('renewable')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'renewable'
                ? 'bg-puregreen-emerald/20 text-puregreen-emerald border border-puregreen-emerald/40 shadow-green-glow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Renewable Matching
          </button>
          <button
            onClick={() => setActiveTab('stack')}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'stack'
                ? 'bg-solar-lime/20 text-solar-lime border border-solar-lime/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            PEM Cell Diagnostics
          </button>
        </div>
      </div>

      {/* Tab 1: Gas Chromatography Spectrum */}
      {activeTab === 'chromatography' && (
        <div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
            {/* Visual Gas Spectrum Bars */}
            <div className="lg:col-span-2 bg-h2dark-900/80 p-5 rounded-xl border border-h2dark-750">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-4">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-cryo-cyan" />
                  Gas Chromatography Absorption Retention Profile
                </span>
                <span className="text-puregreen-emerald font-bold">
                  Purity: {formatPurity(purityBps)}
                </span>
              </div>

              {/* Spectral Peak Simulation */}
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-puregreen-emerald font-bold">
                      H₂ (Hydrogen Gas Peak)
                    </span>
                    <span className="text-slate-200 font-bold">
                      {(purityBps / 100).toFixed(3)}%
                    </span>
                  </div>
                  <div className="w-full h-3 bg-h2dark-800 rounded-full overflow-hidden border border-h2dark-700">
                    <div
                      className="h-full bg-gradient-to-r from-cryo-cyan via-puregreen-emerald to-puregreen-emerald shadow-green-glow"
                      style={{ width: `${Math.min(100, (purityBps / 10000) * 100)}%` }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-400">O₂ (Oxygen Residual)</span>
                    <span className="text-slate-400">0.012% (120 ppm)</span>
                  </div>
                  <div className="w-full h-2 bg-h2dark-800 rounded-full overflow-hidden border border-h2dark-700">
                    <div className="h-full bg-cryo-cyan/60" style={{ width: '4%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-400">N₂ / Argon Inactive</span>
                    <span className="text-slate-400">0.006% (60 ppm)</span>
                  </div>
                  <div className="w-full h-2 bg-h2dark-800 rounded-full overflow-hidden border border-h2dark-700">
                    <div className="h-full bg-slate-500" style={{ width: '2%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-mono mb-1">
                    <span className="text-slate-400">H₂O Vapor / Moisture</span>
                    <span className="text-slate-400">0.002% (5 ppm)</span>
                  </div>
                  <div className="w-full h-2 bg-h2dark-800 rounded-full overflow-hidden border border-h2dark-700">
                    <div className="h-full bg-sky-400/40" style={{ width: '1%' }}></div>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-h2dark-800 flex items-center justify-between text-[11px] font-mono text-slate-500">
                <span>Standard: ISO 14687:2019 Type I Grade D</span>
                <span>Audit Sensor: Agilent 990 Micro GC</span>
              </div>
            </div>

            {/* Purity Compliance Gauge Card */}
            <div className="bg-h2dark-850 p-5 rounded-xl border border-h2dark-700 flex flex-col items-center text-center">
              <div className="w-14 h-14 rounded-2xl bg-puregreen-emerald/10 border border-puregreen-emerald/30 flex items-center justify-center text-puregreen-emerald mb-3 shadow-green-glow">
                <Gauge className="w-7 h-7" />
              </div>
              <span className="text-xs font-mono uppercase text-slate-400 tracking-wider">
                ISO 14687 Fuel Cell Compliance
              </span>
              <div className="text-3xl font-mono font-bold text-puregreen-emerald mt-1">
                {formatPurity(purityBps)}
              </div>
              <span className="text-xs font-mono text-slate-400 mt-1">
                Required Target: ≥ 99.97%
              </span>
              <div className="mt-4 px-3 py-1.5 rounded-lg bg-puregreen-emerald/10 border border-puregreen-emerald/30 text-[11px] font-mono text-puregreen-emerald flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Zero Carbon Dilution Detected</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Renewable Matching */}
      {activeTab === 'renewable' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400">Offshore Wind Farm</span>
              <Wind className="w-4 h-4 text-cryo-cyan" />
            </div>
            <div className="text-2xl font-mono font-bold text-slate-100">74.5%</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">
              Hourly Guarantees of Origin (GOs)
            </div>
            <div className="w-full h-1.5 bg-h2dark-800 rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-cryo-cyan" style={{ width: '74.5%' }}></div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400">Solar PV Direct</span>
              <Sun className="w-4 h-4 text-solar-lime" />
            </div>
            <div className="text-2xl font-mono font-bold text-slate-100">25.5%</div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">
              Co-located 50MW Solar Array
            </div>
            <div className="w-full h-1.5 bg-h2dark-800 rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-solar-lime" style={{ width: '25.5%' }}></div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400">Fossil Grid Mix</span>
              <Zap className="w-4 h-4 text-graybreach-crimson" />
            </div>
            <div className="text-2xl font-mono font-bold text-puregreen-emerald">0.0%</div>
            <div className="text-[11px] font-mono text-puregreen-emerald mt-1">
              Zero Coal/Gas Grid Peaking
            </div>
            <div className="w-full h-1.5 bg-h2dark-800 rounded-full mt-3 overflow-hidden">
              <div className="h-full bg-puregreen-emerald" style={{ width: '0%' }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: PEM Cell Diagnostics */}
      {activeTab === 'stack' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <span className="text-xs font-mono text-slate-400 block mb-1">Electrolyte Tech</span>
            <div className="text-lg font-heading font-bold text-slate-100">PEM Catalyst</div>
            <span className="text-[11px] font-mono text-cryo-cyan">Iridium / Platinum Mesh</span>
          </div>

          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <span className="text-xs font-mono text-slate-400 block mb-1">Operating Current</span>
            <div className="text-lg font-heading font-bold text-slate-100">2.1 A/cm²</div>
            <span className="text-[11px] font-mono text-puregreen-emerald">Optimal Efficiency</span>
          </div>

          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <span className="text-xs font-mono text-slate-400 block mb-1">Stack Temperature</span>
            <div className="text-lg font-heading font-bold text-slate-100">68.4 °C</div>
            <span className="text-[11px] font-mono text-slate-400">Cooling Loop Active</span>
          </div>

          <div className="p-4 rounded-xl bg-h2dark-850 border border-h2dark-700">
            <span className="text-xs font-mono text-slate-400 block mb-1">Pressure Differential</span>
            <div className="text-lg font-heading font-bold text-slate-100">30.2 bar</div>
            <span className="text-[11px] font-mono text-puregreen-emerald">Direct H₂ Compression</span>
          </div>
        </div>
      )}
    </div>
  );
};
