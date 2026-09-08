import { Files, Clock, PlayCircle, LogOut, HardDrive, X, Users, Settings2, Home, Search, List, Download } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../assets/logo.png';
import { useAppStore } from '../lib/store';
import { useStorageStats, formatFileSize, useLogoutAll, useCurrentUser } from '../lib/api';
import { useState, useEffect } from 'react';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    alwaysOpen?: boolean;
}

const musicRoutes: Record<string, string> = {
    home: '/music',
    search: '/music/search',
    playlists: '/music/playlists',
    downloads: '/music/downloads',
    history: '/music/history',
};

export default function Sidebar({ isOpen, onClose, alwaysOpen = false }: SidebarProps) {
    const { activeSection, setActiveSection } = useAppStore();
    const navigate = useNavigate();
    const location = useLocation();

    // On desktop with alwaysOpen, force open; otherwise respect isOpen prop
    const [mobileOpen, setMobileOpen] = useState(false);
    const open = alwaysOpen || (isOpen !== undefined ? isOpen : mobileOpen);

    // Listen for global open-sidebar event (dispatched from MobileBottomNav or hamburger)
    useEffect(() => {
        const handler = () => setMobileOpen(true);
        window.addEventListener('open-sidebar', handler);
        return () => window.removeEventListener('open-sidebar', handler);
    }, []);

    // Sync activeSection from current route so the highlight matches the URL
    useEffect(() => {
        const entry = Object.entries(musicRoutes).find(([, r]) => location.pathname === r || location.pathname.startsWith(r + '/'));
        if (entry) setActiveSection(entry[0] as any);
    }, [location.pathname, setActiveSection]);
    const { data: storage } = useStorageStats();
    const { data: user } = useCurrentUser();
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const [showLogoutAllConfirm, setShowLogoutAllConfirm] = useState(false);
    const logoutAllMutation = useLogoutAll();

    const isAdmin = (user as any)?.role === 'ADMIN' || (user as any)?.role === 'SUPER_ADMIN';

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    };

    const handleLogoutAll = async () => {
        try {
            await logoutAllMutation.mutateAsync();
            handleLogout();
        } catch (error) {
            console.error('Failed to logout all', error);
            handleLogout();
        }
    };

    const musicRoutes: Record<string, string> = {
        home: '/music',
        search: '/music/search',
        playlists: '/music/playlists',
        downloads: '/music/downloads',
        history: '/music/history',
    };

    const handleNavClick = (section: string) => {
        onClose();
        const route = musicRoutes[section];
        if (route) {
            navigate(route);
        } else {
            setActiveSection(section as 'files' | 'recent' | 'continue_watching');
        }
    };

    const NavItem = ({ section, icon: Icon, label }: { section: string; icon: any; label: string }) => (
        <button
            onClick={() => handleNavClick(section as any)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                activeSection === section
                    ? 'text-[#1DB954]'
                    : 'text-white/60 hover:text-white hover:bg-white/10'
            }`}
        >
            <Icon className="w-5 h-5 shrink-0" />
            <span className="truncate">{label}</span>
        </button>
    );

    return (
        <>
            {/* Mobile Overlay */}
            <div
                className={`fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-opacity duration-300 ${
                    isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
                }`}
                onClick={onClose}
            />

            <aside className={`
                w-64 bg-black border-r border-white/10 flex flex-col shrink-0
                fixed inset-y-0 left-0 z-40
                transition-transform duration-300 ease-in-out shadow-2xl
                ${isOpen ? 'translate-x-0' : '-translate-x-full'}
            `}>
                {/* Logo Area */}
                <div className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <img
                            src={logo}
                            alt="TelePlay Logo"
                            className="w-8 h-8 rounded shadow-lg"
                        />
                        <span className="text-lg font-bold text-white">
                            TelePlay
                        </span>
                    </div>
                    <button
                        onClick={onClose}
                        className="md:hidden p-1 text-white/60 hover:text-white"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="flex-1 px-2 space-y-1 overflow-y-auto">
                    <p className="px-3 py-2 text-xs font-semibold text-white/40 uppercase tracking-wider">
                        Menu
                    </p>
                    <NavItem section="home" icon={Home} label="Music" />
                    <NavItem section="search" icon={Search} label="Search" />
                    <NavItem section="playlists" icon={List} label="Playlists" />
                    <NavItem section="downloads" icon={Download} label="Downloads" />
                    <NavItem section="history" icon={Clock} label="Recently Played" />

                    <p className="px-3 py-2 mt-4 text-xs font-semibold text-white/40 uppercase tracking-wider">
                        Library
                    </p>
                    <NavItem section="files" icon={Files} label="My Files" />
                    <NavItem section="recent" icon={Clock} label="Recently Added" />
                    <NavItem section="continue_watching" icon={PlayCircle} label="Continue Watching" />
                </nav>

                {/* Storage Info */}
                <div className="p-4 m-3 rounded-xl bg-[#181818] border border-white/5">
                    <div className="flex items-center gap-2 mb-2 text-sm text-white/60">
                        <HardDrive className="w-4 h-4" />
                        <span>Storage</span>
                    </div>
                    {storage ? (
                        <>
                            <div className="text-xl font-bold text-white mb-1">
                                {formatFileSize(storage.total_size)}
                            </div>
                            <div className="text-xs text-[#1DB954]">
                                Unlimited Storage 🚀
                            </div>
                        </>
                    ) : (
                        <div className="h-4 w-20 bg-[#282828] rounded animate-pulse" />
                    )}
                </div>

                {/* Admin Link */}
                {isAdmin && (
                    <div className="px-3 pb-2">
                        <a href="/admin" className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors">
                            <Settings2 className="w-5 h-5" />
                            <span>Admin Panel</span>
                        </a>
                    </div>
                )}

                {/* Logout */}
                <div className="p-4 border-t border-white/10">
                    <button
                        onClick={() => setShowLogoutConfirm(true)}
                        className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-white/60 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                        <LogOut className="w-5 h-5" />
                        <span className="font-medium">Logout</span>
                    </button>
                    <button
                        onClick={() => setShowLogoutAllConfirm(true)}
                        className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-white/60 hover:text-orange-400 hover:bg-orange-500/10 transition-colors mt-1"
                    >
                        <Users className="w-5 h-5" />
                        <span className="font-medium">Logout All</span>
                    </button>
                </div>
            </aside>

            {/* Logout Modal */}
            {showLogoutConfirm && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="bg-[#181818] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl animate-scale-in">
                        <div className="p-6 text-center">
                            <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <LogOut className="w-6 h-6 text-red-500" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Confirm Logout</h3>
                            <p className="text-white/60 text-sm">
                                Are you sure you want to end your session?
                            </p>
                        </div>
                        <div className="p-4 border-t border-white/5 flex gap-3 bg-[#282828]">
                            <button
                                onClick={() => setShowLogoutConfirm(false)}
                                className="flex-1 px-4 py-2 rounded-lg text-white/60 hover:bg-white/5 transition-colors font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleLogout}
                                className="flex-1 px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white font-medium transition-colors shadow-lg shadow-red-500/20"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Logout All Modal */}
            {showLogoutAllConfirm && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
                    <div className="bg-[#181818] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl animate-scale-in">
                        <div className="p-6 text-center">
                            <div className="w-12 h-12 bg-orange-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Users className="w-6 h-6 text-orange-500" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Logout Everywhere</h3>
                            <p className="text-white/60 text-sm">
                                This will end your session on <strong>all devices</strong>. Are you sure?
                            </p>
                        </div>
                        <div className="p-4 border-t border-white/5 flex gap-3 bg-[#282828]">
                            <button
                                onClick={() => setShowLogoutAllConfirm(false)}
                                className="flex-1 px-4 py-2 rounded-lg text-white/60 hover:bg-white/5 transition-colors font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleLogoutAll}
                                className="flex-1 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-medium transition-colors shadow-lg shadow-orange-500/20"
                                disabled={logoutAllMutation.isPending}
                            >
                                {logoutAllMutation.isPending ? 'Logging out...' : 'Logout All'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}