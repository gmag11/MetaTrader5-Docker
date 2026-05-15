import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

export function useHealth(refetchInterval = 5000) {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.getHealth,
    refetchInterval,
  })
}

export function useStatus(refetchInterval = 5000) {
  return useQuery({
    queryKey: ['status'],
    queryFn: api.getStatus,
    refetchInterval,
  })
}
