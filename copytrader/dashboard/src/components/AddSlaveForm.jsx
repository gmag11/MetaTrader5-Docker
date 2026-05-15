import { useState } from 'react'
import { X, AlertCircle, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'

const SERVERS = [
  { value: 'Weltrade-Demo', label: 'Weltrade Demo' },
  { value: 'Weltrade-Live', label: 'Weltrade Real' },
]

const LOT_MODES = [
  { value: 'exact', label: 'Exacto', description: 'Mismo lote que el principal' },
  { value: 'fixed', label: 'Fijo', description: 'Tamaño de lote fijo' },
  { value: 'multiplier', label: 'Multiplicador', description: 'Lote × multiplicador' },
  { value: 'proportional', label: 'Proporcional', description: 'Escalar por ratio de balance' },
]

export default function AddSlaveForm({ onSave, onCancel, isLoading }) {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    // MT5 Credentials
    login: '',
    password: '',
    server: 'Weltrade-Demo',
    // Copy Settings
    lot_mode: 'proportional',
    lot_value: 1.0,
    max_lot: 10.0,
    min_lot: 0.01,
    magic_number: Math.floor(Date.now() / 1000) % 1000000,
    invert_trades: false,
    max_slippage: 30,
    symbols_filter: '',
  })

  const [errors, setErrors] = useState({})

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }))
    }
  }

  const validateStep1 = () => {
    const newErrors = {}
    if (!form.login.trim()) {
      newErrors.login = 'El ID de cuenta es requerido'
    } else if (!/^\d+$/.test(form.login.trim())) {
      newErrors.login = 'El ID debe ser numérico'
    }
    if (!form.password.trim()) {
      newErrors.password = 'La contraseña es requerida'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleNext = () => {
    if (validateStep1()) {
      setStep(2)
    }
  }

  const handleBack = () => {
    setStep(1)
  }

  const handleSubmit = (e) => {
    e.preventDefault()

    // Generate a unique name based on login
    const name = `slave-${form.login}`

    const data = {
      // MT5 Credentials for container deployment
      mt5_login: form.login.trim(),
      mt5_password: form.password,
      mt5_server: form.server,
      // Slave configuration
      name,
      lot_mode: form.lot_mode,
      lot_value: parseFloat(form.lot_value),
      max_lot: parseFloat(form.max_lot),
      min_lot: parseFloat(form.min_lot),
      magic_number: parseInt(form.magic_number),
      invert_trades: form.invert_trades,
      max_slippage: parseInt(form.max_slippage),
      symbols_filter: form.symbols_filter
        ? form.symbols_filter.split(',').map((s) => s.trim()).filter(Boolean)
        : null,
    }
    onSave(data)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg border border-slate-700 w-full max-w-md max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-slate-100">
            Agregar Cuenta Esclava
          </h2>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-4 pt-4">
          <div className="flex items-center gap-2">
            <div className={clsx(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
              step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-400'
            )}>1</div>
            <div className={clsx('flex-1 h-1 rounded', step >= 2 ? 'bg-blue-600' : 'bg-slate-700')} />
            <div className={clsx(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
              step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-400'
            )}>2</div>
          </div>
          <div className="flex justify-between mt-2 text-xs text-slate-400">
            <span>Cuenta MT5</span>
            <span>Configuración</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          {step === 1 && (
            <div className="space-y-4">
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <p className="text-sm text-blue-200">
                  Ingresa los datos de la cuenta MetaTrader 5 que deseas agregar como esclava.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  ID de Cuenta (Login) <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  name="login"
                  value={form.login}
                  onChange={handleChange}
                  placeholder="19713032"
                  className={clsx(
                    'w-full bg-slate-700 border rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500',
                    errors.login ? 'border-red-500' : 'border-slate-600'
                  )}
                />
                {errors.login && <p className="text-xs text-red-400 mt-1">{errors.login}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Contraseña <span className="text-red-400">*</span>
                </label>
                <input
                  type="password"
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className={clsx(
                    'w-full bg-slate-700 border rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500',
                    errors.password ? 'border-red-500' : 'border-slate-600'
                  )}
                />
                {errors.password && <p className="text-xs text-red-400 mt-1">{errors.password}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Servidor <span className="text-red-400">*</span>
                </label>
                <select
                  name="server"
                  value={form.server}
                  onChange={handleChange}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {SERVERS.map((server) => (
                    <option key={server.value} value={server.value}>
                      {server.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end pt-4">
                <button
                  type="button"
                  onClick={handleNext}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Siguiente
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
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
                      {mode.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  {LOT_MODES.find((m) => m.value === form.lot_mode)?.description}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Valor
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
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Mín
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
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Máx
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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
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
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Deslizamiento
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
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  name="invert_trades"
                  checked={form.invert_trades}
                  onChange={handleChange}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-blue-500 focus:ring-blue-500"
                />
                <label className="ml-2 text-sm text-slate-300">
                  Invertir operaciones (COMPRA → VENTA)
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Filtro de Símbolos (opcional)
                </label>
                <input
                  type="text"
                  name="symbols_filter"
                  value={form.symbols_filter}
                  onChange={handleChange}
                  placeholder="EURUSD, GBPUSD (vacío = todos)"
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Warning */}
              <div className="flex items-start gap-3 p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                <AlertCircle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-200">
                  Se creará un nuevo contenedor MT5 para esta cuenta. Esto puede tardar unos minutos.
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <button
                  type="button"
                  onClick={handleBack}
                  className="px-4 py-2 text-sm text-slate-300 hover:text-slate-100"
                >
                  Atrás
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className={clsx(
                    'flex items-center px-4 py-2 text-sm font-medium rounded-lg',
                    'bg-blue-600 text-white hover:bg-blue-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  {isLoading ? 'Creando...' : 'Crear Esclava'}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
