import { Activity, Users, TrendingUp, DollarSign, AlertCircle } from 'lucide-react'
import { useHealth } from '../hooks/useHealth'
import { useAccounts } from '../hooks/useAccounts'
import { usePositions, usePositionStats } from '../hooks/usePositions'
import StatsCard from '../components/StatsCard'
import AccountCard from '../components/AccountCard'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const { data: health, isLoading: healthLoading } = useHealth()
  const { data: accounts, isLoading: accountsLoading } = useAccounts()
  const { data: positions } = usePositions()

  const positionCount = positions?.total || 0
  const masterConnected = health?.master_connected
  const slavesConnected = health?.slaves_connected || 0
  const slavesTotal = health?.slaves_total || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Panel</h1>
          <p className="text-slate-400 mt-1">Monitorea tu sistema de copy trading</p>
        </div>
        <StatusBadge status={health?.status} size="lg" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Estado del Sistema"
          value={health?.running ? 'Ejecutando' : 'Detenido'}
          subtitle={health?.status === 'healthy' ? 'Saludable' : health?.status}
          icon={Activity}
          color={health?.running ? 'green' : 'red'}
        />
        <StatsCard
          title="Cuenta Principal"
          value={masterConnected ? 'Conectada' : 'Desconectada'}
          subtitle={accounts?.master?.name || '-'}
          icon={Users}
          color={masterConnected ? 'green' : 'red'}
        />
        <StatsCard
          title="Cuentas Esclavas"
          value={`${slavesConnected}/${slavesTotal}`}
          subtitle="conectadas"
          icon={Users}
          color={slavesConnected === slavesTotal ? 'green' : 'yellow'}
        />
        <StatsCard
          title="Posiciones Activas"
          value={positionCount}
          subtitle="siendo copiadas"
          icon={TrendingUp}
          color="blue"
        />
      </div>

      {/* Account Cards */}
      <div>
        <h2 className="text-lg font-semibold text-slate-100 mb-4">Cuentas</h2>
        {accountsLoading ? (
          <div className="text-slate-400">Cargando cuentas...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {accounts?.master && (
              <AccountCard account={accounts.master} />
            )}
            {accounts?.slaves?.map((slave) => (
              <AccountCard key={slave.name} account={slave} />
            ))}
          </div>
        )}
      </div>

      {/* Quick Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Master Balance */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Cuenta Principal</h3>
          {accounts?.master ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Balance</span>
                <span className="text-xl font-semibold text-slate-100">
                  ${accounts.master.balance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Equidad</span>
                <span className="text-xl font-semibold text-slate-100">
                  ${accounts.master.equity?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Posiciones</span>
                <span className="text-xl font-semibold text-slate-100">
                  {accounts.master.positions_count || 0}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-slate-400">No hay cuenta principal conectada</p>
          )}
        </div>

        {/* System Health */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Salud del Sistema</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Estado</span>
              <StatusBadge status={health?.status} size="sm" />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Ejecutando</span>
              <span className={health?.running ? 'text-green-400' : 'text-red-400'}>
                {health?.running ? 'Sí' : 'No'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Mapeos Activos</span>
              <span className="text-slate-100">{health?.active_mappings || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Principal Conectada</span>
              <span className={masterConnected ? 'text-green-400' : 'text-red-400'}>
                {masterConnected ? 'Sí' : 'No'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
