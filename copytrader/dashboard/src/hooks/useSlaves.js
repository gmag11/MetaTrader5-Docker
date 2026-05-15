import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api/client'

export function useSlaves(refetchInterval = 5000) {
  return useQuery({
    queryKey: ['slaves'],
    queryFn: api.getSlaves,
    refetchInterval,
  })
}

export function useCreateSlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data) => api.createSlave(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slaves'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useDeploySlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data) => api.deploySlave(data),
    onSuccess: () => {
      // Wait a bit for container to start before refreshing
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['slaves'] })
        queryClient.invalidateQueries({ queryKey: ['accounts'] })
        queryClient.invalidateQueries({ queryKey: ['health'] })
      }, 5000)
    },
  })
}

export function useUpdateSlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, data }) => api.updateSlave(name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slaves'] })
    },
  })
}

export function useDeleteSlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, closePositions }) => api.deleteSlave(name, closePositions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slaves'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useEnableSlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (name) => api.enableSlave(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slaves'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}

export function useDisableSlave() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, closePositions }) => api.disableSlave(name, closePositions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slaves'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })
}
