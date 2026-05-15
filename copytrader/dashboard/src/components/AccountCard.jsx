import { clsx } from 'clsx'
import { RefreshCw, User, Server } from 'lucide-react'
import { useReconnectAccount } from '../hooks/useAccounts'

export default function AccountCard({ account, showReconnect = true }) {
  const reconnect = useReconnectAccount()
  const isMaster = account.role === 'master'

  const handleReconnect = () => {
    reconnect.mutate(account.name)
  }

  return (
    <div className="bg-slate-800 rounded-lg p-5 border border-slate-700">
      <div className="flex items-start justify-between">
        <div className="flex items-center">
          <div
            className={clsx(
              'p-2 rounded-lg mr-3',
              isMaster ? 'bg-purple-500/20' : 'bg-blue-500/20'
            )}
          >
            {isMaster ? (
              <User className="w-5 h-5 text-purple-400" />
            ) : (
              <Server className="w-5 h-5 text-blue-400" />
            )}
          </div>
          <div>
            <h3 className="font-medium text-slate-100">{account.name}</h3>
            <p className="text-sm text-slate-400">{account.role === 'master' ? 'Principal' : 'Esclavo'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'inline-flex items-center px-2 py-1 rounded text-xs font-medium',
              account.connected
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
            )}
          >
            {account.connected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-slate-500">Balance</p>
          <p className="text-lg font-semibold text-slate-100">
            ${account.balance?.toLocaleString(undefined, { minimumFractionDigits: 2 }) || '0.00'}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">Equidad</p>
          <p className="text-lg font-semibold text-slate-100">
            ${account.equity?.toLocaleString(undefined, { minimumFractionDigits: 2 }) || '0.00'}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-400">
          {account.positions_count || 0} posiciones
        </span>
        {showReconnect && !account.connected && (
          <button
            onClick={handleReconnect}
            disabled={reconnect.isPending}
            className="flex items-center text-blue-400 hover:text-blue-300 disabled:opacity-50"
          >
            <RefreshCw className={clsx('w-4 h-4 mr-1', reconnect.isPending && 'animate-spin')} />
            Reconectar
          </button>
        )}
      </div>

      {account.last_error && (
        <div className="mt-3 p-2 bg-red-500/10 rounded text-xs text-red-400">
          {account.last_error}
        </div>
      )}
    </div>
  )
}
