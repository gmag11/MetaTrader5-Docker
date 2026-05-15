import { useState } from 'react'
import { X } from 'lucide-react'
import { clsx } from 'clsx'

const LOT_MODES = [
  { value: 'exact', label: 'Exacto', description: 'Mismo lote que el principal' },
  { value: 'fixed', label: 'Fijo', description: 'Tamaño de lote fijo' },
  { value: 'multiplier', label: 'Multiplicador', description: 'Lote × multiplicador' },
  { value: 'proportional', label: 'Proporcional', description: 'Escalar por ratio de balance' },
]

export default function SlaveConfigForm({ slave, onSave, onCancel, isLoading }) {
  const [form, setForm] = useState({
    lot_mode: slave?.lot_mode || 'exact',
    lot_value: slave?.lot_value || 1.0,
    max_lot: slave?.max_lot || 10.0,
    min_lot: slave?.min_lot || 0.01,
    magic_number: slave?.magic_number || 123456,
    invert_trades: slave?.invert_trades || false,
    max_slippage: slave?.max_slippage || 20,
    symbols_filter: slave?.symbols_filter?.join(', ') || '',
  })

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
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
    onSave(data)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg border border-slate-700 w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100">
            {slave ? `Configurar ${slave.name}` : 'Agregar Esclavo'}
          </h2>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Lot Mode */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Modo de Lote
            </label>
            <select
              name="lot_mode"
              value={form.lot_mode}
              onChange={handleChange}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {LOT_MODES.map((mode) => (
                <option key={mode.value} value={mode.value}>
                  {mode.label} - {mode.description}
                </option>
              ))}
            </select>
          </div>

          {/* Lot Value */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Valor de Lote
            </label>
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

          {/* Min/Max Lot */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Lote Mínimo
              </label>
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
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Lote Máximo
              </label>
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

          {/* Magic Number */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Número Mágico
            </label>
            <input
              type="number"
              name="magic_number"
              value={form.magic_number}
              onChange={handleChange}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Max Slippage */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Deslizamiento Máximo (puntos)
            </label>
            <input
              type="number"
              name="max_slippage"
              value={form.max_slippage}
              onChange={handleChange}
              min="0"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Symbols Filter */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Filtro de Símbolos (separados por coma, vacío para todos)
            </label>
            <input
              type="text"
              name="symbols_filter"
              value={form.symbols_filter}
              onChange={handleChange}
              placeholder="EURUSD, GBPUSD, USDJPY"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Invert Trades */}
          <div className="flex items-center">
            <input
              type="checkbox"
              name="invert_trades"
              checked={form.invert_trades}
              onChange={handleChange}
              className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
            />
            <label className="ml-2 text-sm text-slate-300">
              Invertir operaciones (COMPRA → VENTA, VENTA → COMPRA)
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-slate-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={clsx(
                'px-4 py-2 text-sm font-medium rounded-lg',
                'bg-blue-600 text-white hover:bg-blue-700',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
