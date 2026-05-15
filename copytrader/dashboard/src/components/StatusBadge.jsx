import { clsx } from 'clsx'

const statusLabels = {
  healthy: 'Saludable',
  degraded: 'Degradado',
  unhealthy: 'Sin conexión',
}

export default function StatusBadge({ status, size = 'md' }) {
  const isHealthy = status === 'healthy'
  const isDegraded = status === 'degraded'
  const label = statusLabels[status] || 'Desconocido'

  return (
    <div
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-3 py-1 text-sm',
        size === 'lg' && 'px-4 py-1.5 text-base',
        isHealthy && 'bg-green-500/20 text-green-400',
        isDegraded && 'bg-yellow-500/20 text-yellow-400',
        !isHealthy && !isDegraded && 'bg-red-500/20 text-red-400'
      )}
    >
      <span
        className={clsx(
          'w-2 h-2 rounded-full mr-2',
          isHealthy && 'bg-green-400',
          isDegraded && 'bg-yellow-400',
          !isHealthy && !isDegraded && 'bg-red-400'
        )}
      />
      {label}
    </div>
  )
}
