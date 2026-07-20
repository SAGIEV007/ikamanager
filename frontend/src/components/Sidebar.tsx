import {
  LayoutDashboard,
  Users,
  Globe,
  Building2,
  FlaskConical,
  Sword,
  Ship,
  TrendingUp,
  Map,
  Landmark,
  Package,
  Activity,
  Settings,
  Shield,
  Skull,
} from 'lucide-react';
import { useStore } from '../stores/useStore';

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'accounts', label: 'Accounts', icon: Users },
  { id: 'quick-actions', label: 'Quick Actions', icon: Activity },
  { id: 'cities', label: 'Cities', icon: Building2 },
  { id: 'islands', label: 'Islands', icon: Globe },
  { id: 'resources', label: 'Resources', icon: Package },
  { id: 'buildings', label: 'Buildings', icon: Landmark },
  { id: 'researches', label: 'Researches', icon: FlaskConical },
  { id: 'movements', label: 'Movements', icon: Ship },
  { id: 'army', label: 'Army', icon: Sword },
  { id: 'pirates', label: 'Pirates', icon: Skull },
  { id: 'map', label: 'Map', icon: Map },
  { id: 'score', label: 'Score', icon: TrendingUp },
  { id: 'proxies', label: 'Proxies', icon: Shield },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { currentPage, setCurrentPage, sidebarOpen } = useStore();

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-[#0f0f23] border-r border-purple-900/30 transition-all duration-300 z-50 ${
        sidebarOpen ? 'w-56' : 'w-16'
      }`}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-purple-900/30">
        <Ship className="w-6 h-6 text-purple-400 shrink-0" />
        {sidebarOpen && (
          <span className="ml-3 text-lg font-bold text-purple-300">IkaManager</span>
        )}
      </div>

      {/* Menu */}
      <nav className="mt-4 flex flex-col gap-1 px-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                isActive
                  ? 'bg-purple-700/30 text-purple-200 border border-purple-600/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className="w-4.5 h-4.5 shrink-0" />
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
