import { useState } from 'react'
import { RefreshCw, Filter, X } from 'lucide-react'
import { clsx } from 'clsx'
import { usePositions, usePositionStats } from '../hooks/usePositions'
import PositionTable from '../components/PositionTable'

export default function Positions() {
  const { data: positions, isLoading, refetch, isFetching } = usePositions()
  const { data: stats } = usePositionStats()

  const [symbolFilter, setSymbolFilter] = useState('')
  const [slaveFilter, setSlaveFilter] = useState('')

  const handleRefresh = () => {
    refetch()
  }

  // Get unique symbols and slave names for filter options
  const allMappings = positions?.mappings ? Object.values(positions.mappings).flat() : []
  const uniqueSymbols = [...new Set(allMappings.map((m) => m.symbol).filter(Boolean))]
  const uniqueSlaves = [...new Set(allMappings.map((m) => m.slave_name).filter(Boolean))]

  // Filter positions
  const filteredPositions = positions?.mappings
    ? Object.fromEntries(
        Object.entries(positions.mappings).filter(([_, mappings]) => {
          const matchesSymbol = !symbolFilter || mappings.some((m) => m.symbol === symbolFilter)
          const matchesSlave = !slaveFilter || mappings.some((m) => m.slave_name === slaveFilter)
          return matchesSymbol && matchesSlave
        })
      )
    : {}

  const hasFilters = symbolFilter || slaveFilter

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Posiciones</h1>
          <p className="text-slate-400 mt-1">Monitorea operaciones activas y mapeos</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center px-4 py-2 bg-slate-700 text-slate-100 rounded-lg hover:bg-slate-600 disabled:opacity-50"
        >
          <RefreshCw className={clsx('w-4 h-4 mr-2', isFetching && 'animate-spin')} />
          Actualizar
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400">Total Posiciones</p>
          <p className="text-2xl font-bold text-slate-100">{stats?.total_positions || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400">Mapeos Activos</p>
          <p className="text-2xl font-bold text-slate-100">{stats?.active_mappings || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400">Abiertas</p>
          <p className="text-2xl font-bold text-green-400">{stats?.open || 0}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-sm text-slate-400">Cerradas</p>
          <p className="text-2xl font-bold text-slate-400">{stats?.closed || 0}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-400">Filtros:</span>
          </div>

          <select
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los Símbolos</option>
            {uniqueSymbols.map((symbol) => (
              <option key={symbol} value={symbol}>
                {symbol}
              </option>
            ))}
          </select>

          <select
            value={slaveFilter}
            onChange={(e) => setSlaveFilter(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas las Esclavas</option>
            {uniqueSlaves.map((slave) => (
              <option key={slave} value={slave}>
                {slave}
              </option>
            ))}
          </select>

          {hasFilters && (
            <button
              onClick={() => {
                setSymbolFilter('')
                setSlaveFilter('')
              }}
              className="flex items-center text-sm text-slate-400 hover:text-slate-100"
            >
              <X className="w-4 h-4 mr-1" />
              Limpiar
            </button>
          )}
        </div>
      </div>

      {/* Positions Table */}
      {isLoading ? (
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-8 text-center">
          <p className="text-slate-400">Cargando posiciones...</p>
        </div>
      ) : (
        <PositionTable positions={filteredPositions} />
      )}

      {/* Auto-refresh notice */}
      <div className="text-center text-sm text-slate-500">
        Las posiciones se actualizan automáticamente cada 5 segundos
      </div>
    </div>
  )
}
