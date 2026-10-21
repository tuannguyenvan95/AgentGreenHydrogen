import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  RefreshCw,
  Search,
  Filter,
  Flame,
  ShieldCheck,
  Zap,
  Layers,
  AlertCircle,
  ExternalLink,
  Cpu,
  CheckCircle2,
} from 'lucide-react';
import {
  STUDIONET_CHAIN_ID,
  STUDIONET_CHAIN_ID_HEX,
  STUDIONET_RPC_URL,
  STUDIO_URL,
  DEFAULT_CONTRACT_ADDRESS,
  getSavedContractAddress,
  readContract,
  waitForTransactionReceipt,
  encodeCalldata,
  fetchStudionetBalance,
  HydrogenPolicyData,
  HydrogenStats,
} from './config/genlayer';
import { Navbar } from './components/Navbar';
import { StatsOverview } from './components/StatsOverview';
import { PolicyCard } from './components/PolicyCard';
import { CreatePolicyModal } from './components/CreatePolicyModal';
import { SubmitTelemetryModal } from './components/SubmitTelemetryModal';
import { QualityInspectorModal } from './components/QualityInspectorModal';
import { AppealModal } from './components/AppealModal';
import { PullPayoutButton } from './components/PullPayoutButton';
import { ElectrolyzerTelemetryVisualizer } from './components/ElectrolyzerTelemetryVisualizer';
import { ErrorBoundary } from './components/ErrorBoundary';

