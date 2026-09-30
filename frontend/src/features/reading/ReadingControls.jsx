/**
 * frontend/src/features/reading/ReadingControls.jsx
 *
 * Floating / expandable controls toolbar for dyslexia ergonomics:
 * - Display modes: Standard, Focus, Guided, Listen
 * - Typography: Font family, text size, letter spacing, line height
 * - Layout: Reading column width & warm eye-comfort background colors
 */
import React, { useState } from 'react'

const MODES = [
  { id: 'standard', label: 'Standard', icon: '📖', desc: 'Full passage reading' },
  { id: 'focus', label: 'Focus Mode', icon: '🔍', desc: 'One chunk at a time' },
  { id: 'guided', label: 'Guided Line', icon: '🎯', desc: 'Sentence highlighter' },
  { id: 'listen', label: 'Listen Aloud', icon: '🔊', desc: 'Read aloud with audio' },
]

const FONTS = [
  { id: 'OpenDyslexic', name: 'OpenDyslexic' },
  { id: 'Lexend', name: 'Lexend' },
  { id: 'Arial', name: 'Arial (Clean)' },
]

const BG_THEMES = [
  { id: '#FFF8F0', label: 'Warm Cream', hex: '#FFF8F0' },
  { id: '#FFFFFF', label: 'White', hex: '#FFFFFF' },
  { id: '#F0F9FF', label: 'Soft Sky', hex: '#F0F9FF' },
  { id: '#F5F5DC', label: 'Gentle Beige', hex: '#F5F5DC' },
]

export default function ReadingControls({
  readingMode,
  setReadingMode,
  font,
  setFont,
  fontSize,
  setFontSize,
  lineSpacing,
  setLineSpacing,
  letterSpacing,
  setLetterSpacing,
  readingWidth,
  setReadingWidth,
  bgColor,
  setBgColor,
  ttsSupported = true,
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-3xl border border-stone-200 shadow-sm p-4 mb-6">
      {/* Top Row: Mode Buttons & Settings Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Mode Selector */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {MODES.map((m) => {
            const isSelected = readingMode === m.id
            if (m.id === 'listen' && !ttsSupported) return null
            return (
              <button
                key={m.id}
                onClick={() => setReadingMode(m.id)}
                className={`px-3 sm:px-4 py-2 rounded-2xl text-xs sm:text-sm font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#1A6B6B] text-white shadow-sm'
                    : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                }`}
                title={m.desc}
              >
                <span>{m.icon}</span>
                <span>{m.label}</span>
              </button>
            )
          })}
        </div>

        {/* Toggle Ergonomics Toolbar */}
        <button
          onClick={() => setExpanded(!expanded)}
          className={`px-3 py-2 rounded-2xl text-xs font-bold flex items-center gap-1.5 border transition-all cursor-pointer ${
            expanded
              ? 'bg-amber-100 text-amber-900 border-amber-300'
              : 'bg-stone-50 text-stone-600 border-stone-200 hover:bg-stone-100'
          }`}
        >
          <span>⚙️</span>
          <span>{expanded ? 'Hide Settings' : 'Text & Spacing'}</span>
        </button>
      </div>

      {/* Expandable Ergonomics Panel */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-stone-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Font Family */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-stone-600 block">Font</label>
            <select
              value={font}
              onChange={(e) => setFont(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-stone-300 text-xs font-medium text-stone-800 bg-white"
            >
              {FONTS.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>

          {/* Font Size */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-stone-600">
              <span>Text Size</span>
              <span className="text-teal-700">{fontSize}px</span>
            </div>
            <input
              type="range"
              min="16"
              max="30"
              step="2"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
          </div>

          {/* Line Height */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-stone-600">
              <span>Line Spacing</span>
              <span className="text-teal-700">{lineSpacing.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="1.4"
              max="2.6"
              step="0.2"
              value={lineSpacing}
              onChange={(e) => setLineSpacing(Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer"
            />
          </div>

          {/* Background Theme */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-stone-600 block">Page Tint</label>
            <div className="flex items-center gap-2">
              {BG_THEMES.map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => setBgColor(theme.hex)}
                  className={`w-7 h-7 rounded-full border-2 transition-all cursor-pointer ${
                    bgColor === theme.hex ? 'border-teal-600 scale-110' : 'border-stone-300'
                  }`}
                  style={{ backgroundColor: theme.hex }}
                  title={theme.label}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
