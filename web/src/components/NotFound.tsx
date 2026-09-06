/**
 * NotFound - 404 page for TelePlay
 *
 * Shows when:
 *  - Setup is complete but the user hits an invalid route
 *  - Pre-setup any unknown route (redirected to /setup)
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSetupStatus } from '../lib/api';
import logo from '../assets/logo.png';

export default function NotFound() {
    const navigate = useNavigate();
    const { data: setupData, isLoading: setupLoading } = useSetupStatus();
    const needsSetup = !setupLoading && setupData && !setupData.configured;

    // If setup is NOT complete yet, redirect to /setup immediately
    useEffect(() => {
        if (!setupLoading && needsSetup) {
            navigate('/setup', { replace: true });
        }
    }, [needsSetup, setupLoading, navigate]);

    if (setupLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-dark-950">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
                    <p className="text-dark-400">Loading…</p>
                </div>
            </div>
        );
    }

    if (needsSetup) {
        // Should be redirected above, but safety net
        return null;
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-dark-950">
            {/* Gradient mesh background */}
            <div className="absolute inset-0">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-red-600/15 rounded-full blur-3xl" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-red-700/5 rounded-full blur-3xl" />
            </div>

            <div className="glass-panel p-10 max-w-lg w-full text-center relative z-10 animate-scale-in">
                <p className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-br from-red-400 to-orange-400 mb-2 leading-none">
                    404
                </p>
                <h1 className="text-2xl font-bold text-white mb-3">صفحه مورد نظر یافت نشد</h1>
                <p className="text-dark-400 text-sm mb-8 leading-relaxed">
                    آدرسی که وارد کردید وجود ندارد یا ممکن است تغییر کرده باشد.
                    <br />
                    لطفاً از منوی اصلی دوباره جستجو کنید.
                </p>

                <div className="flex justify-center mb-8">
                    <div className="w-20 h-20 rounded-full bg-dark-800/60 border border-white/[0.06] flex items-center justify-center animate-pulse-subtle">
                        <svg className="w-10 h-10 text-dark-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                </div>

                <img src={logo} alt="TelePlay" className="w-12 h-12 mx-auto mb-4 opacity-60" />
                <p className="text-dark-600 text-xs uppercase tracking-widest mb-8">TelePlay</p>

                <div className="flex flex-col sm:flex-row gap-3">
                    <button
                        onClick={() => navigate('/')}
                        className="btn-primary py-3 px-6 text-sm font-medium"
                    >
                        بازگشت به صفحه اصلی
                    </button>
                    <button
                        onClick={() => navigate(-1)}
                        className="btn-secondary py-3 px-6 text-sm font-medium"
                    >
                        صفحه قبلی
                    </button>
                </div>
            </div>
        </div>
    );
}
