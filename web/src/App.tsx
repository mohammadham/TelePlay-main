import { Routes, Route, Navigate, useSearchParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useCurrentUser, useLoginWithCode, useBotInfo, useGenerateLoginCode, useVerifyLoginCode } from './lib/api';
import FileBrowser from './components/FileBrowser';
import GlobalContextMenu from './components/GlobalContextMenu';
import logo from './assets/logo.png';

function AuthCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');
    const [status, setStatus] = useState('Processing...');
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        if (token) {
            try {
                console.log('Token received:', token.substring(0, 20) + '...');
                localStorage.setItem('access_token', token);
                const check = localStorage.getItem('access_token');
                if (check === token) {
                    setStatus('✅ Token saved! Redirecting...');
                    setSaved(true);
                    setTimeout(() => {
                        navigate('/', { replace: true });
                    }, 500);
                } else {
                    setStatus('❌ Failed to save token to localStorage');
                }
            } catch (e) {
                setStatus(`❌ Error: ${e}`);
            }
        } else {
            setStatus('❌ No token in URL');
        }
    }, [token, navigate]);

    // If saved but still on this page, try redirect again
    useEffect(() => {
        if (saved) {
            const timer = setTimeout(() => {
                window.location.href = '/';
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [saved]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-dark-950 p-4">
            <div className="text-center max-w-lg">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
                <p className="text-white text-lg mb-4">{status}</p>

                {token && !saved && (
                    <div className="mt-4 p-4 bg-dark-800 rounded-lg text-left">
                        <p className="text-dark-400 text-sm mb-2">Token received (click to copy):</p>
                        <button
                            onClick={() => {
                                navigator.clipboard.writeText(token);
                                setStatus('Token copied! Open browser DevTools console and run:\nlocalStorage.setItem("access_token", "paste-token-here")');
                            }}
                            className="text-xs text-primary-400 break-all text-left hover:text-primary-300"
                        >
                            {token.substring(0, 50)}...
                        </button>
                        <div className="mt-4">
                            <a
                                href="/"
                                className="inline-block px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded text-white text-sm"
                                onClick={() => localStorage.setItem('access_token', token)}
                            >
                                Try Manual Login →
                            </a>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// Add Key icon to imports if not already imported (it's not, need to check imports)
// Wait, I can't easily add imports here without multiple replace.
// I'll stick to simple UI for now or check imports first.
// App.tsx imports: Routes, Route, Navigate, useSearchParams, useNavigate (react-router-dom); useEffect, useState (react); useCurrentUser (./lib/api); FileBrowser
// It does NOT import lucide-react icons. I'll use text or existing SVG.

function LoginPage() {
    const { mutate: loginByCode, isPending: isVerifying } = useLoginWithCode();
    const { mutate: generateCode, isPending: isGenerating } = useGenerateLoginCode();
    const { mutate: verifyCode } = useVerifyLoginCode();
    
    const [code, setCode] = useState('');
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Initial code generation
    useEffect(() => {
        generateCode(undefined, {
            onSuccess: (data) => {
                setCode(data.code);
                setIsPolling(true);
            },
            onError: (err: any) => {
                setError(err.response?.data?.detail || "Failed to generate code");
            }
        });
    }, [generateCode]);

    // Polling logic
    useEffect(() => {
        let timer: any;
        if (isPolling && code) {
            timer = setInterval(() => {
                verifyCode(code, {
                    onSuccess: (data) => {
                        localStorage.setItem('access_token', data.access_token);
                        localStorage.setItem('refresh_token', data.refresh_token);
                        setIsPolling(false);
                        window.location.href = '/';
                    },
                    onError: () => {
                        // Silent failure for polling
                    }
                });
            }, 3000);
        }
        return () => {
            if (timer) clearInterval(timer);
        };
    }, [isPolling, code, verifyCode]);

    const handleManualLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (!code) return;

        loginByCode(code, {
            onSuccess: (data) => {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                window.location.href = '/';
            },
            onError: (err: any) => {
                setError(err.response?.data?.detail || "Invalid code");
            }
        });
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Gradient mesh background */}
            <div className="absolute inset-0 bg-dark-950">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl"></div>
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl"></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-700/5 rounded-full blur-3xl"></div>
            </div>

            <div className="glass-panel p-8 max-w-md w-full text-center animate-scale-in relative z-10">
                {/* Logo */}
                <img src={logo} alt="TelePlay" className="w-24 h-24 mx-auto mb-6 drop-shadow-2xl" />

                <h1 className="text-3xl font-bold mb-2 text-gradient">
                    TelePlay
                </h1>
                <p className="text-dark-400 mb-8">
                    Stream your files from Telegram
                </p>

                <div className="space-y-6">
                    {/* Login Code Section */}
                    <div className="glass-card p-6">
                        <h3 className="text-white font-medium mb-4 flex items-center justify-center gap-2">
                            <svg className="w-5 h-5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                            </svg>
                            Login with Code
                        </h3>
                        <form onSubmit={handleManualLogin} className="flex flex-col gap-3">
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="ENTER 6-DIGIT CODE"
                                    value={code}
                                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                                    maxLength={6}
                                    className="w-full bg-dark-900/60 border border-white/[0.08] rounded-xl px-4 py-4 text-center text-xl tracking-[0.1em] sm:text-2xl sm:tracking-[0.3em] font-mono text-white placeholder:text-sm placeholder:tracking-normal placeholder:font-sans placeholder-dark-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 transition-all duration-200 uppercase"
                                />
                                {isGenerating && (
                                    <div className="absolute inset-0 flex items-center justify-center bg-dark-900/40 rounded-xl">
                                        <div className="w-5 h-5 border-2 border-primary-500/30 border-t-primary-500 rounded-full animate-spin"></div>
                                    </div>
                                )}
                            </div>
                            <button
                                type="submit"
                                disabled={code.length < 6 || isVerifying}
                                className="btn-primary w-full py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isVerifying ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        Verifying...
                                    </span>
                                ) : 'Login'}
                            </button>
                            {error && (
                                <p className="text-red-400 text-sm mt-1">
                                    {error}
                                </p>
                            )}
                        </form>
                        
                        {isPolling && (
                            <div className="flex items-center justify-center gap-2 mt-4 text-xs text-dark-400">
                                <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse"></div>
                                Waiting for confirmation...
                            </div>
                        )}
                        
                        <p className="text-xs text-dark-500 mt-4">
                            Send <span className="text-primary-400 font-mono bg-dark-800/50 px-1.5 py-0.5 rounded">/login {code || 'CODE'}</span> to the bot to get a code.
                        </p>
                    </div>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-white/[0.06]"></div>
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-dark-900/80 px-3 text-dark-500">Or open bot directly</span>
                        </div>
                    </div>

                    <BotLink code={code} />
                </div>
            </div>
        </div>
    );
}

function BotLink({ code }: { code?: string }) {
    const { data: botInfo } = useBotInfo();
    const botUrl = botInfo?.username 
        ? `https://t.me/${botInfo.username}${code ? `?start=${code}` : ''}` 
        : '#';

    return (
        <a
            href={botUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={`btn-secondary inline-flex items-center justify-center gap-2 w-full py-3 ${!botInfo?.username ? 'opacity-50 pointer-events-none' : ''}`}
        >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.18 1.897-.962 6.502-1.359 8.627-.168.9-.5 1.201-.82 1.23-.697.064-1.226-.461-1.901-.903-1.056-.692-1.653-1.123-2.678-1.799-1.185-.781-.417-1.21.258-1.911.177-.184 3.247-2.977 3.307-3.23.007-.032.015-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.139-5.062 3.345-.479.329-.913.489-1.302.481-.428-.009-1.252-.242-1.865-.442-.751-.244-1.349-.374-1.297-.789.027-.216.324-.437.893-.663 3.498-1.524 5.831-2.529 6.998-3.015 3.333-1.386 4.025-1.627 4.477-1.635.099-.002.321.023.465.141.121.099.155.232.17.325.015.094.034.31.019.478z" />
            </svg>
            Open Telegram Bot
        </a>
    );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { data: user, isLoading, error } = useCurrentUser();
    const token = localStorage.getItem('access_token');

    console.log('[ProtectedRoute] Token exists:', !!token);
    console.log('[ProtectedRoute] isLoading:', isLoading);
    console.log('[ProtectedRoute] error:', error);
    console.log('[ProtectedRoute] user:', user);

    if (!token) {
        console.log('[ProtectedRoute] No token, redirecting to login');
        return <Navigate to="/login" replace />;
    }

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-dark-950">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
                    <p className="text-dark-400">Checking authentication...</p>
                </div>
            </div>
        );
    }

    if (error) {
        console.log('[ProtectedRoute] Auth error, showing error message');
        // Show error instead of immediately redirecting
        return (
            <div className="min-h-screen flex items-center justify-center bg-dark-950 p-4">
                <div className="text-center max-w-md">
                    <p className="text-red-400 text-lg mb-4">Authentication Error</p>
                    <p className="text-dark-400 text-sm mb-4">
                        {error instanceof Error ? error.message : 'Failed to verify token'}
                    </p>
                    <button
                        onClick={() => {
                            localStorage.removeItem('access_token');
                            window.location.href = '/login';
                        }}
                        className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded text-white"
                    >
                        Go to Login
                    </button>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}

import MediaPlayer from './components/MediaPlayer';

function App() {
    return (
        <>
            <GlobalContextMenu />
            <MediaPlayer />
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/auth" element={<AuthCallback />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <FileBrowser />
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </>
    );
}

export default App;
