import { useState } from 'react'
import { Settings as SettingsIcon, Save, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { useSlaves, useUpdateSlave } from '../hooks/useSlaves'

const LOT_MODES = [
  { value: 'exact', label: 'Exacto', description: 'Copiar tamaño exacto del principal' },
  { value: 'fixed', label: 'Fijo', description: 'Usar un tamaño de lote fijo' },
  { value: 'multiplier', label: 'Multiplicador', description: 'Multiplicar lote del principal' },
  { value: 'proportional', label: 'Proporcional', description: 'Escalar por ratio de balance' },
]

export default function Settings() {
  const { data: slaves, isLoading } = useSlaves()
  const updateSlave = useUpdateSlave()

  const [selectedSlave, setSelectedSlave] = useState(null)
  const [form, setForm] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const handleSelectSlave = (slave) => {
    setSelectedSlave(slave)
    setForm({
      lot_mode: slave.lot_mode || 'exact',
      lot_value: slave.lot_value || 1.0,
      max_lot: slave.max_lot || 10.0,
      min_lot: slave.min_lot || 0.01,
      magic_number: slave.magic_number || 123456,
      invert_trades: slave.invert_trades || false,
      max_slippage: slave.max_slippage || 20,
      symbols_filter: slave.symbols_filter?.join(', ') || '',
    })
    setSaveSuccess(false)
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSave = () => {
    if (!selectedSlave || !form) return

    const data = {
      ...form,
      lot_value: parseFloat(form.lot_value),
      max_lot: parseFloat(form.max_lot),
      min_lot: parseFloat(form.min_lot),
      magic_number: parseInt(form.magic_number),
      max_slippage: parseInt(form.max_slippage),
      symbols_filter: form.symbols_filter
        ? form.symbols_filter.split(',').map((s) => s.trim()).filter(Boolean)
        : null,
    }

    updateSlave.mutate(
      { name: selectedSlave.name, data },
      {
        onSuccess: () => {
          setSaveSuccess(true)
          setTimeout(() => setSaveSuccess(false), 3000)
        },
      }
    )
  }

  if (isLoading) {
    return <div className="text-slate-400">Cargando...</div>
  }

  const slavesList = slaves || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Configuración</h1>
        <p className="text-slate-400 mt-1">Configura los parámetros de las cuentas esclavas</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Slave List */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <div className="p-4 border-b border-slate-700">
            <h2 className="font-semibold text-slate-100">Cuentas Esclavas</h2>
          </div>
          <div className="divide-y divide-slate-700">
            {slavesList.length === 0 ? (
              <div className="p-4 text-slate-400 text-sm">No hay cuentas esclavas configuradas</div>
            ) : (
              slavesList.map((slave) => (
                <button
                  key={slave.name}
                  onClick={() => handleSelectSlave(slave)}
                  className={clsx(
                    'w-full px-4 py-3 text-left hover:bg-slate-700/50 transition-colors',
                    selectedSlave?.name === slave.name && 'bg-slate-700'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-slate-100">{slave.name}</p>
                      <p className="text-sm text-slate-400">
                        {slave.host}:{slave.port}
                      </p>
                    </div>
                    <span
                      className={clsx(
                        'px-2 py-1 rounded text-xs font-medium',
                        slave.connected
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      )}
                    >
                      {slave.connected ? 'En línea' : 'Fuera de línea'}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Configuration Form */}
        <div className="lg:col-span-2 bg-slate-800 rounded-lg border border-slate-700">
          {!selectedSlave ? (
            <div className="p-8 text-center">
              <SettingsIcon className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">Selecciona una cuenta esclava para configurar</p>
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                <h2 className="font-semibold text-slate-100">
                  Configurar {selectedSlave.name}
                </h2>
                {saveSuccess && (
                  <span className="text-sm text-green-400">¡Configuración guardada!</span>
                )}
              </div>

              <div className="p-4 space-y-5">
                {/* Lot Configuration */}
                <div className="border-b border-slate-700 pb-5">
                  <h3 className="text-sm font-medium text-slate-300 mb-4">Configuración de Lote</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Modo de Lote</label>
                      <select
                        name="lot_mode"
                        value={form.lot_mode}
                        onChange={handleChange}
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {LOT_MODES.map((mode) => (
                          <option key={mode.value} value={mode.value}>
                            {mode.label}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-slate-500 mt-1">
                        {LOT_MODES.find((m) => m.value === form.lot_mode)?.description}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Valor de Lote</label>
                      <input
                        type="number"
                        name="lot_value"
                        value={form.lot_value}
                        onChange={handleChange}
                        step="0.01"
                        min="0"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Lote Mínimo</label>
                      <input
                        type="number"
                        name="min_lot"
                        value={form.min_lot}
                        onChange={handleChange}
                        step="0.01"
                        min="0.01"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Lote Máximo</label>
                      <input
                        type="number"
                        name="max_lot"
                        value={form.max_lot}
                        onChange={handleChange}
                        step="0.01"
                        min="0.01"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Trade Configuration */}
                <div className="border-b border-slate-700 pb-5">
                  <h3 className="text-sm font-medium text-slate-300 mb-4">Configuración de Operaciones</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Número Mágico</label>
                      <input
                        type="number"
                        name="magic_number"
                        value={form.magic_number}
                        onChange={handleChange}
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Deslizamiento Máximo (puntos)</label>
                      <input
                        type="number"
                        name="max_slippage"
                        value={form.max_slippage}
                        onChange={handleChange}
                        min="0"
                        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div className="mt-4">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        name="invert_trades"
                        checked={form.invert_trades}
                        onChange={handleChange}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
                      />
                      <span className="ml-2 text-sm text-slate-300">
                        Invertir operaciones (COMPRA → VENTA, VENTA → COMPRA)
                      </span>
                    </label>
                  </div>
                </div>

                {/* Symbol Filter */}
                <div>
                  <h3 className="text-sm font-medium text-slate-300 mb-4">Filtro de Símbolos</h3>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">
                      Símbolos Permitidos (separados por coma, vacío para todos)
                    </label>
                    <input
                      type="text"
                      name="symbols_filter"
                      value={form.symbols_filter}
                      onChange={handleChange}
                      placeholder="EURUSD, GBPUSD, USDJPY"
                      className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Dejar vacío para copiar todos los símbolos
                    </p>
                  </div>
                </div>

                {/* Warning */}
                <div className="flex items-start gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                  <AlertCircle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                  <div className="text-sm text-yellow-200">
                    Los cambios se aplicarán solo a nuevas operaciones. Las posiciones existentes no serán afectadas.
                  </div>
                </div>

                {/* Save Button */}
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleSave}
                    disabled={updateSlave.isPending}
                    className={clsx(
                      'flex items-center px-6 py-2 rounded-lg font-medium',
                      'bg-blue-600 text-white hover:bg-blue-700',
                      'disabled:opacity-50 disabled:cursor-not-allowed'
                    )}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {updateSlave.isPending ? 'Guardando...' : 'Guardar Cambios'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
