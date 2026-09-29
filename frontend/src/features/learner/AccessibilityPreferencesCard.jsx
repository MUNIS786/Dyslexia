/**
 * frontend/src/features/learner/AccessibilityPreferencesCard.jsx
 * Allows learners to view and refine assistive reading ergonomics.
 */
import React, { useState } from 'react'

const FONTS = [
  { id: 'OpenDyslexic', name: 'OpenDyslexic (Dyslexia-Friendly)' },
  { id: 'Lexend', name: 'Lexend (High Readability)' },
  { id: 'Arial', name: 'Arial (Clean Sans)' },
]

const BG_COLORS = [
  { id: '#FFF8F0', name: 'Warm Cream', hex: '#FFF8F0' },
  { id: '#FFFFFF', name: 'Clean White', hex: '#FFFFFF' },
  { id: '#F0F9FF', name: 'Soft Sky', hex: '#F0F9FF' },
  { id: '#F5F5DC', name: 'Gentle Beige', hex: '#F5F5DC' },
]

export default function AccessibilityPreferencesCard({
  preferences = {},
  onUpdatePreferences,
}) {
  const [font, setFont] = useState(preferences.font || 'OpenDyslexic')
  const [fontSize, setFontSize] = useState(preferences.font_size || 18)
  const [bgColor, setBgColor] = useState(preferences.bg_color || '#FFF8F0')
  const [ttsSpeed, setTtsSpeed] = useState(preferences.tts_speed || 0.85)
  const [highlightWords, setHighlightWords] = useState(preferences.highlight_words ?? true)
  const [syllableSplit, setSyllableSplit] = useState(preferences.syllable_split ?? true)

  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const saveSettings = async (overrides = {}) => {
    const payload = {
      font: overrides.font ?? font,
      font_size: overrides.fontSize ?? fontSize,
      bg_color: overrides.bgColor ?? bgColor,
      tts_speed: overrides.ttsSpeed ?? ttsSpeed,
      highlight_words: overrides.highlightWords ?? highlightWords,
      syllable_split: overrides.syllableSplit ?? syllableSplit,
    }

    if (onUpdatePreferences) {
      setSaving(true)
      try {
        await onUpdatePreferences({ accessibility_preferences: payload })
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      } catch {
        // Handle error silently or toast
      } finally {
        setSaving(false)
      }
    }
  }

  return (
    <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-7 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2 dyslexia-text">
            <span>👓</span> READING & ACCESSIBILITY SETTINGS
          </h3>
          <p className="text-xs text-gray-500">
            Customize letters, size, and colors to make text feel effortless on your eyes
          </p>
        </div>

        {saved && (
          <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
            ✓ Updated!
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Font Family */}
        <div className="space-y-1.5">
          <label htmlFor="pref-font" className="text-xs font-bold text-gray-700 block">
            Reading Font
          </label>
          <select
            id="pref-font"
            value={font}
            onChange={(e) => {
              setFont(e.target.value)
              saveSettings({ font: e.target.value })
            }}
            className="w-full px-3.5 py-2.5 rounded-xl border border-gray-300 bg-white text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-teal-500 font-medium"
          >
            {FONTS.map((f) => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
        </div>

        {/* Font Size */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-bold text-gray-700">
            <label htmlFor="pref-font-size">Text Size</label>
            <span className="text-teal-700 font-bold">{fontSize}px</span>
          </div>
          <input
            id="pref-font-size"
            type="range"
            min="14"
            max="26"
            step="1"
            value={fontSize}
            onChange={(e) => {
              const val = Number(e.target.value)
              setFontSize(val)
              saveSettings({ fontSize: val })
            }}
            className="w-full accent-[#1A6B6B] cursor-pointer"
          />
        </div>

        {/* Speech Speed */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-bold text-gray-700">
            <label htmlFor="pref-tts-speed">Read-Aloud Voice Speed</label>
            <span className="text-teal-700 font-bold">{ttsSpeed}x</span>
          </div>
          <input
            id="pref-tts-speed"
            type="range"
            min="0.5"
            max="1.2"
            step="0.05"
            value={ttsSpeed}
            onChange={(e) => {
              const val = Number(e.target.value)
              setTtsSpeed(val)
              saveSettings({ ttsSpeed: val })
            }}
            className="w-full accent-[#1A6B6B] cursor-pointer"
          />
        </div>

        {/* Background Tint */}
        <div className="space-y-1.5 md:col-span-2 lg:col-span-1">
          <span className="text-xs font-bold text-gray-700 block">Page Tint (Reduces Glare)</span>
          <div className="flex items-center gap-2">
            {BG_COLORS.map((bg) => (
              <button
                key={bg.id}
                type="button"
                onClick={() => {
                  setBgColor(bg.id)
                  saveSettings({ bgColor: bg.id })
                }}
                title={bg.name}
                aria-label={`Select ${bg.name} background`}
                className={`w-8 h-8 rounded-full border-2 transition-all ${
                  bgColor === bg.id ? 'border-[#1A6B6B] scale-110 shadow-md ring-2 ring-teal-200' : 'border-gray-300'
                }`}
                style={{ backgroundColor: bg.hex }}
              />
            ))}
          </div>
        </div>

        {/* Word Highlighting Toggle */}
        <div className="flex items-center justify-between p-3 rounded-2xl bg-gray-50 border border-gray-200">
          <div>
            <p className="text-xs font-bold text-gray-900">Word-by-Word Highlight</p>
            <p className="text-[11px] text-gray-500">Lights up words as you read</p>
          </div>
          <input
            type="checkbox"
            checked={highlightWords}
            onChange={(e) => {
              setHighlightWords(e.target.checked)
              saveSettings({ highlightWords: e.target.checked })
            }}
            className="w-5 h-5 rounded text-[#1A6B6B] accent-[#1A6B6B] cursor-pointer"
          />
        </div>

        {/* Syllable Split Toggle */}
        <div className="flex items-center justify-between p-3 rounded-2xl bg-gray-50 border border-gray-200">
          <div>
            <p className="text-xs font-bold text-gray-900">Syllable Splitting</p>
            <p className="text-[11px] text-gray-500">Breaks tricky words into beats</p>
          </div>
          <input
            type="checkbox"
            checked={syllableSplit}
            onChange={(e) => {
              setSyllableSplit(e.target.checked)
              saveSettings({ syllableSplit: e.target.checked })
            }}
            className="w-5 h-5 rounded text-[#1A6B6B] accent-[#1A6B6B] cursor-pointer"
          />
        </div>
      </div>
    </div>
  )
}
