import axios from 'axios'

// Register a global 401 interceptor once at module load time.
// Any axios call that receives a 401 will redirect to /login.
// The guard prevents duplicate registration during Vite HMR hot-reloads.
let _interceptorRegistered = false
if (!_interceptorRegistered) {
  _interceptorRegistered = true
  axios.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }
      return Promise.reject(error)
    },
  )
}

export interface CurrentUser {
  id: string
  email: string
  display_name: string
  role: string
  slack_user_id: string | null
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const res = await axios.get<CurrentUser>('/auth/me')
  return res.data
}

export async function logout(): Promise<void> {
  await axios.post('/auth/logout')
  window.location.href = '/login'
}
