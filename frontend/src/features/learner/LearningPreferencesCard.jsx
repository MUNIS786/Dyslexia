/**
 * frontend/src/features/learner/LearningPreferencesCard.jsx
 * Interactive card allowing student to select preferred learning modes.
 */
import React, { useState } from 'react'

const MODES = [
  { id: 'Reading', label: 'Reading', icon: '📖', desc: 'Enjoying stories & clear printed text' },
  { id: 'Listening', label: 'Listening', icon: '🔊', desc: 'Audio accompaniment & read-aloud TTS' },
  { id: 'Visual', label: 'Visual', icon: '👀', desc: 'Pictures, colored word shapes & diagrams' },
  { id: 'Interactive', label: 'Interactive', icon: '🎮', desc: 'Games, sound blending & quick quizzes' },
]

export default function LearningPreferencesCard({
  learningModes = ['Reading', 'Visual', 'Interactive'],
  onUpdatePreferences,
}) {
  const [selectedModes, setSelectedModes] = useState(learningModes)
  const [saving, setSaving] = useState(false)
  const [savedMessage, setSavedMessage] = useState(false)

  const handleToggle = async (modeId) => {
    let next
    if (selectedModes.includes(modeId)) {
      if (selectedModes.length === 1) return // Keep at least one selected
      next = selectedModes.filter((m) => m !== modeId)
    } else {
      next = [...selectedModes, modeId]
    }
    setSelectedModes(next)

    if (onUpdatePreferences) {
      setSaving(true)
      try {
        await onUpdatePreferences({ preferred_learning_modes: next })
        setSavedMessage(true)
        setTimeout(() => setSavedMessage(false), 2000)
      } catch {
        // revert on error
        setSelectedModes(selectedModes)
      } finally {
        setSaving(false)
      }
    }
  }

  return (
    <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-7 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2 dyslexia-text">
            <span>✨</span> HOW YOU LIKE TO LEARN
          </h3>
          <p className="text-xs text-gray-500">
            Pick the learning styles that help you understand and enjoy reading most
          </p>
        </div>

        {savedMessage && (
          <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 animate-fade-in">
            ✓ Saved!
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {MODES.map((mode) => {
          const isSelected = selectedModes.includes(mode.id)
          return (
            <button
              key={mode.id}
              onClick={() => handleToggle(mode.id)}
              disabled={saving}
              aria-pressed={isSelected}
              className={`p-4 rounded-2xl border text-left transition-all duration-200 flex flex-col justify-between gap-3 focus:outline-none focus:ring-2 focus:ring-teal-500 ${
                isSelected
                  ? 'bg-teal-50/80 border-[#1A6B6B] shadow-sm ring-1 ring-[#1A6B6B]'
                  : 'bg-gray-50/70 border-gray-200 hover:bg-gray-100/80 text-gray-700'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="text-2xl select-none" aria-hidden="true">{mode.icon}</span>
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                    isSelected ? 'bg-[#1A6B6B] text-white' : 'border border-gray-300'
                  }`}
                >
                  {isSelected ? '✓' : ''}
                </span>
              </div>

              <div>
                <p className={`font-bold text-sm dyslexia-text ${isSelected ? 'text-teal-950' : 'text-gray-900'}`}>
                  {mode.label}
                </p>
                <p className="text-xs text-gray-500 mt-0.5 leading-snug">
                  {mode.desc}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
