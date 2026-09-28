import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { libraryAPI } from '../../api/client'
import { Card, Button, Badge, PageHeader, EmptyState, Spinner } from '../../components/ui'
import toast from 'react-hot-toast'

export default function LibraryPage() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    libraryAPI.list().then(setDocs).catch(() => toast.error('Could not load library.')).finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this document?')) return
    setDeleting(id)
    try {
      await libraryAPI.delete(id)
      setDocs((prev) => prev.filter((d) => d.id !== id))
      toast.success('Deleted.')
    } catch {
      toast.error('Could not delete.')
    } finally {
      setDeleting(null)
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        icon="📚"
        title="My Library"
        subtitle="All your saved documents."
        action={
          <Button onClick={() => navigate('/student/scan')}>
            + Scan New
          </Button>
        }
      />

      {docs.length === 0 ? (
        <EmptyState
          icon="📚"
          title="No documents yet"
          message="Scan a document to save it here. Your library will grow over time."
          action={<Button onClick={() => navigate('/student/scan')}>📷 Scan Text</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {docs.map((doc) => (
            <Card
              key={doc.id}
              onClick={() => navigate(`/student/library/${doc.id}`)}
              className="hover:border-[#1A6B6B] transition-colors"
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1 min-w-0">
                  <p className="dyslexia-text font-bold truncate">{doc.title}</p>
                  <p className="dyslexia-text text-xs text-gray-500 mt-0.5">
                    {new Date(doc.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDelete(doc.id, e)}
                  disabled={deleting === doc.id}
                  className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-red-50 text-red-400 hover:text-red-600 shrink-0"
                >
                  {deleting === doc.id ? '…' : '🗑'}
                </button>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge color="teal">{doc.language?.toUpperCase()}</Badge>
                <Badge color="gray">{doc.wordCount?.toLocaleString() || 0} words</Badge>
                {doc.source && <Badge color="amber">{doc.source}</Badge>}
              </div>
              <p className="dyslexia-text text-sm text-gray-500 mt-3 line-clamp-2">
                {(doc.simplified || doc.original || '').slice(0, 120)}…
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