export const App: React.FC = () => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [genBalance, setGenBalance] = useState<string>('0.000');
  const [isConnecting, setIsConnecting] = useState(false);

  const [policies, setPolicies] = useState<HydrogenPolicyData[]>([]);
  const [stats, setStats] = useState<HydrogenStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filter & Search
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmitOpen, setIsSubmitOpen] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);
  const [isAppealOpen, setIsAppealOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<HydrogenPolicyData | null>(null);

  const activeContract = getSavedContractAddress();

  // Load Policies and Stats from GenLayer Studionet
  const fetchContractData = useCallback(async () => {
    setIsLoading(true);
    try {
      // 1. Fetch Stats
      const rawStats = await readContract('get_stats', []);
      if (rawStats) {
        const parsed = typeof rawStats === 'string' ? JSON.parse(rawStats) : rawStats;
        setStats(parsed);
      }

      // 2. Fetch All Policies
      const rawPolicies = await readContract('get_all_policies', []);
      if (rawPolicies) {
        const list = typeof rawPolicies === 'string' ? JSON.parse(rawPolicies) : rawPolicies;
        if (Array.isArray(list)) {
          setPolicies(list);
          if (list.length > 0 && !selectedPolicy) {
            setSelectedPolicy(list[0]);
          }
        }
      }
    } catch (err: any) {
      console.warn('Error reading from Studionet Intelligent Contract:', err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedPolicy]);

  // Connect Wallet
  const connectWallet = async () => {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      alert('MetaMask or a Web3 compatible wallet is required.');
      return;
    }
    setIsConnecting(true);
    try {
      const accounts = await (window as any).ethereum.request({
        method: 'eth_requestAccounts',
      });
      if (accounts && accounts.length > 0) {
        const addr = accounts[0];
        setWalletAddress(addr);
        const bal = await fetchStudionetBalance(addr);
        setGenBalance(bal);
      }
    } catch (err: any) {
      console.error('Wallet connection error:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnectWallet = () => {
    setWalletAddress(null);
    setGenBalance('0.000');
  };

  useEffect(() => {
    fetchContractData();
    // Auto check if already connected
    if (typeof window !== 'undefined' && (window as any).ethereum) {
      (window as any).ethereum
        .request({ method: 'eth_accounts' })
        .then(async (accounts: string[]) => {
          if (accounts && accounts.length > 0) {
            setWalletAddress(accounts[0]);
            const bal = await fetchStudionetBalance(accounts[0]);
            setGenBalance(bal);
          }
        })
        .catch(() => {});
    }
  }, [fetchContractData]);

  // Send Transaction Helper
  const sendTransaction = async (method: string, args: any[], valueWei = '0x0') => {
    if (!walletAddress) {
      throw new Error('Please connect your Web3 wallet first.');
    }
    const calldata = encodeCalldata(method, args);

    const txParams = {
      from: walletAddress,
      to: activeContract,
      data: calldata,
      value: valueWei,
    };

    setStatusMessage(`Broadcasting ${method} to GenLayer StudioNet...`);
    const txHash = await (window as any).ethereum.request({
      method: 'eth_sendTransaction',
      params: [txParams],
    });

    setStatusMessage(`Consensus in progress for tx: ${txHash.slice(0, 10)}...`);
    await waitForTransactionReceipt(txHash);
    setStatusMessage(`Transaction confirmed on StudioNet!`);
    setTimeout(() => setStatusMessage(null), 5000);

    // Refresh balance and data
    const newBal = await fetchStudionetBalance(walletAddress);
    setGenBalance(newBal);
    await fetchContractData();
  };

  // 1. Create Subsidy Policy
  const handleCreatePolicy = async (data: {
    electrolyzerPlant: string;
    facilityId: string;
    minPurityBps: number;
    maxCarbonIntensityG: number;
    durationBlocks: number;
    escrowGen: string;
  }) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const weiAmount = BigInt(Math.floor(parseFloat(data.escrowGen) * 1e18));
      const valueHex = `0x${weiAmount.toString(16)}`;

      await sendTransaction(
        'create_subsidy_policy',
        [
          data.electrolyzerPlant,
          data.facilityId,
          data.minPurityBps,
          data.maxCarbonIntensityG,
          data.durationBlocks,
        ],
        valueHex
      );
    } catch (e: any) {
      setErrorMessage(e.message || 'Failed to deposit subsidy escrow.');
      throw e;
    } finally {
      setIsProcessing(false);
    }
  };

  // 2. Submit Production Telemetry
  const handleSubmitTelemetry = async (policyId: string, feedUrl: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('submit_production_telemetry', [policyId, feedUrl]);
    } catch (e: any) {
      setErrorMessage(e.message || 'Failed to submit production telemetry.');
      throw e;
    } finally {
      setIsProcessing(false);
    }
  };

  // 3. Adjudicate Quality (AI Clean Energy Jury)
  const handleAdjudicate = async (policyId: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('adjudicate_hydrogen_quality', [policyId]);
    } catch (e: any) {
      setErrorMessage(e.message || 'Adjudication failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // 4. File Appeal
  const handleAppeal = async (data: {
    policyId: string;
    reason: string;
    supplementalUrl: string;
    bondWei: string;
  }) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      const valHex = `0x${BigInt(data.bondWei).toString(16)}`;
      await sendTransaction(
        'appeal_verdict',
        [data.policyId, data.reason, data.supplementalUrl],
        valHex
      );
    } catch (e: any) {
      setErrorMessage(e.message || 'Appeal submission failed.');
      throw e;
    } finally {
      setIsProcessing(false);
    }
  };

  // 5. Adjudicate Appeal
  const handleAdjudicateAppeal = async (policyId: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('adjudicate_appeal', [policyId]);
    } catch (e: any) {
      setErrorMessage(e.message || 'Appellate adjudication failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // 6. Finalize Settlement
  const handleFinalize = async (policyId: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('finalize_settlement', [policyId]);
    } catch (e: any) {
      setErrorMessage(e.message || 'Settlement finalization failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // 7. Reclaim Expired Escrow
  const handleReclaim = async (policyId: string) => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('cancel_or_reclaim', [policyId]);
    } catch (e: any) {
      setErrorMessage(e.message || 'Reclaim failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // 8. Pull-Payment Claim
  const handleClaimPayout = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    try {
      await sendTransaction('claim_payout', []);
    } catch (e: any) {
      setErrorMessage(e.message || 'Withdrawal claim failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Filtered Policies
  const filteredPolicies = policies.filter((p) => {
    const matchesQuery =
      p.facility_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.policy_id.includes(searchQuery) ||
      p.sponsor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.electrolyzer_plant.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesQuery) return false;

    if (filterStatus === 'ALL') return true;
    if (filterStatus === 'OPEN') return p.status === 0;
    if (filterStatus === 'SUBMITTED') return p.status === 1;
    if (filterStatus === 'AWAITING') return p.status === 2;
    if (filterStatus === 'SETTLED') return [3, 4, 5].includes(p.status);
    if (filterStatus === 'DISPUTED') return p.status === 6;
    return true;
  });

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-h2dark-900 text-slate-100 flex flex-col font-sans">
        <Navbar
          walletAddress={walletAddress}
          genBalance={genBalance}
          isConnecting={isConnecting}
          onConnectWallet={connectWallet}
          onDisconnectWallet={disconnectWallet}
          onContractChanged={fetchContractData}
        />

        {/* Global Alert / Toast */}
        {statusMessage && (
          <div className="fixed bottom-6 right-6 z-50 p-4 rounded-xl bg-h2dark-800 border border-cryo-cyan text-xs font-mono text-cryo-cyan shadow-cryo-glow flex items-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin shrink-0" />
            <span>{statusMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4 w-full">
            <div className="p-4 rounded-xl bg-graybreach-crimson/15 border border-graybreach-crimson/40 text-graybreach-crimson text-xs font-mono flex items-center justify-between gap-2 shadow-crimson-glow">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={() => setErrorMessage(null)}
                className="text-graybreach-crimson hover:underline text-[11px]"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
          {/* Pull Payout Safety Withdrawal Banner */}
          <PullPayoutButton
            walletAddress={walletAddress}
            onClaim={handleClaimPayout}
            isClaiming={isProcessing}
          />

          {/* Aggregated Cleantech Stats */}
          <StatsOverview stats={stats} totalPolicies={policies.length} />

          {/* DePIN Live Telemetry & PEM Visualizer */}
          <ElectrolyzerTelemetryVisualizer
            activePolicy={selectedPolicy || (policies.length > 0 ? policies[0] : null)}
          />

          {/* Action & Filter Bar */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 mb-6">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setIsCreateOpen(true)}
                className="px-4 py-2.5 rounded-xl bg-cryo-cyan hover:bg-cryo-deep text-h2dark-950 font-heading font-semibold text-xs tracking-wide transition-all shadow-cryo-glow flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                <span>Create Subsidy Escrow</span>
              </button>

              <button
                onClick={fetchContractData}
                disabled={isLoading}
                className="p-2.5 rounded-xl bg-h2dark-800 border border-h2dark-700 hover:border-slate-500 text-slate-300 transition-colors"
                title="Refresh from GenLayer StudioNet"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Filter and Search */}
            <div className="flex items-center gap-2 w-full md:w-auto">
              {/* Search */}
              <div className="relative flex-1 md:w-64">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  placeholder="Search facility or policy..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-h2dark-800 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100 placeholder:text-slate-500"
                />
              </div>

              {/* Status Filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-3 py-2 rounded-xl bg-h2dark-800 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-200"
              >
                <option value="ALL">All Statuses</option>
                <option value="OPEN">Open Escrows</option>
                <option value="SUBMITTED">Telemetry Submitted</option>
                <option value="AWAITING">Awaiting Payout</option>
                <option value="SETTLED">Settled</option>
                <option value="DISPUTED">Under Appeal</option>
              </select>
            </div>
          </div>

          {/* Policy Cards Grid */}
          {isLoading && policies.length === 0 ? (
            <div className="p-12 text-center bg-h2dark-800 border border-h2dark-700/80 rounded-2xl">
              <RefreshCw className="w-8 h-8 text-cryo-cyan animate-spin mx-auto mb-3" />
              <p className="text-sm font-mono text-slate-400">
                Syncing Clean Hydrogen Escrow Registry with GenLayer StudioNet...
              </p>
            </div>
          ) : filteredPolicies.length === 0 ? (
            <div className="p-12 text-center bg-h2dark-800 border border-h2dark-700/80 rounded-2xl">
              <Flame className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-heading font-semibold text-slate-300">
                No Hydrogen Subsidy Policies Found
              </h3>
              <p className="text-xs font-mono text-slate-500 mt-1 max-w-md mx-auto">
                No policies match your search or filter criteria. Click "Create Subsidy Escrow" to deposit GEN and onboard a new hydrogen production facility.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredPolicies.map((p) => (
                <PolicyCard
                  key={p.policy_id}
                  policy={p}
                  walletAddress={walletAddress}
                  onOpenSubmitTelemetry={(pol) => {
                    setSelectedPolicy(pol);
                    setIsSubmitOpen(true);
                  }}
                  onOpenInspector={(pol) => {
                    setSelectedPolicy(pol);
                    setIsInspectorOpen(true);
                  }}
                  onOpenAppeal={(pol) => {
                    setSelectedPolicy(pol);
                    setIsAppealOpen(true);
                  }}
                  onAdjudicate={handleAdjudicate}
                  onAdjudicateAppeal={handleAdjudicateAppeal}
                  onFinalize={handleFinalize}
                  onReclaim={handleReclaim}
                  isProcessing={isProcessing}
                />
              ))}
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="w-full border-t border-h2dark-800 bg-h2dark-950 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-puregreen-emerald"></span>
              <span>AgentGreenHydrogen · Powered by GenLayer Intelligent Contracts & StudioNet</span>
            </div>
            <div className="flex items-center gap-4">
              <a
                href={STUDIO_URL}
                target="_blank"
                rel="noreferrer"
                className="hover:text-cryo-cyan transition-colors flex items-center gap-1"
              >
                <span>StudioNet Explorer</span>
                <ExternalLink className="w-3 h-3" />
              </a>
              <span className="text-slate-700">|</span>
              <span className="text-slate-400">Chain ID: 61999 (0xF22F)</span>
            </div>
          </div>
        </footer>

        {/* Modals */}
        <CreatePolicyModal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onSubmit={handleCreatePolicy}
          isSubmitting={isProcessing}
        />

        <SubmitTelemetryModal
          isOpen={isSubmitOpen}
          policy={selectedPolicy}
          onClose={() => setIsSubmitOpen(false)}
          onSubmit={handleSubmitTelemetry}
          isSubmitting={isProcessing}
        />

        <QualityInspectorModal
          isOpen={isInspectorOpen}
          policy={selectedPolicy}
          onClose={() => setIsInspectorOpen(false)}
        />

        <AppealModal
          isOpen={isAppealOpen}
          policy={selectedPolicy}
          onClose={() => setIsAppealOpen(false)}
          onSubmitAppeal={handleAppeal}
          isSubmitting={isProcessing}
        />
      </div>
    </ErrorBoundary>
  );
};
