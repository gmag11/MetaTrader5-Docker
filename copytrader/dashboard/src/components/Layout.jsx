import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useHealth } from '../hooks/useHealth'
import StatusBadge from './StatusBadge'

export default function Layout() {
  const { data: health } = useHealth()

  return (
    <div className="flex h-screen bg-slate-900">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-6">
          <h1 className="text-xl font-semibold text-slate-100">Panel de Control</h1>
          <div className="flex items-center gap-4">
            <StatusBadge status={health?.status} />
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
