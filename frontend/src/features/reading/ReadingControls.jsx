/**
 * frontend/src/features/reading/ReadingControls.jsx
 *
 * Floating / expandable controls toolbar for dyslexia ergonomics:
 * - Display modes: Standard, Focus, Guided, Listen
 * - Typography: Font family, text size, letter spacing, line height
 * - Layout: Reading column width & warm eye-comfort background colors
 */
import { useState } from 'react'

const MODES = [
  { id: 'standard', label: 'Standard', icon: '📖', desc: 'Full passage reading' },
  { id: 'focus', label: 'Focus Mode', icon: '🔍', desc: 'One chunk at a time' },
  { id: 'guided', label: 'Guided Line', icon: '🎯', desc: 'Sentence highlighter' },
  { id: 'listen', label: 'Listen Aloud', icon: '🔊', desc: 'Read aloud with audio' },
  { id: 'speech', label: 'Read Aloud', icon: '🎤', desc: 'Practice reading with voice' },
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
  speechSupported = true,
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-3.5 sm:p-4 mb-6">
      {/* Top Row: Mode Buttons & Settings Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Mode Selector */}
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {MODES.map((m) => {
            const isSelected = readingMode === m.id
            if (m.id === 'listen' && !ttsSupported) return null
            if (m.id === 'speech' && !speechSupported) return null
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setReadingMode(m.id)}
                className={`px-3 sm:px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-1.5 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
                  isSelected
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
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
          type="button"
          onClick={() => setExpanded(!expanded)}
          className={`px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 border transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
            expanded
              ? 'bg-amber-100 text-amber-950 border-amber-300'
              : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
          }`}
        >
          <span>⚙️</span>
          <span>{expanded ? 'Hide Tools' : 'Text & Spacing'}</span>
        </button>
      </div>

      {/* Expandable Ergonomics Panel */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Font Family */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700 block">Font</label>
            <select
              value={font}
              onChange={(e) => setFont(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:border-indigo-600"
            >
              {FONTS.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          </div>

          {/* Font Size */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-slate-700">
              <span>Text Size</span>
              <span className="text-indigo-600">{fontSize}px</span>
            </div>
            <input
              type="range"
              min="16"
              max="30"
              step="2"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
          </div>

          {/* Line Height */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-slate-700">
              <span>Line Spacing</span>
              <span className="text-indigo-600">{lineSpacing.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="1.4"
              max="2.6"
              step="0.2"
              value={lineSpacing}
              onChange={(e) => setLineSpacing(Number(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
          </div>

          {/* Background Theme */}
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700 block">Page Tint</label>
            <div className="flex items-center gap-2">
              {BG_THEMES.map((theme) => (
                <button
                  key={theme.id}
                  type="button"
                  onClick={() => setBgColor(theme.hex)}
                  className={`w-7 h-7 rounded-full border-2 transition-all cursor-pointer ${
                    bgColor === theme.hex ? 'border-indigo-600 scale-110 shadow-xs' : 'border-slate-300'
                  }`}
                  style={{ backgroundColor: theme.hex }}
                  title={theme.label}
                  aria-label={theme.label}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
