import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import logo from '../assets/logo.png';

export default function SetupPage() {
    const [loading, setLoading] = useState(false);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [configStatus, setConfigStatus] = useState<{
        telegram_bot_token_set: boolean;
        telegram_api_id_set: boolean;
        telegram_storage_channel_id_set: boolean;
        database_url: string;
    } | null>(null);
    const [fields, setFields] = useState({
        TELEGRAM_API_ID: '',
        TELEGRAM_API_HASH: '',
        TELEGRAM_BOT_TOKEN: '',
        TELEGRAM_STORAGE_CHANNEL_ID: '',
        JWT_SECRET: '',
        DATABASE_URL: '',
        REDIS_URL: '',
        ADMIN_TELEGRAM_IDS: '',
    });

    // Fetch current config status on mount
    useEffect(() => {
        api.get('/setup/status')
            .then(res => {
                setConfigStatus(res.data);
                // Pre-fill auto-detected values
                if (res.data.database_url && !res.data.database_url.startsWith('sqlite')) {
                    setFields(prev => ({ ...prev, DATABASE_URL: res.data.database_url }));
                }
            })
            .catch(() => {});
    }, []);

    const handleChange = (key: string, value: string) => {
        setFields(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setLoading(true);
        setError(null);
        try {
            await api.put('/admin/settings', fields);
            setSaved(true);
            localStorage.setItem('teleplay_setup_dirty', '1');
        } catch (e: any) {
            setError(e?.response?.data?.detail || 'Failed to save settings');
        } finally {
            setLoading(false);
        }
    };

    const isAutoConfigured = (key: string) => {
        if (!configStatus) return false;
        if (key === 'DATABASE_URL') return !!configStatus.database_url && !configStatus.database_url.startsWith('sqlite');
        if (key === 'JWT_SECRET') return true; // Auto-generated
        if (key === 'REDIS_URL') return true; // Auto-detected
        return false;
    };

    const fieldsConfig = [
        { key: 'TELEGRAM_API_ID', label: 'TELEGRAM_API_ID', desc: 'From my.telegram.org (get integer ID)', placeholder: '2345678', required: true },
        { key: 'TELEGRAM_API_HASH', label: 'TELEGRAM_API_HASH', desc: 'From my.telegram.org (34-char string)', placeholder: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6', required: true },
        { key: 'TELEGRAM_BOT_TOKEN', label: 'TELEGRAM_BOT_TOKEN', desc: 'From @BotFather on Telegram', placeholder: '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz', required: true },
        { key: 'TELEGRAM_STORAGE_CHANNEL_ID', label: 'TELEGRAM_STORAGE_CHANNEL_ID', desc: 'Telegram channel ID for storage (e.g. -1001234567890)', placeholder: '-1001234567890', required: true },
        { key: 'JWT_SECRET', label: 'JWT_SECRET', desc: 'Auto-generated secure secret', placeholder: 'auto-generated', auto: true },
        { key: 'DATABASE_URL', label: 'DATABASE_URL', desc: 'Auto-detected from Railway PostgreSQL', placeholder: 'auto-detected', auto: true },
        { key: 'REDIS_URL', label: 'REDIS_URL', desc: 'Auto-detected from Railway Redis', placeholder: 'auto-detected', auto: true },
        { key: 'ADMIN_TELEGRAM_IDS', label: 'ADMIN_TELEGRAM_IDS', desc: 'Comma-separated Telegram user IDs allowed as admins', placeholder: '123456789', required: false },
    ];

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-dark-950">
            {/* Animated gradient background */}
            <div className="absolute inset-0">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-600/15 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}>
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary-700/5 rounded-full blur-3xl"></div>
            </div>

            <div className="relative z-10 w-full max-w-2xl">
                {/* Logo & Title */}
                <div className="text-center mb-8">
                    <img src={logo} alt="TelePlay" className="w-20 h-20 mx-auto mb-4 drop-shadow-2xl" />
                    <h1 className="text-3xl font-bold text-gradient mb-2">TelePlay Setup</h1>
                    <p className="text-dark-400 text-sm">
                        {saved
                            ? 'Settings saved! You can now log in via Telegram bot.'
                            : 'Enter Telegram credentials below. Database, Redis & JWT are auto-configured.'}
                    </p>
                </div>

                {/* Card */}
                <div className="glass-panel p-6 space-y-4">
                    {!saved && (
                        <>
                            {fieldsConfig.map(({ key, label, desc, placeholder, required, auto }) => {
                                const autoConfigured = isAutoConfigured(key);
                                return (
                                    <div key={key} className={autoConfigured ? 'opacity-60' : ''}>
                                        <label className="block text-sm font-medium text-dark-200 mb-1 flex items-center gap-2">
                                            {label}
                                            {autoConfigured && (
                                                <span className="text-xs px-2 py-0.5 bg-primary-500/20 text-primary-400 rounded">Auto</span>
                                            )}
                                            {required && !autoConfigured && (
                                                <span className="text-xs text-red-400">*</span>
                                            )}
                                        </label>
                                        <p className="text-xs text-dark-500 mb-2">{desc}</p>
                                        <input
                                            type="text"
                                            value={fields[key]}
                                            onChange={e => handleChange(key, e.target.value)}
                                            placeholder={placeholder}
                                            readOnly={autoConfigured}
                                            className={`w-full rounded-lg px-4 py-2.5 text-sm placeholder:text-dark-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500/50 transition-all ${
                                                autoConfigured
                                                    ? 'bg-dark-800/50 border-white/[0.05] text-dark-400 cursor-not-allowed'
                                                    : 'bg-dark-900/60 border border-white/[0.08] text-white'
                                            }`}
                                        />
                                    </div>
                                );
                            })}

                            {error && (
                                <p className="text-red-400 text-sm mt-2">{error}</p>
                            )}

                            <button
                                onClick={handleSave}
                                disabled={loading}
                                className="w-full btn-primary py-3 mt-2 disabled:opacity-50"
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        Saving...
                                    </span>
                                ) : 'Save & Continue'}
                            </button>
                        </>
                    )}

                    {saved && (
                        <div className="text-center py-8">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                                <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <p className="text-white text-lg font-medium mb-2">Configuration Saved!</p>
                            <p className="text-dark-400 text-sm mb-6">
                                Go to <a href="/admin/settings" className="text-primary-400 hover:text-primary-300 underline">/admin/settings</a> to manage settings later.
                                Start the Telegram bot and log in.
                            </p>
                            <a
                                href="/login"
                                className="inline-block btn-primary px-8 py-3"
                            >
                                Go to Login
                            </a>
                        </div>
                    )}
                </div>

                {/* Help link */}
                <p className="text-center text-xs text-dark-600 mt-6">
                    Need help? Check{' '}
                    <a href="https://github.com/your-org/TelePlay#setup" target="_blank" rel="noreferrer" className="text-primary-500 hover:underline">
                        documentation
                    </a>
                </p>
            </div>
        </div>
    );
}