/**
 * frontend/src/features/learner/ProfileConfidenceCard.jsx
 * Displays profile confidence and metadata with educational transparency.
 */
import React from 'react'

export default function ProfileConfidenceCard({
  confidence = {},
  metadata = {},
}) {
  const overall = Math.round((confidence.overall || 0) * 100)
  const screening = Math.round((confidence.screening || 0) * 100)
  const performance = Math.round((confidence.performance || 0) * 100)

  return (
    <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-7 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2 dyslexia-text">
            <span>ℹ️</span> PROFILE INFORMATION & CONFIDENCE
          </h3>
          <p className="text-xs text-gray-500">
            Your profile updates as you complete screenings and practice reading
          </p>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-bold bg-teal-50 text-teal-800 border border-teal-200">
          Data Calibration: {overall}%
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500">Overall Confidence</p>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-xl font-black text-gray-900">{overall}%</span>
            <span className="text-[11px] text-teal-700 font-bold">
              {overall > 70 ? 'High Fidelity' : 'Growing Evidence'}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-[#1A6B6B] h-full rounded-full" style={{ width: `${overall}%` }} />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500">Screening Battery Evidence</p>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-xl font-black text-gray-900">{screening}%</span>
            <span className="text-[11px] text-gray-600">
              {confidence.screening_questions_answered || 20} Questions
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-teal-500 h-full rounded-full" style={{ width: `${screening}%` }} />
          </div>
        </div>

        <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-100">
          <p className="text-xs font-semibold text-gray-500">Daily Reading Telemetry</p>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-xl font-black text-gray-900">{performance}%</span>
            <span className="text-[11px] text-gray-600">Active Sessions</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
            <div className="bg-[#E8A020] h-full rounded-full" style={{ width: `${performance}%` }} />
          </div>
        </div>
      </div>

      <div className="text-xs text-gray-500 leading-relaxed pt-2 border-t border-gray-100 flex flex-wrap justify-between items-center gap-2">
        <span>
          Profile Engine: V{metadata.profile_version || 2}.0 &bull; Primary Source: {metadata.source || 'screening'}
        </span>
        <span className="text-gray-400">
          Last Synced: {new Date((metadata.updated_at || Date.now() / 1000) * 1000).toLocaleDateString('en-IN')}
        </span>
      </div>
    </div>
  )
}
