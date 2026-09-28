import { useState, useRef } from 'react'
import { scanAPI, assignmentsAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, ReadingText, Select, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

const LANGUAGES = [
  { value: 'en', label: '🇬🇧 English' },
  { value: 'hi', label: '🇮🇳 Hindi' },
  { value: 'ta', label: '🇮🇳 Tamil' },
  { value: 'mr', label: '🇮🇳 Marathi' },
]

export default function TeacherScanPage() {
  const [file, setFile] = useState(null)
  const [language, setLanguage] = useState('en')
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState(null)
  const [assignForm, setAssignForm] = useState({ title: '', dueInDays: '7', maxScore: '100' })
  const [creating, setCreating] = useState(false)
  const [created, setCreated] = useState(false)
  const fileRef = useRef(null)

  const handleScan = async () => {
    if (!file) { toast.error('Please select a file first.'); return }
    setScanning(true)
    setResult(null)
    setCreated(false)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('language', language)
      const scanned = await scanAPI.scan(fd)
      const simplified = await scanAPI.simplify({ text: scanned.text, language })
      setResult({
        ...simplified,
        wordCount: scanned.wordCount,
        method: scanned.method,
        title: file.name.replace(/\.[^.]+$/, ''),
      })
      setAssignForm((f) => ({ ...f, title: file.name.replace(/\.[^.]+$/, '') }))
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not scan file.')
    } finally {
      setScanning(false)
    }
  }

  const handleCreateAssignment = async () => {
    if (!assignForm.title.trim()) { toast.error('Please enter a title.'); return }
    if (!result) return
    setCreating(true)
    try {
      await assignmentsAPI.create({
        title: assignForm.title,
        description: `Scanned from: ${file?.name}`,
        originalText: result.simplified || result.original || '',
        language,
        dueInDays: parseInt(assignForm.dueInDays),
        maxScore: parseInt(assignForm.maxScore),
      })
      toast.success('✅ Assignment sent to class!')
      setCreated(true)
    } catch {
      toast.error('Could not create assignment.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="📷"
        title="Scan & Convert"
        subtitle="Upload any document. We convert it to dyslexia-friendly format. Then post it to your class."
      />

      {/* Step 1: Upload */}
      <Card>
        <h2 className="dyslexia-text font-bold text-lg mb-4">Step 1: Upload Document</h2>
        <Select
          label="🌐 Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          options={LANGUAGES}
          className="mb-4"
        />
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx"
          onChange={(e) => { setFile(e.target.files[0]); setResult(null); setCreated(false) }}
          className="hidden"
        />
        <div
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-[#1A6B6B] rounded-xl p-8 text-center cursor-pointer hover:bg-[#E0F2F2] transition-colors mb-4"
        >
          <p className="text-4xl mb-2">📤</p>
          <p className="dyslexia-text font-semibold text-[#1A6B6B]">
            {file ? file.name : 'Click to choose a document'}
          </p>
          <p className="dyslexia-text text-xs text-gray-400 mt-1">
            PDF, image (OCR), Word, or text file
          </p>
        </div>
        <Button onClick={handleScan} loading={scanning} disabled={!file} className="w-full">
          📷 Scan & Convert to Dyslexia Format
        </Button>
      </Card>

      {/* Loading */}
      {scanning && (
        <div className="flex flex-col items-center py-10 gap-3">
          <Spinner size="lg" />
          <p className="dyslexia-text text-[#1A6B6B] font-semibold">Reading and converting document…</p>
          <p className="dyslexia-text text-sm text-gray-400">This may take a moment for images.</p>
        </div>
      )}

      {/* Step 2: Preview result */}
      {result && !scanning && (
        <Card>
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h2 className="dyslexia-text font-bold text-lg">Step 2: Preview Converted Text</h2>
            <div className="flex gap-2 flex-wrap">
              <Badge color="teal">{result.wordCount} words</Badge>
              {result.method && <Badge color="amber">{result.method}</Badge>}
            </div>
          </div>
          <div className="bg-[#FFF8F0] rounded-xl p-4 mb-4 max-h-64 overflow-y-auto">
            <ReadingText
              text={result.simplified || result.original || ''}
              highlights={result.highlights || []}
            />
          </div>
          {(result.bullet_points || []).length > 0 && (
            <div className="bg-white rounded-xl border border-[#E5E0D8] p-4">
              <p className="dyslexia-text font-semibold text-sm mb-2">• Key Points:</p>
              <ol className="flex flex-col gap-1.5">
                {result.bullet_points.map((bp, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-[#1A6B6B] font-bold shrink-0">{i + 1}.</span>
                    <p className="dyslexia-text text-sm">{bp}</p>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </Card>
      )}

      {/* Step 3: Create assignment */}
      {result && !scanning && (
        <Card className={created ? 'border-2 border-green-200 bg-green-50' : ''}>
          <h2 className="dyslexia-text font-bold text-lg mb-4">
            {created ? '✅ Assignment Created!' : 'Step 3: Post to Class'}
          </h2>
          {!created && (
            <div className="flex flex-col gap-4">
              <input
                className="w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                  focus:outline-none focus:border-[#1A6B6B]"
                placeholder="Assignment title"
                value={assignForm.title}
                onChange={(e) => setAssignForm((f) => ({ ...f, title: e.target.value }))}
              />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="dyslexia-text font-semibold block mb-1 text-sm">Due In</label>
                  <select
                    value={assignForm.dueInDays}
                    onChange={(e) => setAssignForm((f) => ({ ...f, dueInDays: e.target.value }))}
                    className="w-full px-3 py-2.5 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                      focus:outline-none focus:border-[#1A6B6B]"
                  >
                    <option value="1">Tomorrow</option>
                    <option value="3">3 days</option>
                    <option value="7">1 week</option>
                    <option value="14">2 weeks</option>
                  </select>
                </div>
                <div>
                  <label className="dyslexia-text font-semibold block mb-1 text-sm">Max Score</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2.5 rounded-xl border-2 border-[#E5E0D8] bg-white dyslexia-text
                      focus:outline-none focus:border-[#1A6B6B]"
                    value={assignForm.maxScore}
                    onChange={(e) => setAssignForm((f) => ({ ...f, maxScore: e.target.value }))}
                  />
                </div>
              </div>
              <Button onClick={handleCreateAssignment} loading={creating} size="lg" className="w-full" variant="accent">
                📤 Post Assignment to Class
              </Button>
            </div>
          )}
          {created && (
            <p className="dyslexia-text text-green-700">
              The converted document has been posted as an assignment. Your students will see it in their assignments.
            </p>
          )}
        </Card>
      )}
    </div>
  )
}
