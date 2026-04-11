import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Login } from './pages/Login.tsx'

const isLoginPage = window.location.pathname === '/login'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isLoginPage ? <Login /> : <App />}
  </StrictMode>,
)
