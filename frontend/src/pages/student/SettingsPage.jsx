import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { classroomAPI } from '../../api/client'
import { Card, Button, Select, PageHeader, Badge } from '../../components/ui'
import toast from 'react-hot-toast'

const FONTS = [
  { value: 'Lexend, sans-serif', label: 'Lexend (Recommended)' },
  { value: 'OpenDyslexic, sans-serif', label: 'OpenDyslexic' },
  { value: 'Arial, sans-serif', label: 'Arial' },
]
const BG_COLORS = [
  { value: '#FFF8F0', label: 'Cream (Recommended)' },
  { value: '#FFFFFF', label: 'White' },
  { value: '#FFFDE0', label: 'Light Yellow' },
  { value: '#E8F4F8', label: 'Light Blue' },
]
const TEXT_COLORS = [
  { value: '#1A2A2A', label: 'Dark (Recommended)' },
  { value: '#000000', label: 'Black' },
  { value: '#1A2060', label: 'Dark Blue' },
]
const TTS_SPEEDS = [
  { value: '0.5', label: '0.5x (Slowest)' },
  { value: '0.75', label: '0.75x (Slow)' },
  { value: '1', label: '1x (Normal)' },
  { value: '1.25', label: '1.25x (Fast)' },
  { value: '1.5', label: '1.5x (Faster)' },
  { value: '2', label: '2x (Fastest)' },
]
const TTS_LANGUAGES = [
  { value: 'en-IN', label: '🇬🇧 English (India)' },
  { value: 'hi-IN', label: '🇮🇳 Hindi' },
  { value: 'ta-IN', label: '🇮🇳 Tamil' },
  { value: 'mr-IN', label: '🇮🇳 Marathi' },
]

