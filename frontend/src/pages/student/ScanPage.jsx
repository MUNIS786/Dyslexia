import { useState, useRef } from 'react'
import { scanAPI, libraryAPI, progressAPI } from '../../api/client'
import { useTTS } from '../../hooks/useTTS'
import {
  Card, Button, Select, PageHeader, ReadingText, TTSButton, Badge, Spinner, Alert, Textarea
} from '../../components/ui'
import toast from 'react-hot-toast'

const LANGUAGES = [
  { value: 'en', label: '🇬🇧 English' },
  { value: 'hi', label: '🇮🇳 Hindi' },
  { value: 'ta', label: '🇮🇳 Tamil' },
  { value: 'mr', label: '🇮🇳 Marathi' },
]
const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

export default function ScanPage() {
  const [mode, setMode] = useState('upload') // upload | paste | notes
  const [language, setLanguage] = useState('en')
  const [file, setFile] = useState(null)
  const [pasteText, setPasteText] = useState('')
  const [notesTitle, setNotesTitle] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState('simplified') // simplified | original | bullets
  const [speed, setSpeed] = useState(1)
  const [saving, setSaving] = useState(false)
  const fileRef = useRef(null)
  const { speak, stop, toggle, speaking, wordIndex, words } = useTTS()

  const getDisplayText = () => {
    if (!result) return ''
    if (viewMode === 'original') return result.original || result.text || ''
    return result.simplified || result.text || ''
  }

  const handleScan = async () => {
    if (!file) { toast.error('Please select a file first.'); return }
    setLoading(true)
    stop()
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('language', language)
      const scanned = await scanAPI.scan(fd)
      // Auto simplify
      const simplified = await scanAPI.simplify({ text: scanned.text, language })
      setResult({ ...simplified, wordCount: scanned.wordCount, title: file.name })
      setViewMode('simplified')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not scan file.')
    } finally {
      setLoading(false)
    }
  }

  const handleSimplify = async () => {
    if (!pasteText.trim()) { toast.error('Please paste some text first.'); return }
    setLoading(true)
    stop()
    try {
      const res = await scanAPI.simplify({ text: pasteText, language })
      setResult({ ...res, wordCount: pasteText.split(/\s+/).length, title: 'Pasted text' })
      setViewMode('simplified')
    } catch {
      toast.error('Could not simplify text.')
    } finally {
      setLoading(false)
    }
  }

  const handleConvertNotes = async () => {
    if (!pasteText.trim()) { toast.error('Please paste notes first.'); return }
    setLoading(true)
    stop()
    try {
      const res = await scanAPI.convertNotes({ text: pasteText, language, title: notesTitle || 'My Notes' })
      setResult({ ...res, wordCount: pasteText.split(/\s+/).length, title: notesTitle || 'My Notes' })
      setViewMode('simplified')
    } catch {
      toast.error('Could not convert notes.')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!result) return
    setSaving(true)
    try {
      await libraryAPI.save({
        title: result.title || 'Untitled',
        language,
        original: result.original || result.text || '',
        simplified: result.simplified || '',
        bullet_points: result.bullet_points || [],
        highlights: result.highlights || [],
        source: mode,
      })
      await progressAPI.scan({ wordCount: result.wordCount || 0, title: result.title || 'Untitled' })
      toast.success('✅ Saved to your library!')
    } catch {
      toast.error('Could not save to library.')
    } finally {
      setSaving(false)
    }
  }

  const displayText = getDisplayText()

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon="📷" title="Scan & Simplify" subtitle="Upload a file or paste text. We will make it easy to read." />

      {/* Mode tabs */}
      <div className="flex gap-2 bg-white rounded-xl p-1 border border-[#E5E0D8]">
        {[
          { id: 'upload', label: '📁 Upload File' },
          { id: 'paste', label: '✏️ Paste Text' },
          { id: 'notes', label: '📓 Notes Converter' },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => { setMode(m.id); setResult(null); stop() }}
            className={`flex-1 py-2.5 rounded-lg dyslexia-text text-sm font-semibold transition-all
              ${mode === m.id ? 'bg-[#1A6B6B] text-white' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Controls */}
      <Card>
        <Select
          label="🌐 Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          options={LANGUAGES}
          className="mb-4"
        />

        {mode === 'upload' && (
          <div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx"
              onChange={(e) => setFile(e.target.files[0])}
              className="hidden"
            />
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-[#1A6B6B] rounded-xl p-8 text-center cursor-pointer
                hover:bg-[#E0F2F2] transition-colors"
            >
              <p className="text-4xl mb-2">📤</p>
              <p className="dyslexia-text font-semibold text-[#1A6B6B]">
                {file ? file.name : 'Click to choose a file'}
              </p>
              <p className="dyslexia-text text-sm text-gray-500 mt-1">
                PDF, image, Word, or text file
              </p>
            </div>
            <Button
              className="w-full mt-3"
              onClick={handleScan}
              loading={loading}
              disabled={!file}
            >
              📷 Scan & Simplify
            </Button>
          </div>
        )}

        {(mode === 'paste' || mode === 'notes') && (
          <div className="flex flex-col gap-3">
            {mode === 'notes' && (
              <input
                className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                  focus:outline-none focus:border-[#1A6B6B]"
                placeholder="Notes title (optional)"
                value={notesTitle}
                onChange={(e) => setNotesTitle(e.target.value)}
              />
            )}
            <Textarea
              label={mode === 'notes' ? '📓 Paste your notes' : '✏️ Paste your text'}
              rows={6}
              placeholder="Paste text here…"
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
            />
            {mode === 'notes' && (
              <Badge color="green" className="self-start">✅ Works Offline</Badge>
            )}
            <Button
              onClick={mode === 'notes' ? handleConvertNotes : handleSimplify}
              loading={loading}
            >
              {mode === 'notes' ? '📓 Convert Notes' : '✨ Simplify Text'}
            </Button>
          </div>
        )}
      </Card>

      {/* Result */}
      {loading && (
        <div className="flex flex-col items-center py-10 gap-3">
          <Spinner size="lg" />
          <p className="dyslexia-text text-[#1A6B6B]">Processing your text…</p>
        </div>
      )}

      {result && !loading && (
        <Card>
          {/* View toggle */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {['simplified', 'original', 'bullets'].map((v) => (
              <button
                key={v}
                onClick={() => { setViewMode(v); stop() }}
                className={`px-3 py-1.5 rounded-lg dyslexia-text text-sm font-semibold capitalize transition-all
                  ${viewMode === v ? 'bg-[#1A6B6B] text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
              >
                {v === 'simplified' ? '✨ Simplified' : v === 'original' ? '📄 Original' : '• Bullets'}
              </button>
            ))}
          </div>

          {/* TTS controls */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <TTSButton
              text={displayText}
              speed={speed}
              speaking={speaking}
              onToggle={toggle}
            />
            <select
              value={speed}
              onChange={(e) => { setSpeed(parseFloat(e.target.value)); stop() }}
              className="px-3 py-2 rounded-lg border border-[#E5E0D8] dyslexia-text text-sm"
            >
              {SPEEDS.map((s) => (
                <option key={s} value={s}>{s}x</option>
              ))}
            </select>
          </div>

          {/* Content */}
          <div className="bg-[#FFF8F0] rounded-xl p-4" style={{ lineHeight: 'var(--line-spacing)' }}>
            {viewMode === 'bullets' ? (
              <ol className="flex flex-col gap-2">
                {(result.bullet_points || []).map((bp, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="font-bold text-[#1A6B6B] shrink-0">{i + 1}.</span>
                    <ReadingText
                      text={bp}
                      highlights={result.highlights || []}
                      wordIndex={speaking ? wordIndex : -1}
                    />
                  </li>
                ))}
              </ol>
            ) : (
              <ReadingText
                text={displayText}
                highlights={result.highlights || []}
                wordIndex={speaking ? wordIndex : -1}
              />
            )}
          </div>

          {/* Save button */}
          <Button
            className="w-full mt-4"
            variant="secondary"
            onClick={handleSave}
            loading={saving}
          >
            📚 Save to Library
          </Button>
        </Card>
      )}
    </div>
  )
}
