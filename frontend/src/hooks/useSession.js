import { useEffect, useRef } from 'react'
import { progressAPI } from '../api/client'
import { useAuth } from '../context/AuthContext'

export function useSession() {
  const { user } = useAuth()
  const startRef = useRef(null)

  useEffect(() => {
    if (!user) return
    progressAPI.sessionStart().catch(() => {})
    startRef.current = Date.now()

    const handleUnload = () => {
      if (!startRef.current) return
      const minutes = Math.round((Date.now() - startRef.current) / 60000)
      if (minutes > 0) {
        progressAPI.sessionEnd(minutes).catch(() => {})
      }
    }

    window.addEventListener('beforeunload', handleUnload)
    return () => {
      window.removeEventListener('beforeunload', handleUnload)
      handleUnload()
    }
  }, [user])
}
