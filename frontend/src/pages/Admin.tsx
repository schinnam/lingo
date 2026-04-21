import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fetchCurrentUser, logout, type CurrentUser } from '../api/auth'
import {
  useAdminUsers,
  useUpdateUserRole,
  useStats,
  useAudit,
  useJobs,
  useTriggerJob,
} from '../hooks/useAdmin'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
})

type Tab = 'users' | 'stats' | 'audit' | 'jobs'

const ROLES = ['member', 'editor', 'admin'] as const

function UsersTab() {
  const { data: users, isLoading, isError } = useAdminUsers()
  const updateRole = useUpdateUserRole()

  if (isLoading) return <LoadingRow />
  if (isError) return <ErrorRow />

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
          <th className="py-3 pr-4 font-medium">Name</th>
          <th className="py-3 pr-4 font-medium">Email</th>
          <th className="py-3 font-medium">Role</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {users?.map((user) => (
          <tr key={user.id} className="hover:bg-gray-50">
            <td className="py-3 pr-4 font-medium text-gray-900">{user.display_name}</td>
            <td className="py-3 pr-4 text-gray-500">{user.email}</td>
            <td className="py-3">
              <select
                value={user.role}
                onChange={(e) => updateRole.mutate({ userId: user.id, role: e.target.value })}
                className="border border-gray-200 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Role for ${user.display_name}`}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function StatsTab() {
  const { data: stats, isLoading, isError } = useStats()

  if (isLoading) return <LoadingRow />
  if (isError) return <ErrorRow />
  if (!stats) return null

  const statCards = [
    { label: 'Total Terms', value: stats.total_terms },
    { label: 'Total Users', value: stats.total_users },
    { label: 'Total Votes', value: stats.total_votes },
    ...Object.entries(stats.by_status).map(([status, count]) => ({
      label: `${status.charAt(0).toUpperCase() + status.slice(1)} Terms`,
      value: count,
    })),
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {statCards.map(({ label, value }) => (
        <div key={label} className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-sm text-gray-500 mt-1">{label}</div>
        </div>
      ))}
    </div>
  )
}

function AuditTab() {
  const PAGE_SIZE = 50
  const [offset, setOffset] = useState(0)
  const { data: events, isLoading, isError } = useAudit(PAGE_SIZE, offset)

  if (isLoading) return <LoadingRow />
  if (isError) return <ErrorRow />

  return (
    <div>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="py-3 pr-4 font-medium">Action</th>
            <th className="py-3 pr-4 font-medium">Target</th>
            <th className="py-3 font-medium">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {events?.map((ev) => (
            <tr key={ev.id} className="hover:bg-gray-50">
              <td className="py-3 pr-4 font-mono text-gray-800">{ev.action}</td>
              <td className="py-3 pr-4 text-gray-500">
                {ev.target_type ? `${ev.target_type} ${ev.target_id?.slice(0, 8)}…` : '—'}
              </td>
              <td className="py-3 text-gray-400 whitespace-nowrap">
                {new Date(ev.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center gap-3 mt-4">
        <button
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={offset === 0}
          className="px-3 py-1 text-sm border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-500">Showing {offset + 1}–{offset + (events?.length ?? 0)}</span>
        <button
          onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={!events || events.length < PAGE_SIZE}
          className="px-3 py-1 text-sm border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}

const JOB_TYPES = ['LingoDiscoveryJob', 'LingoStalenessJob']

function JobsTab() {
  const { data: jobs, isLoading, isError } = useJobs()
  const triggerJob = useTriggerJob()

  if (isLoading) return <LoadingRow />
  if (isError) return <ErrorRow />

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        {JOB_TYPES.map((jt) => (
          <button
            key={jt}
            onClick={() => triggerJob.mutate(jt)}
            disabled={triggerJob.isPending}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Run {jt.replace('Lingo', '').replace('Job', '')}
          </button>
        ))}
      </div>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="py-3 pr-4 font-medium">Job</th>
            <th className="py-3 pr-4 font-medium">Status</th>
            <th className="py-3 font-medium">Error</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {jobs?.map((job) => (
            <tr key={job.id} className="hover:bg-gray-50">
              <td className="py-3 pr-4 font-mono text-gray-800">{job.job_type}</td>
              <td className="py-3 pr-4">
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                  job.status === 'success' ? 'bg-green-100 text-green-700' :
                  job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                  job.status === 'failed' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {job.status}
                </span>
              </td>
              <td className="py-3 text-red-400 text-xs">{job.error ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function LoadingRow() {
  return <div className="py-12 text-center text-sm text-gray-400">Loading…</div>
}

function ErrorRow() {
  return <div className="py-12 text-center text-sm text-red-400">Failed to load. Check your connection and try again.</div>
}

const TAB_LABELS: Record<Tab, string> = {
  users: 'Users',
  stats: 'Stats',
  audit: 'Audit Log',
  jobs: 'Jobs',
}

function AdminInner() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [authStatus, setAuthStatus] = useState<'loading' | 'ready' | 'forbidden'>('loading')
  const [activeTab, setActiveTab] = useState<Tab>('users')

  useEffect(() => {
    fetchCurrentUser()
      .then((user) => {
        if (user.role !== 'admin') {
          window.location.href = '/'
          return
        }
        setCurrentUser(user)
        setAuthStatus('ready')
      })
      .catch(() => {
        // 401 interceptor handles redirect to /login
        setAuthStatus('forbidden')
      })
  }, [])

  if (authStatus === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <span className="text-gray-400 text-sm">Loading…</span>
      </div>
    )
  }

  if (authStatus === 'forbidden') return null

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-8 py-3 flex items-center gap-6">
        <a href="/" className="text-xl font-bold font-mono text-gray-900 whitespace-nowrap hover:text-gray-700">
          Lingo
        </a>
        <span className="text-gray-300">/</span>
        <h1 className="text-sm font-semibold text-gray-700">Admin</h1>
        <div className="flex-1" />
        {currentUser && (
          <span className="text-sm text-gray-500">{currentUser.display_name}</span>
        )}
        <button
          onClick={() => logout()}
          className="whitespace-nowrap text-sm text-gray-500 hover:text-gray-900"
        >
          Logout
        </button>
      </header>

      <div className="border-b border-gray-200 bg-white px-8">
        <nav className="flex gap-1" role="tablist">
          {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </div>

      <main className="flex-1 overflow-y-auto px-8 py-6">
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'stats' && <StatsTab />}
        {activeTab === 'audit' && <AuditTab />}
        {activeTab === 'jobs' && <JobsTab />}
      </main>
    </div>
  )
}

export function AdminPage() {
  return (
    <QueryClientProvider client={queryClient}>
      <AdminInner />
    </QueryClientProvider>
  )
}
