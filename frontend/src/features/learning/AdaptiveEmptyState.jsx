/**
 * frontend/src/features/learning/AdaptiveEmptyState.jsx — Empty & Pending State.
 * Shown when screening is incomplete or when initial calibration is pending.
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button } from '../../components/ui'

export default function AdaptiveEmptyState({
  hasScreening = false,
  message,
}) {
  const navigate = useNavigate()

  return (
    <Card className="text-center py-12 max-w-xl mx-auto my-6 border-2 border-dashed border-[#1A6B6B]/30">
      <div className="w-16 h-16 bg-[#F0F8FF] text-[#1A6B6B] rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
        🎯
      </div>
      <h2 className="dyslexia-text font-bold text-xl text-[#1A2A2A] mb-2">
        {hasScreening
          ? 'Calibrating Your Adaptive Tasks'
          : 'Ready to Discover Your Learning Level?'}
      </h2>
      <p className="dyslexia-text text-sm text-gray-600 mb-6 max-w-md mx-auto leading-relaxed">
        {message ||
          (hasScreening
            ? "We're synthesizing your micro-task recommendations based on your latest reading check."
            : 'Complete your quick reading screening check so the Adaptive Engine can match activities to your unique superpowers!')}
      </p>

      {!hasScreening && (
        <Button
          onClick={() => navigate('/student/screening')}
          className="px-6 py-2.5 font-bold shadow-md bg-[#1A6B6B] text-white hover:bg-[#155555]"
        >
          Take Reading Screening →
        </Button>
      )}
    </Card>
  )
}
