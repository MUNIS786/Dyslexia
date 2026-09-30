/**
 * frontend/src/features/tutor/TutorPromptChips.jsx
 *
 * Child-friendly quick question suggestions to inspire the learner
 * and make asking for help easy without heavy typing.
 */
import React from 'react'

const DEFAULT_PROMPTS = [
  { id: 'p1', label: '📖 Explain this story', query: 'Can you help me understand what happened in this story?' },
  { id: 'p2', label: '🔍 Explain this word', query: 'Can you explain the meaning of this word simply?' },
  { id: 'p3', label: '💡 Give me a hint', query: 'Can you give me a gentle hint for my question?' },
  { id: 'p4', label: '✍️ How do I spell...', query: 'How do I spell this word and remember the letters?' },
  { id: 'p5', label: '🌟 I need encouragement', query: "I'm finding this reading tricky. Can you encourage me?" },
]

export default function TutorPromptChips({ onSelectPrompt, disabled = false }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none py-1">
      <span className="text-xs font-bold text-stone-500 shrink-0 hidden sm:inline">
        Quick Ask:
      </span>
      {DEFAULT_PROMPTS.map((p) => (
        <button
          key={p.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelectPrompt(p.query)}
          className="shrink-0 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 transition-all active:scale-95 disabled:opacity-50 cursor-pointer shadow-2xs hover:shadow-xs"
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
