import { clsx } from 'clsx'

export default function StatsCard({ title, value, subtitle, icon: Icon, trend, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    yellow: 'bg-yellow-500/20 text-yellow-400',
    red: 'bg-red-500/20 text-red-400',
    purple: 'bg-purple-500/20 text-purple-400',
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
          {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={clsx('p-3 rounded-lg', colors[color])}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
      {trend !== undefined && (
        <div className="mt-4 flex items-center">
          <span
            className={clsx(
              'text-sm font-medium',
              trend >= 0 ? 'text-green-400' : 'text-red-400'
            )}
          >
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
          <span className="text-sm text-slate-500 ml-2">vs last hour</span>
        </div>
      )}
    </div>
  )
}
