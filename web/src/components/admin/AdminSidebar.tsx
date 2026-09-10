import {
    LayoutDashboard, Users, HardDrive, Database, Megaphone, Server, Settings2,
    Bot, UserCog, Crown, FileText, Upload, Home, X, ChevronRight, ChevronLeft, Menu, LogOut,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../../assets/logo.png';
import { useState, useEffect, useRef } from 'react';

// ── Admin route map ──────────────────────────────────────────────────────────
const ADMIN_ROUTE_MAP: Record<string, { icon: any; label: string; section?: string }> = {
    '/admin':              { icon: LayoutDashboard, label: 'Overview',      section: 'overview' },
    '/admin/users':        { icon: Users,           label: 'Users',         section: 'users' },
    '/admin/files':        { icon: HardDrive,       label: 'Files',         section: 'files' },
    '/admin/cache':        { icon: Database,        label: 'Cache',         section: 'cache' },
    '/admin/ads':          { icon: Megaphone,       label: 'Ads',           section: 'ads' },
    '/admin/system':       { icon: Server,          label: 'System',        section: 'system' },
    '/admin/settings':     { icon: Settings2,       label: 'Settings',      section: 'settings' },
    '/admin/bots':         { icon: Bot,             label: 'Bots',          section: 'bots' },
    '/admin/accounts':     { icon: UserCog,         label: 'Accounts',      section: 'accounts' },
    '/admin/admins':       { icon: Crown,           label: 'Admins',        section: 'admins' },
    '/admin/seo':          { icon: FileText,        label: 'SEO',           section: 'seo' },
    '/admin/upload':       { icon: Upload,          label: 'Upload',        section: 'upload' },
    '/admin/channel-import': { icon: Database,      label: 'Channel Import', section: 'channel-import' },
};

interface Props {
    isDesktop: boolean;
    isOpen: boolean;
    onClose: () => void;
    onToggleCollapse: () => void;
    isCollapsed: boolean;
}

export default function AdminSidebar({
    isDesktop, isOpen, onClose, onToggleCollapse, isCollapsed
}: Props) {
    const navigate = useNavigate();
    const location = useLocation();
    const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
    const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const sidebarRef = useRef<HTMLDivElement>(null);
    const isPhone = window.innerWidth < 768;
    const hasOverlay = isPhone && isOpen;
    const [isHovering, setIsHovering] = useState(false);

    useEffect(() => {
        return () => { if (hoverTimer.current) clearTimeout(hoverTimer.current); };
    }, []);

    // Desktop → always open
    if (isDesktop) {
        return (
            <aside className="fixed left-0 top-0 w-64 h-full bg-[#0a0a0a] border-r border-white/10 flex flex-col z-50">
                <AdminSidebarContent
                    isAdmin={true}
                    navigate={navigate}
                    ROUTE_MAP={ADMIN_ROUTE_MAP}
                    location={location}
                />
            </aside>
        );
    }

    return (
        <>
            {/* Icon strip button (always visible on tablet/phone when collapsed) */}
            {!isCollapsed && (
                <button
                    onClick={onToggleCollapse}
                    className="fixed top-3 left-3 z-50 w-10 h-10 rounded-xl bg-[#181818]/90 backdrop-blur border border-white/10 flex items-center justify-center text-white/70 hover:text-white transition-all"
                    aria-label="Toggle sidebar"
                >
                    <Menu className="w-5 h-5" />
                </button>
            )}

            {/* Icon strip (collapsed state on tablet) */}
            {isCollapsed && !isPhone && (
                <aside className="fixed left-0 top-0 w-14 h-full bg-[#0a0a0a] border-r border-white/10 flex flex-col items-center py-4 z-50">
                    <img src={logo} alt="Logo" className="w-8 h-8 mb-6 rounded" />
                    <nav className="flex flex-col gap-2 w-full px-2">
                        {Object.entries(ADMIN_ROUTE_MAP).map(([route, { icon: Icon, label }]) => {
                            const isActive = location.pathname === route || location.pathname.startsWith(route + '/');
                            return (
                                <TooltipButton
                                    key={route}
                                    label={label}
                                    isActive={isActive}
                                    onClick={() => handleNavClick(route)}
                                >
                                    <Icon className="w-5 h-5" />
                                </TooltipButton>
                            );
                        })}
                    </nav>
                    <div className="mt-auto px-2 w-full">
                        <TooltipButton label="Back to App" isActive={false} onClick={() => navigate('/')}>
                            <Home className="w-5 h-5" />
                        </TooltipButton>
                        <TooltipButton label="Logout" isActive={false} onClick={() => setShowLogoutConfirm(true)}>
                            <LogOut className="w-5 h-5 text-red-400" />
                        </TooltipButton>
                    </div>
                </aside>
            )}

            {/* Full sidebar (expanded on tablet, slide-over on phone) */}
            {(isCollapsed || !isPhone) && (
                <>
                    {hasOverlay && (
                        <div
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                            onClick={onClose}
                        />
                    )}
                    <aside
                        ref={sidebarRef}
                        className={`
                            fixed left-0 top-0 h-full bg-[#0a0a0a] border-r border-white/10
                            flex flex-col z-50 transition-all duration-300 ease-in-out
                            ${isPhone
                                ? isOpen ? 'w-64 translate-x-0' : 'w-64 -translate-x-full'
                                : isCollapsed
                                    ? 'w-14 hover:w-64 group'
                                    : 'w-64'
                            }
                        `}
                        onMouseEnter={() => {
                            if (isCollapsed && !isPhone) {
                                setIsHovering(true);
                                hoverTimer.current = setTimeout(() => {
                                    if (sidebarRef.current) {
                                        sidebarRef.current.style.width = '16rem';
                                    }
                                }, 150);
                            }
                        }}
                        onMouseLeave={() => {
                            if (hoverTimer.current) clearTimeout(hoverTimer.current);
                            setIsHovering(false);
                            if (isCollapsed && !isPhone && sidebarRef.current) {
                                sidebarRef.current.style.width = '3.5rem';
                            }
                        }}
                    >
                        <AdminSidebarContent
                            onClose={onClose}
                            onToggleCollapse={onToggleCollapse}
                            isCollapsed={isCollapsed}
                            isHovering={isHovering}
                            isAdmin={true}
                            navigate={navigate}
                            ROUTE_MAP={ADMIN_ROUTE_MAP}
                            location={location}
                            isPhone={isPhone}
                            showLogoutConfirm={showLogoutConfirm}
                            setShowLogoutConfirm={setShowLogoutConfirm}
                        />
                    </aside>
                </>
            )}

            {showLogoutConfirm && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-[#181818] border border-white/10 rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl">
                        <div className="p-6 text-center">
                            <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <LogOut className="w-6 h-6 text-red-500" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Confirm Logout</h3>
                            <p className="text-white/60 text-sm">Are you sure you want to end your session?</p>
                        </div>
                        <div className="p-4 border-t border-white/5 flex gap-3 bg-[#282828]">
                            <button onClick={() => setShowLogoutConfirm(false)} className="flex-1 px-4 py-2 rounded-lg text-white/60 hover:bg-white/5 transition-colors font-medium">Cancel</button>
                            <button onClick={() => { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); window.location.href = '/login'; }} className="flex-1 px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white font-medium shadow-lg shadow-red-500/20">Logout</button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );

    function handleNavClick(route: string) {
        onClose();
        navigate(route);
    }
}

// ── Admin sidebar content ────────────────────────────────────────────────────
interface AdminContentProps {
    onClose?: () => void;
    onToggleCollapse?: () => void;
    isCollapsed?: boolean;
    isHovering?: boolean;
    isAdmin: boolean;
    navigate: (path: string) => void;
    ROUTE_MAP: Record<string, { icon: any; label: string }>;
    location: ReturnType<typeof useLocation>;
    isPhone?: boolean;
    showLogoutConfirm?: boolean;
    setShowLogoutConfirm?: (v: boolean) => void;
}

function AdminSidebarContent({
    onClose, onToggleCollapse, isCollapsed, isHovering, isAdmin, navigate, ROUTE_MAP, location, isPhone,
    showLogoutConfirm: _showLogoutConfirm, setShowLogoutConfirm: _setShowLogoutConfirm
}: AdminContentProps) {
    const isIconOnly = isCollapsed && !isPhone && !isHovering;

    return (
        <>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-4 border-b border-white/5">
                <div className="flex items-center gap-3 overflow-hidden">
                    <img src={logo} alt="Logo" className="w-8 h-8 rounded shrink-0" />
                    <span className={`font-bold text-white truncate transition-all duration-300 ${
                        isIconOnly ? 'opacity-0 w-0' : 'opacity-100'
                    }`}>
                        TelePlay Admin
                    </span>
                </div>
                {/* Toggle button (tablet only) */}
                {onToggleCollapse && (
                    <button
                        onClick={onToggleCollapse}
                        className={`shrink-0 p-1.5 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors ${
                            isIconOnly ? 'invisible' : ''
                        }`}
                        aria-label="Toggle sidebar"
                    >
                        {isIconOnly ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
                    </button>
                )}
                {/* Close button (phone only) */}
                {isPhone && onClose && (
                    <button onClick={onClose} className="p-1.5 rounded-lg text-white/50 hover:text-white hover:bg-white/10" aria-label="Close">
                        <X className="w-5 h-5" />
                    </button>
                )}
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
                <p className={`px-3 py-2 text-xs font-semibold text-white/30 uppercase tracking-wider ${
                    isIconOnly ? 'text-center' : ''
                }`}>
                    {isIconOnly ? '···' : 'Admin'}
                </p>
                {Object.entries(ROUTE_MAP).map(([route, { icon: Icon, label }]) => {
                    const isActive = location.pathname === route || location.pathname.startsWith(route + '/');
                    return (
                        <TooltipButton
                            key={route}
                            label={label}
                            isActive={isActive}
                            onClick={() => { navigate(route); if (isPhone) onClose?.(); }}
                            isCollapsed={isIconOnly}
                        >
                            <Icon className="w-5 h-5 shrink-0" />
                            <span className={`truncate transition-opacity ${
                                isIconOnly ? 'opacity-0' : 'opacity-100'
                            }`}>{label}</span>
                        </TooltipButton>
                    );
                })}
            </nav>

            {/* Admin + Logout */}
            <div className="px-2 pb-3 space-y-1">
                <TooltipButton label="Back to App" isActive={false}
                    onClick={() => { navigate('/'); if (isPhone) onClose?.(); }}
                    isCollapsed={isIconOnly}>
                    <Home className="w-5 h-5 shrink-0" />
                    <span className="truncate">Back to App</span>
                </TooltipButton>
                <TooltipButton label="Logout" isActive={false}
                    onClick={() => _setShowLogoutConfirm?.(true)}
                    isCollapsed={isIconOnly}>
                    <LogOut className="w-5 h-5 shrink-0" />
                    <span className="truncate">Logout</span>
                </TooltipButton>
            </div>
        </>
    );
}

// ── Tooltip button for collapsed icon mode ───────────────────────────────────
interface TooltipButtonProps {
    children: React.ReactNode;
    label: string;
    isActive: boolean;
    onClick: () => void;
    isCollapsed?: boolean;
}

function TooltipButton({ children, label, isActive, onClick, isCollapsed }: TooltipButtonProps) {
    const [showTooltip, setShowTooltip] = useState(false);
    const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

    const handleMouseEnter = () => {
        if (isCollapsed) {
            timer.current = setTimeout(() => setShowTooltip(true), 200);
        }
    };
    const handleMouseLeave = () => {
        if (timer.current) clearTimeout(timer.current);
        setShowTooltip(false);
    };

    return (
        <div className="relative">
            <button
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                onClick={onClick}
                className={`
                    w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all
                    ${isActive
                        ? 'text-[#1DB954] bg-[#1DB954]/10'
                        : 'text-white/60 hover:text-white hover:bg-white/10'
                    }
                    ${isCollapsed ? 'justify-center' : ''}
                `}
                title={label}
            >
                {children}
            </button>
            {/* Tooltip */}
            {isCollapsed && showTooltip && (
                <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2.5 py-1.5 bg-[#1e1e1e] border border-white/10 rounded-lg text-white text-sm whitespace-nowrap z-[60] shadow-xl">
                    {label}
                </div>
            )}
        </div>
    );
}
