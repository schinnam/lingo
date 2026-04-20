import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Login } from './pages/Login.tsx'
import { AdminPage } from './pages/Admin.tsx'

const path = window.location.pathname

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {path === '/login' ? <Login /> : path === '/admin' ? <AdminPage /> : <App />}
  </StrictMode>,
)