export default function SettingsPage() {
  const { user, updateSettings } = useAuth()
  const navigate = useNavigate()
  const s = user?.settings || {}

  const [local, setLocal] = useState({
    font: s.font || 'Lexend, sans-serif',
    fontSize: s.fontSize || 18,
    lineSpacing: s.lineSpacing || 2,
    letterSpacing: s.letterSpacing || 0.05,
    bgColor: s.bgColor || '#FFF8F0',
    textColor: s.textColor || '#1A2A2A',
    ttsSpeed: s.ttsSpeed || 1,
    ttsLanguage: s.ttsLanguage || 'en-IN',
    highlightWords: s.highlightWords ?? true,
    showBulletPoints: s.showBulletPoints ?? true,
    autoSimplify: s.autoSimplify ?? true,
  })
  const [saving, setSaving] = useState(false)
  const [classCode, setClassCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [classroom, setClassroom] = useState(null)

  // Live preview: apply changes to CSS variables immediately
  const set = (key, val) => {
    setLocal((prev) => {
      const next = { ...prev, [key]: val }
      // Apply live preview
      const root = document.documentElement
      if (key === 'font') root.style.setProperty('--font-family', val)
      if (key === 'fontSize') root.style.setProperty('--font-size', `${val}px`)
      if (key === 'lineSpacing') root.style.setProperty('--line-spacing', val)
      if (key === 'letterSpacing') root.style.setProperty('--letter-spacing', `${val}em`)
      if (key === 'bgColor') { root.style.setProperty('--bg-color', val); document.body.style.backgroundColor = val }
      if (key === 'textColor') { root.style.setProperty('--text-color', val); document.body.style.color = val }
      return next
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateSettings(local)
      toast.success('✅ Settings saved!')
    } catch {
      toast.error('Could not save settings.')
    } finally {
      setSaving(false)
    }
  }

  const handleJoinClassroom = async () => {
    if (!classCode.trim()) return
    setJoining(true)
    try {
      const res = await classroomAPI.join(classCode.trim())
      setClassroom(res)
      toast.success(`✅ Joined ${res.teacherName}'s classroom!`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid classroom code.')
    } finally {
      setJoining(false)
    }
  }

  const handleLeave = async () => {
    if (!confirm('Leave this classroom?')) return
    await classroomAPI.leave()
    setClassroom(null)
    toast.success('Left classroom.')
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader icon="⚙️" title="Settings" subtitle="Customize how text looks and sounds." />

      {/* Font */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">🔤 Text Appearance</h2>

        <div className="flex flex-col gap-4">
          <Select
            label="Font Family"
            value={local.font}
            onChange={(e) => set('font', e.target.value)}
            options={FONTS}
          />

          <div>
            <label className="dyslexia-text font-semibold block mb-1">
              Font Size: {local.fontSize}px
            </label>
            <input
              type="range"
              min={14}
              max={28}
              step={1}
              value={local.fontSize}
              onChange={(e) => set('fontSize', parseInt(e.target.value))}
              className="w-full accent-[#1A6B6B]"
            />
            <div className="flex justify-between text-xs text-gray-400 dyslexia-text">
              <span>14px (Small)</span><span>28px (Large)</span>
            </div>
          </div>

          <div>
            <label className="dyslexia-text font-semibold block mb-1">
              Line Spacing: {local.lineSpacing}
            </label>
            <input
              type="range"
              min={1.5}
              max={3.0}
              step={0.1}
              value={local.lineSpacing}
              onChange={(e) => set('lineSpacing', parseFloat(e.target.value))}
              className="w-full accent-[#1A6B6B]"
            />
            <div className="flex justify-between text-xs text-gray-400 dyslexia-text">
              <span>1.5 (Compact)</span><span>3.0 (Spacious)</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Colors */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">🎨 Colors</h2>

        <div className="mb-4">
          <p className="dyslexia-text font-semibold mb-2">Background Color</p>
          <div className="flex gap-3 flex-wrap">
            {BG_COLORS.map((c) => (
              <button
                key={c.value}
                onClick={() => set('bgColor', c.value)}
                className={`w-10 h-10 rounded-xl border-2 transition-all
                  ${local.bgColor === c.value ? 'border-[#1A6B6B] scale-110 shadow-md' : 'border-[#E5E0D8]'}`}
                style={{ backgroundColor: c.value }}
                title={c.label}
              />
            ))}
          </div>
        </div>

        <div>
          <p className="dyslexia-text font-semibold mb-2">Text Color</p>
          <div className="flex gap-3 flex-wrap">
            {TEXT_COLORS.map((c) => (
              <button
                key={c.value}
                onClick={() => set('textColor', c.value)}
                className={`w-10 h-10 rounded-xl border-2 transition-all
                  ${local.textColor === c.value ? 'border-[#E8A020] scale-110 shadow-md' : 'border-[#E5E0D8]'}`}
                style={{ backgroundColor: c.value }}
                title={c.label}
              />
            ))}
          </div>
        </div>
      </Card>

      {/* Live preview */}
      <Card className="border-2 border-[#1A6B6B]">
        <h2 className="dyslexia-text font-bold text-base mb-3 text-[#1A6B6B]">👁 Live Preview</h2>
        <div
          className="rounded-xl p-4"
          style={{
            backgroundColor: local.bgColor,
            color: local.textColor,
            fontFamily: local.font,
            fontSize: `${local.fontSize}px`,
            lineHeight: local.lineSpacing,
            letterSpacing: `${local.letterSpacing}em`,
          }}
        >
          The quick brown fox jumps over the lazy dog. Reading is a superpower and you are getting better every day!
          <span className="bg-amber-300 rounded px-0.5"> Highlighted word </span> looks like this.
        </div>
      </Card>

      {/* TTS */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">🔊 Text-to-Speech</h2>
        <div className="flex flex-col gap-4">
          <Select
            label="Speaking Speed"
            value={String(local.ttsSpeed)}
            onChange={(e) => set('ttsSpeed', parseFloat(e.target.value))}
            options={TTS_SPEEDS}
          />
          <Select
            label="Language"
            value={local.ttsLanguage}
            onChange={(e) => set('ttsLanguage', e.target.value)}
            options={TTS_LANGUAGES}
          />
        </div>
      </Card>

      {/* Toggles */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">🎛️ Features</h2>
        <div className="flex flex-col gap-4">
          {[
            { key: 'highlightWords', label: 'Highlight important words', icon: '✨' },
            { key: 'showBulletPoints', label: 'Show bullet point summaries', icon: '•' },
            { key: 'autoSimplify', label: 'Auto-simplify on scan', icon: '🤖' },
          ].map((opt) => (
            <div key={opt.key} className="flex items-center justify-between">
              <p className="dyslexia-text font-medium">
                {opt.icon} {opt.label}
              </p>
              <button
                onClick={() => set(opt.key, !local[opt.key])}
                className={`w-14 h-7 rounded-full transition-all relative
                  ${local[opt.key] ? 'bg-[#1A6B6B]' : 'bg-gray-300'}`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all
                    ${local[opt.key] ? 'left-8' : 'left-1'}`}
                />
              </button>
            </div>
          ))}
        </div>
      </Card>

      {/* Classroom */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">🏫 Classroom</h2>
        {classroom ? (
          <div className="flex flex-col gap-3">
            <div className="bg-green-50 rounded-xl p-3">
              <p className="dyslexia-text font-semibold text-green-700">✅ Joined!</p>
              <p className="dyslexia-text text-sm">Teacher: {classroom.teacherName}</p>
              {classroom.classroomCode && (
                <p className="dyslexia-text text-sm">Code: <span className="font-mono font-bold">{classroom.classroomCode}</span></p>
              )}
            </div>
            <Button variant="danger" size="sm" onClick={handleLeave}>Leave Classroom</Button>
          </div>
        ) : (
          <div className="flex gap-3">
            <input
              className="flex-1 px-4 py-3 rounded-xl border-2 border-[#E5E0D8] dyslexia-text
                focus:outline-none focus:border-[#1A6B6B]"
              placeholder="Enter classroom code"
              value={classCode}
              onChange={(e) => setClassCode(e.target.value.toUpperCase())}
            />
            <Button onClick={handleJoinClassroom} loading={joining} disabled={!classCode.trim()}>
              Join
            </Button>
          </div>
        )}
      </Card>

      <Button size="lg" className="w-full" onClick={handleSave} loading={saving}>
        💾 Save Settings
      </Button>
    </div>
  )
}
