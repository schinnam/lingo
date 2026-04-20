import axios from 'axios'

export interface AdminUser {
  id: string
  email: string
  display_name: string
  role: string
}

export interface StatsResponse {
  total_terms: number
  by_status: Record<string, number>
  total_users: number
  total_votes: number
}

export interface AuditEvent {
  id: string
  actor_id: string | null
  action: string
  target_type: string | null
  target_id: string | null
  payload: Record<string, unknown> | null
  created_at: string
}

export interface Job {
  id: string
  job_type: string
  status: string
  progress_json: Record<string, unknown> | null
  error: string | null
}

export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const res = await axios.get<AdminUser[]>('/api/v1/users')
  return res.data
}

export async function updateUserRole(userId: string, role: string): Promise<AdminUser> {
  const res = await axios.patch<AdminUser>(`/api/v1/users/${userId}/role`, { role })
  return res.data
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await axios.get<StatsResponse>('/api/v1/admin/stats')
  return res.data
}

export async function fetchAudit(limit = 50, offset = 0): Promise<AuditEvent[]> {
  const res = await axios.get<AuditEvent[]>('/api/v1/admin/audit', { params: { limit, offset } })
  return res.data
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await axios.get<Job[]>('/api/v1/admin/jobs')
  return res.data
}

export async function triggerJob(jobType: string): Promise<void> {
  await axios.post(`/api/v1/admin/jobs/${jobType}/run`)
}
