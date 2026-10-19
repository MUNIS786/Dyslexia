/**
 * frontend/src/features/tutor/TutorMessageBubble.jsx
 *
 * Child-friendly conversational message bubble supporting:
 * - Dyslexia-accessible layout and line spacing
 * - Formatted text with emphasis and bullet points
 * - Concept explanation card
 * - Actionable next learning steps
 * - Gentle follow-up check questions
 */

export default function TutorMessageBubble({
  message,
  onExecuteAction,
  studentName = 'You',
}) {
  const isUser = message.role === 'user'

  // Simple Markdown text renderer for bold, italic, and paragraphs
  const renderFormattedText = (rawText) => {
    if (!rawText) return null
    const lines = rawText.split('\n')
    return lines.map((line, idx) => {
      if (!line.trim()) {
        return <div key={idx} className="h-2" />
      }

      // Check if bullet point
      const isBullet = line.trim().startsWith('•') || line.trim().startsWith('-')
      const cleanLine = isBullet ? line.trim().replace(/^[•-]\s*/, '') : line

      // Regex replacement for bold **word**
      const parts = cleanLine.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)

      const renderedParts = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={pIdx} className="font-extrabold text-slate-900">
              {part.slice(2, -2)}
            </strong>
          )
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return (
            <em key={pIdx} className="italic text-slate-800">
              {part.slice(1, -1)}
            </em>
          )
        }
        return part
      })

      if (isBullet) {
        return (
          <div key={idx} className="flex items-start gap-2 ml-2 my-1">
            <span className="text-indigo-600 font-bold" aria-hidden="true">•</span>
            <span className="flex-1 leading-relaxed">{renderedParts}</span>
          </div>
        )
      }

      return (
        <p key={idx} className="leading-relaxed mb-1 last:mb-0">
          {renderedParts}
        </p>
      )
    })
  }

  if (isUser) {
    return (
      <div className="flex items-start justify-end gap-2.5 my-3">
        <div className="max-w-[85%] sm:max-w-[75%] rounded-3xl rounded-tr-xs bg-indigo-600 text-white p-4 shadow-sm">
          <div className="text-xs font-semibold text-indigo-100 mb-1 flex items-center justify-end gap-1">
            <span>{studentName}</span>
          </div>
          <div className="text-sm sm:text-base font-medium dyslexia-text">{message.content}</div>
        </div>
        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-800 flex items-center justify-center shrink-0 border border-indigo-300 text-sm font-bold">
          👤
        </div>
      </div>
    )
  }

  // Assistant bubble
  return (
    <div className="flex items-start gap-2.5 my-3">
      <div className="w-9 h-9 rounded-2xl bg-indigo-100 text-indigo-800 flex items-center justify-center shrink-0 border border-indigo-200 shadow-2xs mt-0.5 text-base">
        🤖
      </div>

      <div className="max-w-[90%] sm:max-w-[80%] space-y-3">
        {/* Main message bubble */}
        <div className="rounded-3xl rounded-tl-xs bg-white text-slate-800 p-4 sm:p-5 border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between text-[11px] font-bold text-slate-500 border-b border-slate-100 pb-1.5">
            <span className="flex items-center gap-1 text-indigo-700">
              Personal AI Tutor
            </span>
            {message.source && (
              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">
                {message.source === 'gemini' ? 'AI Companion' : 'Offline Guide'}
              </span>
            )}
          </div>

          <div className="text-sm sm:text-base font-normal text-slate-800 dyslexia-text leading-relaxed">
            {renderFormattedText(message.content)}
          </div>

          {/* Explanation Callout if present */}
          {message.explanation && (
            <div className="bg-amber-50/80 border border-amber-200 rounded-2xl p-3.5 flex items-start gap-2 text-xs sm:text-sm text-amber-950">
              <span className="text-base shrink-0 mt-0.5" aria-hidden="true">💡</span>
              <div className="leading-snug dyslexia-text">
                <span className="font-bold block text-amber-900 mb-0.5">Quick Insight:</span>
                {message.explanation}
              </div>
            </div>
          )}

          {/* Follow-up question if present */}
          {message.followUpQuestion && (
            <div className="bg-indigo-50/60 border border-indigo-200/80 rounded-2xl p-3.5 flex items-start gap-2 text-xs sm:text-sm text-indigo-950 font-medium">
              <span className="text-base shrink-0 mt-0.5" aria-hidden="true">❓</span>
              <div className="leading-snug dyslexia-text">
                {message.followUpQuestion}
              </div>
            </div>
          )}
        </div>

        {/* Suggested Next Action Button */}
        {message.suggestedAction && onExecuteAction && (
          <div className="flex items-center pl-2">
            <button
              type="button"
              onClick={() => onExecuteAction(message.suggestedAction)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs hover:shadow-md transition-all active:scale-95 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
            >
              <span>{message.suggestedAction.label || 'Try Next Step'}</span>
              <span>➔</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
