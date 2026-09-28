import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authAPI } from '../api/client'

const AuthContext = createContext(null)

export function applySettings(settings = {}) {
  const root = document.documentElement
  if (settings.font) root.style.setProperty('--font-family', settings.font)
  if (settings.fontSize) root.style.setProperty('--font-size', `${settings.fontSize}px`)
  if (settings.lineSpacing) root.style.setProperty('--line-spacing', settings.lineSpacing)
  if (settings.letterSpacing)
    root.style.setProperty('--letter-spacing', `${settings.letterSpacing}em`)
  if (settings.bgColor) {
    root.style.setProperty('--bg-color', settings.bgColor)
    document.body.style.backgroundColor = settings.bgColor
  }
  if (settings.textColor) {
    root.style.setProperty('--text-color', settings.textColor)
    document.body.style.color = settings.textColor
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('dyslexaid_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      authAPI
        .me()
        .then((u) => {
          setUser(u)
          if (u.settings) applySettings(u.settings)
        })
        .catch(() => {
          localStorage.removeItem('dyslexaid_token')
          setToken(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token])

  const login = useCallback(async (email, password) => {
    const data = await authAPI.signin({ email, password })
    localStorage.setItem('dyslexaid_token', data.token)
    setToken(data.token)
    setUser(data.user)
    if (data.user?.settings) applySettings(data.user.settings)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('dyslexaid_token')
    setToken(null)
    setUser(null)
  }, [])

  const updateUser = useCallback((patch) => {
    setUser((prev) => ({ ...prev, ...patch }))
  }, [])

  const updateSettings = useCallback(async (patch) => {
    const updated = await authAPI.updateSettings(patch)
    setUser((prev) => ({ ...prev, settings: { ...prev?.settings, ...patch } }))
    applySettings(patch)
    return updated
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, updateUser, updateSettings }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
