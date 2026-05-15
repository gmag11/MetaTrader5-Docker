import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

export function usePositions(refetchInterval = 3000) {
  return useQuery({
    queryKey: ['positions'],
    queryFn: api.getPositions,
    refetchInterval,
  })
}

export function usePositionStats(refetchInterval = 5000) {
  return useQuery({
    queryKey: ['positionStats'],
    queryFn: api.getPositionStats,
    refetchInterval,
  })
}
