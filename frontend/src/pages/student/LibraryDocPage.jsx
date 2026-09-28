import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { libraryAPI, progressAPI } from '../../api/client'
import { useTTS } from '../../hooks/useTTS'
import {
  Card, Button, Badge, PageHeader, ReadingText, TTSButton, Modal, Spinner
} from '../../components/ui'
import toast from 'react-hot-toast'

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2]

export default function LibraryDocPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [doc, setDoc] = useState(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('simplified')
  const [speed, setSpeed] = useState(1)
  const [wordModal, setWordModal] = useState(null)
  const [mastering, setMastering] = useState(false)
  const { speak, stop, toggle, speaking, wordIndex, words } = useTTS()

  useEffect(() => {
    libraryAPI.get(id).then(setDoc).catch(() => toast.error('Could not load document.')).finally(() => setLoading(false))
  }, [id])

  const displayText = doc
    ? (viewMode === 'original' ? doc.original : doc.simplified) || doc.original || ''
    : ''

  const handleWordClick = (word) => {
    const clean = word.replace(/[^a-zA-Z]/g, '')
    if (clean) setWordModal(clean)
  }

  const handleMasterWord = async () => {
    if (!wordModal) return
    setMastering(true)
    try {
      await progressAPI.word(wordModal)
      toast.success(`⭐ "${wordModal}" added to mastered words!`)
      setWordModal(null)
    } catch {
      toast.error('Could not save word.')
    } finally {
      setMastering(false)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )
  if (!doc) return (
    <div className="text-center py-20">
      <p className="dyslexia-text text-gray-500">Document not found.</p>
      <Button onClick={() => navigate('/student/library')} className="mt-4">← Back to Library</Button>
    </div>
  )

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="📄"
        title={doc.title}
        action={<Button variant="ghost" onClick={() => navigate('/student/library')}>← Library</Button>}
      />

      {/* Meta */}
      <div className="flex flex-wrap gap-2">
        <Badge color="teal">{doc.language?.toUpperCase()}</Badge>
        <Badge color="gray">{doc.wordCount?.toLocaleString()} words</Badge>
      </div>

      {/* View toggle */}
      <div className="flex gap-2">
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

      {/* TTS bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <TTSButton text={displayText} speed={speed} speaking={speaking} onToggle={toggle} />
        <select
          value={speed}
          onChange={(e) => { setSpeed(parseFloat(e.target.value)); stop() }}
          className="px-3 py-2 rounded-lg border border-[#E5E0D8] dyslexia-text text-sm"
        >
          {SPEEDS.map((s) => <option key={s} value={s}>{s}x</option>)}
        </select>
        <Badge color="amber">💡 Tap highlighted words to master them</Badge>
      </div>

      {/* Content */}
      <Card className="bg-[#FFF8F0]">
        {viewMode === 'bullets' ? (
          <ol className="flex flex-col gap-3">
            {(doc.bullet_points || []).map((bp, i) => (
              <li key={i} className="flex gap-3">
                <span className="font-bold text-[#1A6B6B] shrink-0">{i + 1}.</span>
                <ClickableText
                  text={bp}
                  highlights={doc.highlights || []}
                  onWordClick={handleWordClick}
                  wordIndex={speaking ? wordIndex : -1}
                />
              </li>
            ))}
          </ol>
        ) : (
          <ClickableText
            text={displayText}
            highlights={doc.highlights || []}
            onWordClick={handleWordClick}
            wordIndex={speaking ? wordIndex : -1}
          />
        )}
      </Card>

      {/* Word mastery modal */}
      <Modal open={!!wordModal} onClose={() => setWordModal(null)} title="⭐ Master This Word">
        <div className="flex flex-col gap-4">
          <div className="bg-[#FFF3DC] rounded-xl p-4 text-center">
            <p className="dyslexia-text text-3xl font-bold text-[#1A6B6B]">{wordModal}</p>
          </div>
          <p className="dyslexia-text text-sm text-gray-600">
            Add this word to your mastered words list. Your progress will be tracked!
          </p>
          <div className="flex gap-3">
            <Button variant="ghost" onClick={() => setWordModal(null)} className="flex-1">
              Cancel
            </Button>
            <Button onClick={handleMasterWord} loading={mastering} className="flex-1">
              ⭐ Add to Mastered
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function ClickableText({ text, highlights, onWordClick, wordIndex }) {
  if (!text) return null
  const highlightSet = new Set((highlights || []).map((h) => h.toLowerCase()))
  const chunks = text.split(/(\s+)/)
  let wIdx = 0

  return (
    <p
      className="dyslexia-text"
      style={{ lineHeight: 'var(--line-spacing)', letterSpacing: 'var(--letter-spacing)' }}
    >
      {chunks.map((chunk, i) => {
        if (/^\s+$/.test(chunk)) return <span key={i}>{chunk}</span>
        const idx = wIdx++
        const isHighlighted = highlightSet.has(chunk.toLowerCase().replace(/[^a-z]/g, ''))
        const isCurrent = idx === wordIndex
        return (
          <span
            key={i}
            onClick={() => isHighlighted && onWordClick(chunk)}
            className={`${isCurrent ? 'current-word' : isHighlighted ? 'highlight-word cursor-pointer hover:bg-amber-300' : ''}`}
          >
            {chunk}
          </span>
        )
      })}
    </p>
  )
}
