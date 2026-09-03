/**
 * SetupPage - TelePlay Initial Setup Wizard
 *
 * A complete, step-by-step wizard for initial TelePlay configuration.
 * Handles bot token validation, Telegram account authentication (with 2FA),
 * and super admin creation.
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

type SetupStep = 'bot' | 'user' | 'admin' | 'complete';
type AuthState = 'idle' | 'sending' | 'code_sent' | 'verifying' | '2fa_required' | '2fa_verifying' | 'success' | 'error';

export default function SetupPage() {
    const [step, setStep] = useState<SetupStep>('bot');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [autoConfig, setAutoConfig] = useState<any>(null);

    // Bot form state
    const [botToken, setBotToken] = useState('');
    const [botValid, setBotValid] = useState(false);
    const [botInfo, setBotInfo] = useState<any>(null);
    const [extraTokens, setExtraTokens] = useState<string[]>(['']);

    // User authentication state
    const [userPhone, setUserPhone] = useState('');
    const [userId, setUserId] = useState('');
    const [userHash, setUserHash] = useState('');
    const [userProxy, setUserProxy] = useState('');  // Proxy configuration
    const [proxySkipped, setProxySkipped] = useState(false); // Track if user skipped proxy
    const [proxyTestState, setProxyTestState] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
    const [proxyTestError, setProxyTestError] = useState<string | null>(null);
    const [isSendingCode, setIsSendingCode] = useState(false); // Lock form while sending
    const [isVerifyingCode, setIsVerifyingCode] = useState(false); // Lock form while verifying
    const [resendCooldown, setResendCooldown] = useState(0); // Resend button cooldown in seconds
    const [userCode, setUserCode] = useState('');
    const [userPassword, setUserPassword] = useState('');
    const [authState, setAuthState] = useState<AuthState>('idle');
    const [sessionString, setSessionString] = useState('');
    const [phoneCodeHash, setPhoneCodeHash] = useState('');
    const [needs2fa, setNeeds2fa] = useState(false);
    const [lastErrorCode, setLastErrorCode] = useState<string | null>(null);
    const [userVerified, setUserVerified] = useState(false);

    // Admin form state
    const [superAdminId, setSuperAdminId] = useState('');
    const [additionalAdmins, setAdditionalAdmins] = useState<string[]>(['']);

    // Redirect handled by parent App.tsx based on setupData.configured.
    // Do NOT fetch status here — that caused a redirect loop.
    // We only store autoConfig for UI display if needed.
    useEffect(() => {
        // No self-redirect: App.tsx owns the setup→login routing.
    }, []);

    // ── Resend Cooldown Timer ────────────────────────────────────────
    useEffect(() => {
        if (resendCooldown > 0) {
            const timer = setInterval(() => {
                setResendCooldown(prev => prev - 1);
            }, 1000);
            return () => clearInterval(timer);
        }
    }, [resendCooldown]);

    // ── Bot Token Validation ───────────────────────────────────────
    const validateBotToken = async () => {
        if (!botToken.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const res = await api.post('/setup/bot/validate', { token: botToken });
            if (res.data.valid) {
                setBotValid(true);
                setBotInfo(res.data);
            } else {
                setError(res.data.error || 'Invalid bot token');
            }
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Failed to validate bot token');
        } finally {
            setLoading(false);
        }
    };

    // ── Telegram Auth Handlers ─────────────────────────────────────

    /**
     * Send login code to phone number.
     * Handles timeout, expired codes, and network errors gracefully.
     * Locks form during send, navigates to code entry on success.
     */
    const sendUserCode = useCallback(async () => {
        if (!userPhone.trim() || !userId.trim() || !userHash.trim()) {
            setError('Please enter phone, API ID, and API hash');
            return;
        }

        setIsSendingCode(true);
        setAuthState('sending');
        setError(null);
        setLastErrorCode(null);
        setLoading(true);

        try {
            const res = await api.post('/setup/user/send-code', {
                phone: userPhone.startsWith('+') ? userPhone : `+${userPhone}`,
                api_id: parseInt(userId),
                api_hash: userHash,
                proxy: userProxy.trim() || undefined,
            });

            if (res.data.success) {
                // SUCCESS: Immediately navigate to code entry phase
                const codeHash = res.data.phone_code_hash || '';
                setPhoneCodeHash(codeHash);
                setAuthState('code_sent');
                setUserCode('');
                setUserPassword('');
                setNeeds2fa(false);
                setError(null);
                setLastErrorCode(null);
                
                // Start 120-second resend cooldown
                setResendCooldown(120);
            } else {
                // Handle specific error types - only show error if actually failed
                const errorCode = res.data.error;
                const errorMessage = res.data.message || res.data.error || 'Failed to send code';

                // Don't show "network error" if code was actually sent
                if (errorCode === 'timeout') {
                    setError('Connection timeout. Check your internet connection or proxy settings.');
                } else if (errorCode === 'phone_code_expired') {
                    setError('Request timed out. Please check your network and try again.');
                } else if (errorCode === 'network_error') {
                    // Only show network error if no code was sent
                    setError('Network error. If you are in a restricted region, please configure a Telegram proxy.');
                } else {
                    setError(errorMessage);
                }
                setLastErrorCode(errorCode);
                setAuthState('error');
            }
        } catch (e: any) {
            const errorMsg = e?.response?.data?.message || e?.response?.data?.detail || 'Failed to send code';
            setError(errorMsg);
            setAuthState('error');
            setLastErrorCode('unknown');
        } finally {
            setIsSendingCode(false);
            setLoading(false);
        }
    }, [userPhone, userId, userHash, userProxy]);

    /**
     * Test proxy connection by checking if we can connect to Telegram through the proxy.
     * Uses a lightweight connection test without sending a real code.
     */
    const testProxyConnection = useCallback(async () => {
        if (!userProxy.trim()) return;
        
        setProxyTestState('testing');
        setProxyTestError(null);

        try {
            // Use a lightweight test - just check if proxy allows connection to Telegram
            // We'll use the validate bot token endpoint which only needs HTTP connectivity
            // Or we can do a simple connection test
            const res = await api.post('/setup/user/send-code', {
                phone: '+999999999999', // Test number - will fail validation but test proxy
                api_id: parseInt(userId) || 123456,
                api_hash: userHash || 'test',
                proxy: userProxy.trim(),
            });

            // Check if proxy worked (connection established)
            // If we get invalid_credentials or phone_invalid, proxy worked
            // If we get network_error or proxy_error, proxy failed
            if (res.data.error === 'network_error' || res.data.error === 'proxy_error') {
                throw new Error(res.data.message || 'Proxy connection failed');
            }
            
            // If we get here, proxy connection worked (even if auth failed)
            setProxyTestState('success');
            setProxyTestError(null);
        } catch (e: any) {
            const errorMsg = e?.response?.data?.message || e?.response?.data?.detail || e.message || 'Proxy test failed';
            setProxyTestState('error');
            setProxyTestError(errorMsg);
        }
    }, [userProxy, userId, userHash]);

    /**
     * Verify login code (and optional 2FA password).
     * On first attempt with 2FA, returns has_2fa=true.
     * On retry with password, completes the full auth flow.
     * Locks form during verification.
     */
    const verifyUserCode = useCallback(async () => {
        if (!userCode.trim()) {
            setError('Please enter the verification code');
            return;
        }
        if (!phoneCodeHash) {
            setError('No code hash available. Please request a new code first.');
            return;
        }

        setIsVerifyingCode(true);
        setAuthState(needs2fa ? '2fa_verifying' : 'verifying');
        setError(null);
        setLoading(true);

        try {
            const res = await api.post('/setup/user/verify-code', {
                phone: userPhone.startsWith('+') ? userPhone : `+${userPhone}`,
                api_id: parseInt(userId),
                api_hash: userHash,
                phone_code_hash: phoneCodeHash,
                code: userCode,
                password: needs2fa ? userPassword : undefined,
                proxy: userProxy.trim() || undefined,
            });

            if (res.data.has_2fa && !needs2fa) {
                // First time detecting 2FA - show password field but keep user on this step
                setNeeds2fa(true);
                setError(
                    'This account has 2FA enabled. Please enter your 2FA password below and click Verify.'
                );
                setAuthState('2fa_required');
            } else if (res.data.success && res.data.session_string) {
                setSessionString(res.data.session_string);
                setAuthState('success');
                setUserVerified(true);
            } else {
                const errorCode = res.data.error;
                const errorMessage = res.data.message || res.data.error || 'Verification failed';

                if (errorCode === 'phone_code_expired') {
                    setError('Code expired! Please click "Resend Code" to get a fresh code.');
                    setAuthState('error');
                    setLastErrorCode(errorCode);
                } else if (errorCode === 'invalid_code') {
                    setError('Invalid code. Please check and try again.');
                    setAuthState('error');
                    setLastErrorCode(errorCode);
                } else {
                    setError(errorMessage);
                    setAuthState('error');
                    setLastErrorCode(errorCode);
                }
            }
        } catch (e: any) {
            setError(e?.response?.data?.message || e?.response?.data?.detail || 'Verification failed');
            setAuthState('error');
            setLastErrorCode('unknown');
        } finally {
            setIsVerifyingCode(false);
            setLoading(false);
        }
    }, [userCode, phoneCodeHash, needs2fa, userPassword, userPhone, userId, userHash, userProxy]);

    // ── Complete Setup ─────────────────────────────────────────────
    const handleComplete = async () => {
        if (!botValid || !userVerified) return;
        setLoading(true);
        setError(null);
        try {
            const res = await api.post('/setup/complete', {
                bot_token: botToken,
                extra_bot_tokens: extraTokens.filter(t => t.trim()),
                user_phone: userPhone.startsWith('+') ? userPhone : `+${userPhone}`,
                user_api_id: parseInt(userId),
                user_api_hash: userHash,
                user_session_string: sessionString,
                user_2fa_password: userPassword || null,
                user_proxy: proxySkipped ? null : (userProxy.trim() || null),
                super_admin_id: parseInt(superAdminId),
                admin_telegram_ids: additionalAdmins
                    .filter(a => a.trim())
                    .map(a => parseInt(a)),
            });
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
            window.location.href = '/login';
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Setup failed');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Reset the auth flow back to send code stage.
     * Clears all auth state including 2FA flag.
     */
    const resetAuthFlow = useCallback(() => {
        setAuthState('idle');
        setPhoneCodeHash('');
        setUserCode('');
        setUserPassword('');
        setNeeds2fa(false);
        setLastErrorCode(null);
        setUserVerified(false);
    }, []);

    /**
     * Go back to previous step after successful completion of current step.
     */
    const goToStep = useCallback((s: SetupStep) => {
        setStep(s);
        setError(null);
    }, []);

    // ── Render ──────────────────────────────────────────────────────
    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-dark-950">
            <div className="absolute inset-0">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/15 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-700/5 rounded-full blur-3xl"></div>
            </div>

            <div className="relative z-10 w-full max-w-2xl">
                {/* Progress Indicator */}
                <div className="flex justify-center mb-8">
                    {['Bot Token', 'User Account', 'Super Admin'].map((label, i) => (
                        <div key={label} className="flex items-center">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                                ['bot', 'user', 'admin'].includes(step) &&
                                ['bot', 'user', 'admin'][i] === step ? 'bg-primary-500 text-white' :
                                ['bot', 'user', 'admin'].includes(step) &&
                                ['bot', 'user', 'admin'].indexOf(step) > i ? 'bg-green-500 text-white' :
                                'bg-dark-800 text-dark-500'
                            }`}>
                                {(['bot', 'user', 'admin'].indexOf(step) > i) ? '✓' : i + 1}
                            </div>
                            {i < 2 && (
                                <div className={`w-16 h-1 ${
                                    ['bot', 'user', 'admin'].indexOf(step) > i ? 'bg-green-500' : 'bg-dark-800'
                                }`}></div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Logo */}
                <div className="text-center mb-6">
                    <img src="/assets/logo.png" alt="TelePlay" className="w-16 h-16 mx-auto mb-3 drop-shadow-2xl" />
                    <h1 className="text-2xl font-bold text-gradient mb-1">TelePlay Setup</h1>
                    <p className="text-dark-400 text-sm">
                        {step === 'bot' && 'Configure your Telegram bot'}
                        {step === 'user' && 'Set up your user account'}
                        {step === 'admin' && 'Create your admin account'}
                        {step === 'complete' && 'Setup complete!'}
                    </p>
                </div>

                {/* Card */}
                <div className="glass-panel p-6 space-y-4">
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Step 1: Bot Token */}
                    {step === 'bot' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-dark-200 mb-1">
                                    Main Bot Token <span className="text-red-400">*</span>
                                </label>
                                <p className="text-xs text-dark-500 mb-2">From @BotFather</p>
                                <input
                                    type="text"
                                    value={botToken}
                                    onChange={e => setBotToken(e.target.value)}
                                    placeholder="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
                                    className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                />
                            </div>

                            {botInfo && (
                                <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm flex items-center gap-2">
                                    <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    Bot validated: @{botInfo.username}
                                </div>
                            )}

                            <button
                                onClick={validateBotToken}
                                disabled={loading || !botToken.trim()}
                                className="btn-secondary w-full py-2.5 disabled:opacity-50"
                            >
                                Validate Bot Token
                            </button>

                            {botValid && (
                                <button onClick={() => setStep('user')} className="btn-primary w-full py-3">
                                    Continue to User Account
                                </button>
                            )}
                        </>
                    )}

                    {/* Step 2: User Account Authentication */}
                    {step === 'user' && (
                        <>
                            {/* Phase 1: Enter credentials */}
                            {authState === 'idle' || (authState === 'error' && !phoneCodeHash) ? (
                                <>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            Phone Number <span className="text-red-400">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={userPhone}
                                            onChange={e => setUserPhone(e.target.value)}
                                            placeholder="+989xxxxxxxxx"
                                            disabled={isSendingCode}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            API ID <span className="text-red-400">*</span>
                                        </label>
                                        <p className="text-xs text-dark-500 mb-1">Get from my.telegram.org</p>
                                        <input
                                            type="number"
                                            value={userId}
                                            onChange={e => setUserId(e.target.value)}
                                            placeholder="2345678"
                                            disabled={isSendingCode}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            API Hash <span className="text-red-400">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={userHash}
                                            onChange={e => setUserHash(e.target.value)}
                                            placeholder="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
                                            disabled={isSendingCode}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            Proxy (Optional)
                                        </label>
                                        <p className="text-xs text-dark-500 mb-1">SOCKS5 or HTTP proxy for restricted networks. Format: socks5://user:pass@host:port or http://host:port</p>
                                        <input
                                            type="text"
                                            value={userProxy}
                                            onChange={e => setUserProxy(e.target.value)}
                                            placeholder="socks5://user:pass@host:1080 or http://host:8080"
                                            disabled={isSendingCode}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                        />
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={testProxyConnection}
                                            disabled={loading || isSendingCode || !userProxy.trim()}
                                            className="btn-secondary w-full py-2.5 disabled:opacity-50"
                                        >
                                            {loading && proxyTestState === 'testing' ? 'Testing...' : 'Test Proxy Connection'}
                                        </button>
                                        <button
                                            onClick={() => setProxySkipped(!proxySkipped)}
                                            className={`btn-secondary w-full py-2.5 ${proxySkipped ? 'bg-green-500/20 border-green-500/30 text-green-400' : ''}`}
                                        >
                                            {proxySkipped ? '✓ Proxy Skipped' : 'Skip Proxy (No Proxy Needed)'}
                                        </button>
                                    </div>
                                    {proxyTestState === 'success' && (
                                        <p className="text-xs text-green-400 mt-1">✓ Proxy connection successful!</p>
                                    )}
                                    {proxyTestState === 'error' && (
                                        <p className="text-xs text-red-400 mt-1">✗ Proxy connection failed: {proxyTestError}</p>
                                    )}
                                    <button
                                        onClick={sendUserCode}
                                        disabled={loading || isSendingCode || !userPhone.trim() || !userId.trim() || !userHash.trim()}
                                        className="btn-primary w-full py-3 disabled:opacity-50"
                                    >
                                        {isSendingCode ? 'Sending Code...' : 'Send Login Code'}
                                    </button>
                                    {lastErrorCode === 'timeout' && (
                                        <p className="text-xs text-yellow-400 mt-1">
                                            💡 Tip: Configure TELEGRAM_PROXY environment variable if you are behind a firewall.
                                        </p>
                                    )}
                                </>
                            ) : null}

                            {/* Phase 2: Enter verification code */}
                            {authState === 'sending' || authState === 'code_sent' || authState === '2fa_required' || authState === 'verifying' || authState === '2fa_verifying' || (authState === 'error' && !!phoneCodeHash) ? (
                                <>
                                    <div className="p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg text-primary-300 text-sm">
                                        {authState === 'sending' ? (
                                            `Sending code to ${userPhone}...`
                                        ) : (
                                            <>
                                                Code sent to {userPhone}.
                                                <p className="text-xs text-primary-500/70 mt-1">
                                                    Enter the code from Telegram. Expires in ~2 minutes.
                                                    <button onClick={resetAuthFlow} className="text-primary-400 ml-2 hover:underline focus:outline-none">Change phone number</button>
                                                </p>
                                            </>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            Login Code <span className="text-red-400">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={userCode}
                                            onChange={e => setUserCode(e.target.value)}
                                            placeholder="12345"
                                            maxLength={6}
                                            disabled={isVerifyingCode || authState === 'sending'}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                        />
                                    </div>
                                    {(authState === '2fa_required' || authState === '2fa_verifying') && (
                                        <>
                                            <div>
                                                <label className="block text-sm font-medium text-dark-200 mb-1">
                                                    2FA Password
                                                </label>
                                                <input
                                                    type="password"
                                                    value={userPassword}
                                                    onChange={e => setUserPassword(e.target.value)}
                                                    placeholder="Your Telegram 2FA password"
                                                    disabled={isVerifyingCode || authState === '2fa_verifying'}
                                                    className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                                                />
                                            </div>
                                            <p className="text-xs text-primary-500/70">
                                                This account has 2FA enabled. Enter your password below.
                                            </p>
                                        </>
                                    )}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={verifyUserCode}
                                            disabled={loading || isVerifyingCode || authState === 'sending' || !userCode.trim()}
                                            className="btn-primary flex-1 py-3 disabled:opacity-50"
                                        >
                                            {isVerifyingCode ? (authState === '2fa_verifying' ? 'Checking 2FA...' : 'Verifying...') : 'Verify & Login'}
                                        </button>
                                        <button
                                            onClick={sendUserCode}
                                            disabled={loading || isSendingCode || authState === 'sending' || resendCooldown > 0}
                                            className="btn-secondary py-3 disabled:opacity-50"
                                            style={{ whiteSpace: 'nowrap' }}
                                        >
                                            {resendCooldown > 0
                                                ? `Resend in ${Math.floor(resendCooldown / 60)}:${String(resendCooldown % 60).padStart(2, '0')}`
                                                : 'Resend Code'}
                                        </button>
                                    </div>
                                    {lastErrorCode === 'phone_code_expired' && (
                                        <p className="text-xs text-yellow-400 mt-1">
                                            ⚠️ Code expired! Click "Resend Code" above to get a fresh code.
                                        </p>
                                    )}
                                </>
                            ) : null}

                            {/* Phase 3: Success */}
                            {authState === 'success' && (
                                <div className="text-center py-4">
                                    <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-green-500/20 flex items-center justify-center">
                                        <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <p className="text-green-400 font-medium">Account Connected!</p>
                                    <p className="text-dark-400 text-sm mt-1">@{userVerified ? 'verified' : ''}</p>
                                    <button onClick={() => setStep('admin')} className="btn-primary w-full py-3 mt-4">
                                        Continue to Admin Setup
                                    </button>
                                </div>
                            )}
                        </>
                    )}

                    {/* Step 3: Super Admin */}
                    {step === 'admin' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-dark-200 mb-1">
                                    Your Telegram ID <span className="text-red-400">*</span>
                                </label>
                                <p className="text-xs text-dark-500 mb-2">Becomes SUPER_ADMIN</p>
                                <input
                                    type="number"
                                    value={superAdminId}
                                    onChange={e => setSuperAdminId(e.target.value)}
                                    placeholder="123456789"
                                    className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                />
                            </div>
                            {additionalAdmins.map((adminId, idx) => (
                                <div key={idx}>
                                    <label className="block text-sm font-medium text-dark-200 mb-1">
                                        Additional Admin {idx + 1}
                                    </label>
                                    <input
                                        type="number"
                                        value={adminId}
                                        onChange={e => {
                                            const newIds = [...additionalAdmins];
                                            newIds[idx] = e.target.value;
                                            setAdditionalAdmins(newIds);
                                        }}
                                        placeholder="123456789"
                                        className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                    />
                                </div>
                            ))}
                            <button
                                onClick={() => setAdditionalAdmins([...additionalAdmins, ''])}
                                className="btn-secondary w-full py-2 text-sm"
                            >
                                + Add Another Admin
                            </button>
                            <button
                                onClick={handleComplete}
                                disabled={loading || !superAdminId.trim()}
                                className="btn-primary w-full py-3 mt-4 disabled:opacity-50"
                            >
                                {loading ? 'Creating Accounts...' : 'Complete Setup'}
                            </button>
                        </>
                    )}

                    {/* Step 4: Complete */}
                    {step === 'complete' && (
                        <div className="text-center py-8">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                                <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <p className="text-white text-xl font-bold mb-2">Welcome to TelePlay!</p>
                            <p className="text-dark-400 text-sm mb-6">
                                Setup complete. You can now log in via Telegram.
                            </p>
                            <a href="/login" className="btn-primary inline-block px-8 py-3">
                                Go to Login
                            </a>
                            <p className="text-xs text-dark-600 mt-4">
                                Visit{' '}
                                <a href="/admin/settings" className="text-primary-400 hover:underline">
                                    /admin/settings
                                </a>{' '}
                                to manage bots and accounts.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
