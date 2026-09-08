import { Home, Search, List, Download, Clock } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  route: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'music', label: 'Music', icon: Home, route: '/music' },
  { id: 'search', label: 'Search', icon: Search, route: '/music/search' },
  { id: 'playlists', label: 'Playlists', icon: List, route: '/music/playlists' },
  { id: 'downloads', label: 'Downloads', icon: Download, route: '/music/downloads' },
  { id: 'history', label: 'History', icon: Clock, route: '/music/history' },
];

export default function MobileBottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (route: string) =>
    location.pathname === route || location.pathname.startsWith(route + '/');

  return (
    <nav
      className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 md:hidden"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center gap-1.5 px-2 py-1.5 rounded-2xl bg-[#181818]/95 backdrop-blur-xl border border-white/10 shadow-2xl">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.route);
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.route)}
              aria-label={item.label}
              aria-current={active ? 'page' : undefined}
              className={`
                flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl transition-all duration-200
                ${active
                  ? 'bg-[#1DB954] text-black font-semibold shadow-lg shadow-[#1DB954]/20'
                  : 'text-white/60 hover:text-white hover:bg-white/10'
                }
              `}
            >
              <Icon className={`w-5 h-5 shrink-0 ${active ? 'fill-black' : ''}`} />
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}