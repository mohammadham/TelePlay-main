/**
 * ErrorBoundary - Catches JavaScript errors in child components
 * Shows fallback UI when a component crashes
 */
import { Component, ReactNode } from 'react';
import logo from '../assets/logo.png';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center p-4 bg-dark-950">
                    <div className="glass-panel p-8 max-w-md w-full text-center">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
                            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
                        <p className="text-dark-400 text-sm mb-6">
                            An unexpected error occurred. Please try refreshing the page.
                        </p>
                        <img src={logo} alt="TelePlay" className="w-12 h-12 mx-auto mb-4 opacity-60" />
                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={() => window.location.reload()}
                                className="btn-primary px-6 py-2.5 text-sm"
                            >
                                Refresh Page
                            </button>
                            <button
                                onClick={() => window.location.href = '/'}
                                className="btn-secondary px-6 py-2.5 text-sm"
                            >
                                Go Home
                            </button>
                        </div>
                        {(import.meta.env.DEV || process.env.NODE_ENV === 'development') && this.state.error && (
                            <details className="mt-6 text-left">
                                <summary className="text-xs text-dark-500 cursor-pointer">Error Details</summary>
                                <pre className="text-xs text-red-400 mt-2 bg-dark-900/50 p-3 rounded overflow-auto max-h-40">
                                    {this.state.error.toString()}
                                </pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
