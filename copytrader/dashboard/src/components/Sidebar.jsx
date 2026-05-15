import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, TrendingUp, Settings, Activity } from 'lucide-react'
import { clsx } from 'clsx'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Panel' },
  { to: '/accounts', icon: Users, label: 'Cuentas' },
  { to: '/positions', icon: TrendingUp, label: 'Posiciones' },
  { to: '/settings', icon: Settings, label: 'Configuración' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-slate-800 border-r border-slate-700 flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-slate-700">
        <Activity className="w-8 h-8 text-blue-500 mr-3" />
        <span className="text-lg font-bold text-slate-100">CopyTrader</span>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center px-6 py-3 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-slate-700 text-blue-400 border-r-2 border-blue-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700/50'
              )
            }
          >
            <Icon className="w-5 h-5 mr-3" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-700">
        <p className="text-xs text-slate-500 text-center">v1.0.0</p>
      </div>
    </aside>
  )
}
