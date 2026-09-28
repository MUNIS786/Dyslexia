import { useState, useEffect } from 'react'
import { classroomAPI } from '../../api/client'
import { Card, Button, PageHeader, Badge, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

export default function JoinClassroom() {
  const [code, setCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [leaving, setLeaving] = useState(false)
  const [classroom, setClassroom] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    classroomAPI.info()
      .then((d) => setClassroom(d.classroom || null))
      .catch(() => setClassroom(null))
      .finally(() => setLoading(false))
  }, [])

  const handleJoin = async () => {
    if (!code.trim()) return
    setJoining(true)
    try {
      const res = await classroomAPI.join(code.trim())
      setResult(res)
      setClassroom({ teacherName: res.teacherName, schoolName: res.schoolName, code: res.classroomCode })
      toast.success(`✅ Joined ${res.teacherName}'s classroom!`)
      setCode('')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid classroom code. Please check and try again.')
    } finally {
      setJoining(false)
    }
  }

  const handleLeave = async () => {
    if (!confirm('Are you sure you want to leave this classroom?')) return
    setLeaving(true)
    try {
      await classroomAPI.leave()
      setClassroom(null)
      setResult(null)
      toast.success('You have left the classroom.')
    } catch {
      toast.error('Could not leave classroom.')
    } finally {
      setLeaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader icon="🏫" title="Classroom" subtitle="Join your teacher's classroom using a code." />

      {/* Current classroom */}
      {!loading && classroom && (
        <Card className="border-2 border-green-200 bg-green-50">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="dyslexia-text font-bold text-lg text-green-800">✅ You are in a classroom</p>
              <div className="flex flex-col gap-1 mt-2">
                <p className="dyslexia-text text-sm text-green-700">
                  👩‍🏫 Teacher: <span className="font-semibold">{classroom.teacherName}</span>
                </p>
                {classroom.schoolName && (
                  <p className="dyslexia-text text-sm text-green-700">
                    🏫 School: <span className="font-semibold">{classroom.schoolName}</span>
                  </p>
                )}
                {classroom.code && (
                  <p className="dyslexia-text text-sm text-green-700">
                    🔑 Code: <span className="font-mono font-bold text-base">{classroom.code}</span>
                  </p>
                )}
              </div>
            </div>
            <Button variant="danger" size="sm" onClick={handleLeave} loading={leaving}>
              Leave Classroom
            </Button>
          </div>
        </Card>
      )}

      {/* Join result */}
      {result && (
        <Alert type="success">
          <p className="dyslexia-text font-semibold">
            Welcome to {result.teacherName}'s class!
          </p>
          {result.pendingAssignments > 0 && (
            <p className="dyslexia-text text-sm mt-1">
              📝 You have {result.pendingAssignments} assignment{result.pendingAssignments !== 1 ? 's' : ''} waiting.
            </p>
          )}
        </Alert>
      )}

      {/* Join form — only show if not in classroom */}
      {!classroom && (
        <Card>
          <h2 className="dyslexia-text font-bold text-lg mb-2">Enter Classroom Code</h2>
          <p className="dyslexia-text text-sm text-gray-500 mb-4">
            Ask your teacher for the 6-letter code.
          </p>
          <div className="flex gap-3 flex-wrap">
            <input
              className="flex-1 min-w-[160px] px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white
                dyslexia-text text-xl font-mono tracking-widest uppercase focus:outline-none focus:border-[#1A6B6B]"
              placeholder="ABC123"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase().slice(0, 8))}
              onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
              maxLength={8}
            />
            <Button onClick={handleJoin} loading={joining} disabled={!code.trim()} size="lg">
              Join Classroom
            </Button>
          </div>
        </Card>
      )}

      <Alert type="info">
        <p className="dyslexia-text text-sm">
          Your teacher will share assignments and announcements with you once you join their classroom.
        </p>
      </Alert>
    </div>
  )
}
