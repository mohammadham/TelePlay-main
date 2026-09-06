/**
 * SetupRedirect — shown while /api/setup/status is still loading
 *
 * Prevents flickering between routes before we know whether setup is needed.
 */
import logo from './assets/logo.png';

export default function SetupRedirect() {
    return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-dark-950">
            <div className="text-center">
                <img src={logo} alt="TelePlay" className="w-16 h-16 mx-auto mb-4 opacity-80 animate-pulse-subtle" />
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500/30 border-t-primary-500 mx-auto mb-3" />
                <p className="text-dark-400 text-sm">در حال بررسی وضعیت سیستم…</p>
            </div>
        </div>
    );
}
