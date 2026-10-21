export function formatGen(val: string | number | bigint | null | undefined): string {
  if (val === null || val === undefined) return '0.000';
  try {
    let big: bigint;
    if (typeof val === 'string' && val.startsWith('0x')) {
      big = BigInt(val);
    } else {
      big = BigInt(val.toString());
    }
    const divisor = 10n ** 18n;
    const integerPart = big / divisor;
    const remainder = big % divisor;
    const fractionPart = remainder.toString().padStart(18, '0').slice(0, 4);
    return `${integerPart}.${fractionPart}`;
  } catch {
    return '0.000';
  }
}

export function formatAddress(address: string | null | undefined): string {
  if (!address) return '0x0000...0000';
  const clean = address.trim();
  if (clean.length <= 10) return clean;
  return `${clean.slice(0, 6)}...${clean.slice(-4)}`;
}

export function formatTimestamp(ts: string | number | bigint | null | undefined): string {
  if (!ts) return 'N/A';
  try {
    const num = Number(ts);
    if (num <= 0) return 'Pending';
    const date = new Date(num * 1000);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return 'Invalid Date';
  }
}

export function formatPurity(bps: number | string | null | undefined): string {
  if (bps === null || bps === undefined || Number(bps) === 0) return '0.00%';
  const n = Number(bps);
  return `${(n / 100).toFixed(2)}%`;
}

export function formatCarbonIntensity(grams: number | string | null | undefined): string {
  if (grams === null || grams === undefined || Number(grams) === 0) return '0.00 kg CO₂e/kg';
  const n = Number(grams);
  return `${(n / 1000).toFixed(2)} kg CO₂e/kg`;
}

export const STATUS_LABELS: Record<number, { label: string; color: string; border: string; bg: string }> = {
  0: {
    label: 'ESCROW OPEN',
    color: 'text-cryo-cyan',
    border: 'border-cryo-cyan/40',
    bg: 'bg-cryo-cyan/10',
  },
  1: {
    label: 'TELEMETRY SUBMITTED',
    color: 'text-yellow-400',
    border: 'border-yellow-400/40',
    bg: 'bg-yellow-400/10',
  },
  2: {
    label: 'AWAITING PAYOUT (COOLING-OFF)',
    color: 'text-cryo-cyan',
    border: 'border-cryo-cyan/40',
    bg: 'bg-cryo-cyan/15',
  },
  3: {
    label: 'CERTIFIED GREEN (100% PAID)',
    color: 'text-puregreen-emerald',
    border: 'border-puregreen-emerald/50',
    bg: 'bg-puregreen-emerald/15',
  },
  4: {
    label: 'PARTIAL PENALTY (50% CUT)',
    color: 'text-penalty-amber',
    border: 'border-penalty-amber/50',
    bg: 'bg-penalty-amber/15',
  },
  5: {
    label: 'GRAY H2 REJECTED (REFUNDED)',
    color: 'text-graybreach-crimson',
    border: 'border-graybreach-crimson/50',
    bg: 'bg-graybreach-crimson/15',
  },
  6: {
    label: 'DISPUTED (UNDER APPEAL)',
    color: 'text-purple-400',
    border: 'border-purple-400/50',
    bg: 'bg-purple-400/15',
  },
  7: {
    label: 'EXPIRED & RECLAIMED',
    color: 'text-slate-400',
    border: 'border-slate-500/40',
    bg: 'bg-slate-500/10',
  },
  8: {
    label: 'UNRESOLVED (PROTECTED)',
    color: 'text-rose-400',
    border: 'border-rose-400/40',
    bg: 'bg-rose-400/10',
  },
};
