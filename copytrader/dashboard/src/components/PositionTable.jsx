import { clsx } from 'clsx'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

export default function PositionTable({ positions }) {
  if (!positions || Object.keys(positions).length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-8 text-center">
        <p className="text-slate-400">No hay posiciones activas</p>
      </div>
    )
  }

  const entries = Object.entries(positions)

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Ticket Principal
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Símbolo
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Tipo
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Volumen
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Mapeos Esclavos
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">
              Estado
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700">
          {entries.map(([masterTicket, mappings]) => {
            const firstMapping = mappings[0]
            const isBuy = firstMapping?.master_volume > 0

            return (
              <tr key={masterTicket} className="hover:bg-slate-700/50">
                <td className="px-4 py-3 text-sm text-slate-100 font-mono">
                  #{masterTicket}
                </td>
                <td className="px-4 py-3 text-sm text-slate-100 font-medium">
                  {firstMapping?.symbol || '-'}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={clsx(
                      'inline-flex items-center px-2 py-1 rounded text-xs font-medium',
                      isBuy
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    )}
                  >
                    {isBuy ? (
                      <ArrowUpRight className="w-3 h-3 mr-1" />
                    ) : (
                      <ArrowDownRight className="w-3 h-3 mr-1" />
                    )}
                    {isBuy ? 'COMPRA' : 'VENTA'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-100">
                  {Math.abs(firstMapping?.master_volume || 0).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {mappings.map((m, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300"
                      >
                        {m.slave_name}: #{m.slave_ticket} ({Math.abs(m.slave_volume).toFixed(2)})
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={clsx(
                      'inline-flex px-2 py-1 rounded text-xs font-medium',
                      firstMapping?.status === 'open'
                        ? 'bg-blue-500/20 text-blue-400'
                        : firstMapping?.status === 'closed'
                        ? 'bg-slate-500/20 text-slate-400'
                        : 'bg-red-500/20 text-red-400'
                    )}
                  >
                    {firstMapping?.status === 'open' ? 'Abierta' : firstMapping?.status === 'closed' ? 'Cerrada' : 'Error'}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
