import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import logo from '../assets/logo.png';

type SetupStep = 'bot' | 'user' | 'admin' | 'complete';

export default function SetupPage() {
    const [step, setStep] = useState<SetupStep>('bot');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [autoConfig, setAutoConfig] = useState<any>(null);

    // Bot form
    const [botToken, setBotToken] = useState('');
    const [botValid, setBotValid] = useState(false);
    const [botInfo, setBotInfo] = useState<any>(null);
    const [extraTokens, setExtraTokens] = useState<string[]>(['']);

    // User account form
    const [userPhone, setUserPhone] = useState('');
    const [userId, setUserId] = useState('');
    const [userHash, setUserHash] = useState('');
    const [userCode, setUserCode] = useState('');
    const [userPassword, setUserPassword] = useState('');
    const [codeSent, setCodeSent] = useState(false);
    const [needs2fa, setNeeds2fa] = useState(false);
    const [sessionString, setSessionString] = useState('');
    const [userVerified, setUserVerified] = useState(false);
    const [phoneCodeHash, setPhoneCodeHash] = useState('');

    // Admin form
    const [superAdminId, setSuperAdminId] = useState('');
    const [additionalAdmins, setAdditionalAdmins] = useState<string[]>(['']);

    // Fetch setup status on mount
    useEffect(() => {
        api.get('/setup/status')
            .then(res => {
                setAutoConfig(res.data);
                if (res.data.configured || res.data.has_admin) {
                    // Already setup, redirect to login
                    window.location.href = '/login';
                }
            })
            .catch(() => {});
    }, []);

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
                setBotValid(false);
            }
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Failed to validate bot token');
        } finally {
            setLoading(false);
        }
    };

    // ── User Code Flow ─────────────────────────────────────────────
    const sendUserCode = async () => {
        if (!userPhone.trim() || !userId.trim() || !userHash.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const res = await api.post('/setup/user/send-code', {
                phone: userPhone.startsWith('+') ? userPhone : `+${userPhone}`,
                api_id: parseInt(userId),
                api_hash: userHash,
            });
            if (res.data.success) {
                setCodeSent(true);
                setPhoneCodeHash(res.data.phone_code_hash || '');
            } else {
                setError(res.data.error || 'Failed to send code');
            }
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Failed to send code');
        } finally {
            setLoading(false);
        }
    };

    const verifyUserCode = async () => {
        if (!userCode.trim()) return;
        if (!phoneCodeHash) {
            setError('Phone code hash missing. Please request a new code.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const res = await api.post('/setup/user/verify-code', {
                phone: userPhone.startsWith('+') ? userPhone : `+${userPhone}`,
                api_id: parseInt(userId),
                api_hash: userHash,
                phone_code_hash: phoneCodeHash,
                code: userCode,
                password: needs2fa ? userPassword : undefined,
            });
            if (res.data.has_2fa) {
                // First time 2FA detected - need to resend code with password
                // The old phone_code_hash is now INVALID (consumed by first attempt)
                if (!needs2fa) {
                    // First 2FA detection - show password field and explain
                    setNeeds2fa(true);
                    setError('2FA enabled! Please enter your 2FA password and click "Resend Code" to get a fresh code, then enter the new code + password together.');
                } else {
                    // Already had 2FA field shown - password was wrong or code expired
                    setError('Invalid 2FA password or code expired. Please click "Resend Code" and try again with new code + password.');
                }
                return;
            }
            if (res.data.success && res.data.session_string) {
                setSessionString(res.data.session_string);
                setUserVerified(true);
            } else {
                setError(res.data.error || 'Verification failed');
            }
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Verification failed');
        } finally {
            setLoading(false);
        }
    };

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
                super_admin_id: parseInt(superAdminId),
                admin_telegram_ids: additionalAdmins
                    .filter(a => a.trim())
                    .map(a => parseInt(a)),
            });
            // Store tokens
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
            setStep('complete');
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Setup failed');
        } finally {
            setLoading(false);
        }
    };

    // ── Render ──────────────────────────────────────────────────────
    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-dark-950">
            <div className="absolute inset-0">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/15 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-700/5 rounded-full blur-3xl"></div>
            </div>

            <div className="relative z-10 w-full max-w-2xl">
                {/* Progress */}
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
                            {i < 2 && <div className={`w-16 h-1 ${(['bot', 'user', 'admin'].indexOf(step) > i) ? 'bg-green-500' : 'bg-dark-800'}`}></div>}
                        </div>
                    ))}
                </div>

                {/* Logo */}
                <div className="text-center mb-6">
                    <img src={logo} alt="TelePlay" className="w-16 h-16 mx-auto mb-3 drop-shadow-2xl" />
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
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    Bot validated: @{botInfo.username}
                                </div>
                            )}

                            <div className="pt-2">
                                <button
                                    onClick={validateBotToken}
                                    disabled={loading || !botToken.trim()}
                                    className="btn-secondary w-full py-2.5 disabled:opacity-50"
                                >
                                    Validate Bot Token
                                </button>
                            </div>

                            {botValid && (
                                <button onClick={() => setStep('user')} className="btn-primary w-full py-3">
                                    Continue to User Account
                                </button>
                            )}
                        </>
                    )}

                    {/* Step 2: User Account */}
                    {step === 'user' && (
                        <>
                            {!codeSent ? (
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
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">
                                            API ID <span className="text-red-400">*</span>
                                        </label>
                                        <p className="text-xs text-dark-500 mb-1">From my.telegram.org</p>
                                        <input
                                            type="number"
                                            value={userId}
                                            onChange={e => setUserId(e.target.value)}
                                            placeholder="2345678"
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
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
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                        />
                                    </div>
                                    <button onClick={sendUserCode} disabled={loading || !userPhone || !userId || !userHash} className="btn-primary w-full py-3 disabled:opacity-50">
                                        {loading ? 'Sending...' : 'Send Login Code'}
                                    </button>
                                </>
                            ) : !userVerified ? (
                                <>
                                    <div className="p-3 bg-primary-500/10 border border-primary-500/30 rounded-lg text-primary-300 text-sm">
                                        Code sent to {userPhone}. Enter the code from Telegram.
                                        <p className="text-xs text-primary-500/70 mt-1">Code expires in ~1-2 minutes. Use "Resend Code" if needed.</p>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-dark-200 mb-1">Login Code <span className="text-red-400">*</span></label>
                                        <input
                                            type="text"
                                            value={userCode}
                                            onChange={e => setUserCode(e.target.value)}
                                            placeholder="12345"
                                            maxLength={6}
                                            className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                        />
                                    </div>
                                    {needs2fa && (
                                        <div>
                                            <label className="block text-sm font-medium text-dark-200 mb-1">2FA Password</label>
                                            <input
                                                type="password"
                                                value={userPassword}
                                                onChange={e => setUserPassword(e.target.value)}
                                                placeholder="Your Telegram 2FA password"
                                                className="w-full bg-dark-900/60 border border-white/[0.08] rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                                            />
                                        </div>
                                    )}
                                    {needs2fa && (
                                        <p className="text-xs text-primary-500/70 mt-1">
                                            Enter the 2FA password for your Telegram account
                                        </p>
                                    )}
                                    <div className="flex gap-2">
                                        <button onClick={verifyUserCode} disabled={loading || !userCode} className="btn-primary flex-1 py-3 disabled:opacity-50">
                                            {loading ? 'Verifying...' : 'Verify & Login'}
                                        </button>
                                        <button onClick={sendUserCode} disabled={loading || !userPhone || !userId || !userHash} className="btn-secondary py-3 disabled:opacity-50" style={{whiteSpace: 'nowrap'}}>
                                            Resend Code
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-4">
                                    <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-green-500/20 flex items-center justify-center">
                                        <svg className="w-6 h-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <p className="text-green-400 font-medium">Account Connected!</p>
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
                                <p className="text-xs text-dark-500 mb-2">Your Telegram user ID (becomes SUPER_ADMIN)</p>
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
                            <button onClick={handleComplete} disabled={loading || !superAdminId} className="btn-primary w-full py-3 mt-4 disabled:opacity-50">
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
                                Your account has been created. You can now log in via Telegram.
                            </p>
                            <a href="/login" className="btn-primary inline-block px-8 py-3">
                                Go to Login
                            </a>
                            <p className="text-xs text-dark-600 mt-4">
                                Visit <a href="/admin/settings" className="text-primary-400 hover:underline">/admin/settings</a> to manage bots and accounts later.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}