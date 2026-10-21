import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in AgentGreenHydrogen:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-h2dark-800 border border-graybreach-crimson/40 rounded-xl p-6 text-center shadow-crimson-glow">
            <div className="w-12 h-12 bg-graybreach-crimson/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-graybreach-crimson/30">
              <AlertTriangle className="w-6 h-6 text-graybreach-crimson" />
            </div>
            <h3 className="text-lg font-heading font-semibold text-slate-100 mb-2">
              Industrial Command Console Error
            </h3>
            <p className="text-sm text-slate-400 mb-4 font-mono">
              {this.state.error?.message || 'An unexpected rendering anomaly occurred.'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-cryo-cyan/20 hover:bg-cryo-cyan/30 text-cryo-cyan border border-cryo-cyan/40 rounded-lg text-sm font-medium transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Reboot Command Console
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
