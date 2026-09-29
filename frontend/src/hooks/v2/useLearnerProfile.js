/**
 * frontend/src/hooks/v2/useLearnerProfile.js — Hooks for accessing and updating V2 Learner Profile.
 */
import { useState, useEffect, useCallback } from 'react'
import { learnerV2API } from '../../api/v2/client'

export function useLearnerProfile() {
  const [profile, setProfile] = useState(null)
  const [learningState, setLearningState] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [profRes, stateRes] = await Promise.allSettled([
        learnerV2API.getProfile(),
        learnerV2API.getState(),
      ])

      if (profRes.status === 'fulfilled' && profRes.value?.status === 'ok') {
        setProfile(profRes.value.profile)
      } else if (profRes.status === 'rejected') {
        setError(profRes.reason?.response?.data?.detail || 'Failed to load learner profile')
      }

      if (stateRes.status === 'fulfilled' && stateRes.value?.status === 'ok') {
        setLearningState(stateRes.value.learning_state)
      }
    } catch (err) {
      setError(err?.message || 'Unexpected error loading profile')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const updateProfile = useCallback(async (patchData) => {
    try {
      const res = await learnerV2API.updateProfile(patchData)
      if (res?.status === 'ok') {
        setProfile(res.profile)
        return res.profile
      }
    } catch (err) {
      const errMsg = err?.response?.data?.detail || 'Failed to update profile'
      setError(errMsg)
      throw err
    }
  }, [])

  return {
    profile,
    learningState,
    loading,
    error,
    refresh: loadData,
    updateProfile,
  }
}

export function useStudentLearnerProfile(studentId) {
  const [profile, setProfile] = useState(null)
  const [studentName, setStudentName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    if (!studentId) return
    setLoading(true)
    setError(null)
    try {
      const res = await learnerV2API.getStudentProfile(studentId)
      if (res?.status === 'ok') {
        setProfile(res.profile)
        setStudentName(res.student_name || '')
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load student profile')
    } finally {
      setLoading(false)
    }
  }, [studentId])

  useEffect(() => {
    loadData()
  }, [loadData])

  return {
    profile,
    studentName,
    loading,
    error,
    refresh: loadData,
  }
}
