import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'

export function useAccounts(refetchInterval = 5000) {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: api.getAccounts,
    refetchInterval,
  })
}

export function useReconnectAccount() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (name) => api.reconnectAccount(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
    },
  })
}
