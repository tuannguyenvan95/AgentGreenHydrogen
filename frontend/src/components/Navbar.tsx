import React, { useState } from 'react';
import {
  ShieldCheck,
  Wallet,
  Settings,
  ExternalLink,
  Flame,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import {
  STUDIONET_CHAIN_ID,
  STUDIONET_CHAIN_ID_HEX,
  STUDIONET_RPC_URL,
  STUDIO_URL,
  DEFAULT_CONTRACT_ADDRESS,
  getSavedContractAddress,
  saveContractAddress,
} from '../config/genlayer';
import { formatAddress } from '../utils/formatters';

interface NavbarProps {
  walletAddress: string | null;
  genBalance: string;
  isConnecting: boolean;
  onConnectWallet: () => void;
  onDisconnectWallet: () => void;
  onContractChanged: (newAddress: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  walletAddress,
  genBalance,
  isConnecting,
  onConnectWallet,
  onDisconnectWallet,
  onContractChanged,
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [customAddress, setCustomAddress] = useState(getSavedContractAddress());
  const [copied, setCopied] = useState(false);
  const [copiedContract, setCopiedContract] = useState(false);

  const activeContract = getSavedContractAddress();

  const handleCopy = (text: string, isContract = false) => {
    navigator.clipboard.writeText(text);
    if (isContract) {
      setCopiedContract(true);
      setTimeout(() => setCopiedContract(false), 2000);
    } else {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSwitchNetwork = async () => {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      alert('Please install MetaMask or a compatible Web3 wallet.');
      return;
    }
    try {
      await (window as any).ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: STUDIONET_CHAIN_ID_HEX }],
      });
    } catch (switchError: any) {
      if (switchError.code === 4902) {
        try {
          await (window as any).ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [
              {
                chainId: STUDIONET_CHAIN_ID_HEX,
                chainName: 'GenLayer StudioNet',
                nativeCurrency: {
                  name: 'GEN',
                  symbol: 'GEN',
                  decimals: 18,
                },
                rpcUrls: [STUDIONET_RPC_URL],
                blockExplorerUrls: [STUDIO_URL],
              },
            ],
          });
        } catch (addError) {
          console.error('Failed to add StudioNet:', addError);
        }
      }
    }
  };

  const handleSaveContract = () => {
    const clean = customAddress.trim();
    if (clean.startsWith('0x') && clean.length === 42) {
      saveContractAddress(clean);
      onContractChanged(clean);
      setShowSettings(false);
    } else {
      alert('Please enter a valid 42-character hex address.');
    }
  };

  const handleResetContract = () => {
    saveContractAddress(DEFAULT_CONTRACT_ADDRESS);
    setCustomAddress(DEFAULT_CONTRACT_ADDRESS);
    onContractChanged(DEFAULT_CONTRACT_ADDRESS);
    setShowSettings(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full bg-h2dark-900/90 backdrop-blur-md border-b border-h2dark-700/60 shadow-console">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-h2dark-800 border border-cryo-cyan/40 shadow-cryo-glow">
            <Flame className="w-6 h-6 text-cryo-cyan animate-pulse" />
            <span className="absolute -bottom-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-puregreen-emerald opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-puregreen-emerald"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-heading font-bold text-lg sm:text-xl text-slate-100 tracking-tight flex items-center gap-1.5">
                AgentGreenHydrogen
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-puregreen-emerald/15 text-puregreen-emerald border border-puregreen-emerald/30">
                ISO 14687 CERTIFIED
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono hidden sm:block">
              Autonomous Green H₂ Purity & Clean Electrolysis Escrow
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {/* Network indicator pill */}
          <button
            onClick={handleSwitchNetwork}
            className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-h2dark-800 border border-h2dark-700 hover:border-cryo-cyan/50 text-xs font-mono text-slate-300 transition-colors"
            title="Switch to GenLayer StudioNet (Chain ID 61999)"
          >
            <span className="w-2 h-2 rounded-full bg-cryo-cyan animate-pulse"></span>
            <span>StudioNet (61999)</span>
          </button>

          {/* Active Contract pill */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-h2dark-800 border border-h2dark-700 text-xs font-mono text-slate-300">
            <span className="text-slate-500">Contract:</span>
            <span className="text-cryo-cyan">{formatAddress(activeContract)}</span>
            <button
              onClick={() => handleCopy(activeContract, true)}
              className="text-slate-400 hover:text-slate-200 transition-colors"
              title="Copy Contract Address"
            >
              {copiedContract ? <Check className="w-3.5 h-3.5 text-puregreen-emerald" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Settings button */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 rounded-lg bg-h2dark-800 border border-h2dark-700 hover:border-cryo-cyan/50 text-slate-400 hover:text-slate-200 transition-colors"
            title="Configure Contract Address"
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* Wallet Connection */}
          {walletAddress ? (
            <div className="flex items-center gap-2">
              <div className="hidden sm:flex flex-col items-end px-3 py-1 rounded-lg bg-h2dark-800 border border-h2dark-700">
                <span className="text-[10px] font-mono text-slate-400">Balance</span>
                <span className="text-xs font-mono font-bold text-cryo-cyan">
                  {genBalance} GEN
                </span>
              </div>
              <button
                onClick={onDisconnectWallet}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-h2dark-800 border border-cryo-cyan/40 hover:border-cryo-cyan text-xs font-mono text-slate-200 transition-all shadow-cryo-glow"
              >
                <div className="w-2 h-2 rounded-full bg-puregreen-emerald"></div>
                <span>{formatAddress(walletAddress)}</span>
              </button>
            </div>
          ) : (
            <button
              onClick={onConnectWallet}
              disabled={isConnecting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cryo-cyan hover:bg-cryo-deep text-h2dark-950 font-heading font-semibold text-xs tracking-wide transition-all shadow-cryo-glow disabled:opacity-50"
            >
              <Wallet className="w-4 h-4" />
              <span>{isConnecting ? 'Connecting...' : 'Connect Wallet'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Contract Settings Drawer / Modal */}
      {showSettings && (
        <div className="border-t border-h2dark-700/80 bg-h2dark-850 px-4 py-4 sm:px-6">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="w-full md:w-2/3">
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Target Intelligent Contract Address (GenLayer StudioNet)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={customAddress}
                  onChange={(e) => setCustomAddress(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-h2dark-900 border border-h2dark-700 focus:border-cryo-cyan focus:outline-none text-xs font-mono text-slate-100"
                  placeholder="0x..."
                />
              </div>
            </div>
            <div className="flex items-center gap-2 w-full md:w-auto justify-end">
              <button
                onClick={handleResetContract}
                className="px-3 py-2 rounded-lg bg-h2dark-800 border border-h2dark-700 hover:border-slate-500 text-xs font-mono text-slate-300 transition-colors"
              >
                Reset Default
              </button>
              <button
                onClick={handleSaveContract}
                className="px-4 py-2 rounded-lg bg-puregreen-emerald hover:bg-puregreen-dark text-h2dark-950 font-heading font-semibold text-xs transition-colors shadow-green-glow"
              >
                Save Contract
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-2 rounded-lg bg-h2dark-800 border border-h2dark-700 text-xs font-mono text-slate-400 hover:text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
