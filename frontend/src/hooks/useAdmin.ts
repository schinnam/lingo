import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAdminUsers,
  updateUserRole,
  fetchStats,
  fetchAudit,
  fetchJobs,
  triggerJob,
} from '../api/admin'

export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: fetchAdminUsers,
  })
}

export function useUpdateUserRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      updateUserRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })
}

export function useStats() {
  return useQuery({
    queryKey: ['admin-stats'],
    queryFn: fetchStats,
  })
}

export function useAudit(limit: number, offset: number) {
  return useQuery({
    queryKey: ['admin-audit', limit, offset],
    queryFn: () => fetchAudit(limit, offset),
  })
}

export function useJobs() {
  return useQuery({
    queryKey: ['admin-jobs'],
    queryFn: fetchJobs,
  })
}

export function useTriggerJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobType: string) => triggerJob(jobType),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-jobs'] }),
  })
}
