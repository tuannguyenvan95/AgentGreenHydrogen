import React, { useState, useEffect } from 'react';
import { ArrowDownCircle, RefreshCw, CheckCircle2 } from 'lucide-react';
import { readContract } from '../config/genlayer';
import { formatGen } from '../utils/formatters';

interface PullPayoutButtonProps {
  walletAddress: string | null;
  onClaim: () => Promise<void>;
  isClaiming: boolean;
}

export const PullPayoutButton: React.FC<PullPayoutButtonProps> = ({
  walletAddress,
  onClaim,
  isClaiming,
}) => {
  const [claimableBalance, setClaimableBalance] = useState('0');
  const [loading, setLoading] = useState(false);

  const fetchClaimable = async () => {
    if (!walletAddress) {
      setClaimableBalance('0');
      return;
    }
    setLoading(true);
    try {
      const bal = await readContract('get_claimable_balance', [walletAddress]);
      setClaimableBalance(bal ? String(bal) : '0');
    } catch (e) {
      console.warn('Error reading claimable balance:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaimable();
  }, [walletAddress]);

  const hasFunds = BigInt(claimableBalance || '0') > 0n;

  if (!walletAddress || !hasFunds) {
    return null;
  }

  return (
    <div className="mb-6 p-4 rounded-2xl bg-puregreen-emerald/10 border border-puregreen-emerald/40 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-green-glow">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-puregreen-emerald/20 flex items-center justify-center text-puregreen-emerald">
          <ArrowDownCircle className="w-5 h-5 animate-bounce" />
        </div>
        <div>
          <h4 className="font-heading font-semibold text-sm text-slate-100">
            Claimable Subsidy / Appeal Balance Available
          </h4>
          <p className="text-xs font-mono text-slate-400">
            Pull-Payment buffer holds{' '}
            <span className="text-puregreen-emerald font-bold">
              {formatGen(claimableBalance)} GEN
            </span>{' '}
            safely ready for withdrawal.
          </p>
        </div>
      </div>
      <button
        onClick={onClaim}
        disabled={isClaiming}
        className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-puregreen-emerald hover:bg-puregreen-dark text-h2dark-950 font-heading font-semibold text-xs tracking-wide transition-all shadow-green-glow disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <ArrowDownCircle className="w-4 h-4" />
        <span>{isClaiming ? 'Withdrawing...' : `Withdraw ${formatGen(claimableBalance)} GEN`}</span>
      </button>
    </div>
  );
};
