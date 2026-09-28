import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { notifAPI } from '../api/client'
import { useAuth } from './AuthContext'

const NotifContext = createContext(null)

export function NotifProvider({ children }) {
  const { token } = useAuth()
  const [notifs, setNotifs] = useState([])
  const [unread, setUnread] = useState(0)

  const fetchNotifs = useCallback(async () => {
    if (!token) return
    try {
      const data = await notifAPI.list()
      setNotifs(data.items || [])
      setUnread(data.unread || 0)
    } catch {}
  }, [token])

  const markRead = useCallback(async (id) => {
    await notifAPI.read(id)
    setNotifs((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
    setUnread((prev) => Math.max(0, prev - 1))
  }, [])

  const markAllRead = useCallback(async () => {
    await notifAPI.readAll()
    setNotifs((prev) => prev.map((n) => ({ ...n, read: true })))
    setUnread(0)
  }, [])

  useEffect(() => {
    if (!token) return
    fetchNotifs()
    const url = notifAPI.streamUrl()
    const es = new EventSource(url)
    es.onmessage = (e) => {
      try {
        const notif = JSON.parse(e.data)
        setNotifs((prev) => [notif, ...prev])
        setUnread((prev) => prev + 1)
      } catch {}
    }
    return () => es.close()
  }, [token, fetchNotifs])

  return (
    <NotifContext.Provider value={{ notifs, unread, fetchNotifs, markRead, markAllRead }}>
      {children}
    </NotifContext.Provider>
  )
}

export function useNotifs() {
  return useContext(NotifContext)
}
