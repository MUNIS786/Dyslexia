/**
 * frontend/src/hooks/v2/useAdaptiveEngine.js — React Hook for V2 Adaptive Learning Engine.
 * Manages recommendations, active task sessions, telemetry, and ZPD progression.
 */
import { useState, useEffect, useCallback } from 'react'
import { learningV2API } from '../../api/v2/client'
import toast from 'react-hot-toast'

export function useAdaptiveEngine(count = 4) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [recommendations, setRecommendations] = useState([])
  const [learningState, setLearningState] = useState(null)
  const [tierCalibration, setTierCalibration] = useState(null)
  const [activeActivity, setActiveActivity] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [recsRes, stateRes] = await Promise.all([
        learningV2API.getRecommendations(count).catch((e) => ({ recommendations: [] })),
        learningV2API.getState().catch((e) => null),
      ])

      setRecommendations(recsRes.recommendations || [])
      if (stateRes) {
        setLearningState(stateRes.state || null)
        setTierCalibration(stateRes.tierCalibration || null)
      }
    } catch (err) {
      console.error('Error fetching adaptive learning data:', err)
      setError(err?.response?.data?.detail || 'Failed to load adaptive learning activities.')
    } finally {
      setLoading(false)
    }
  }, [count])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const startActivity = useCallback((activity) => {
    setActiveActivity(activity)
  }, [])

  const cancelActivity = useCallback(() => {
    setActiveActivity(null)
  }, [])

  const submitAttempt = useCallback(
    async (attemptPayload) => {
      setSubmitting(true)
      try {
        const res = await learningV2API.submitAttempt(attemptPayload)

        if (res.tierChanged) {
          if (res.currentTier > res.previousTier) {
            toast.success(`🎉 Level Up! You're now on Level ${res.currentTier}!`, {
              duration: 5000,
              icon: '🚀',
            })
          } else {
            toast('Adjusted difficulty to keep learning comfortable and steady.', {
              icon: '🌱',
            })
          }
        } else if (res.celebration) {
          toast.success(res.message || 'Awesome job!', { icon: '⭐' })
        }

        // Refresh state and recommendations
        await fetchData()
        setActiveActivity(null)
        return res
      } catch (err) {
        console.error('Failed to submit activity attempt:', err)
        toast.error('Could not save your progress. Please try again.')
        throw err
      } finally {
        setSubmitting(false)
      }
    },
    [fetchData]
  )

  return {
    loading,
    error,
    recommendations,
    learningState,
    tierCalibration,
    activeActivity,
    submitting,
    startActivity,
    cancelActivity,
    submitAttempt,
    refresh: fetchData,
  }
}
