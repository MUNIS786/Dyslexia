import React from 'react'

export default function ContentValidationPanel({ validationResult, onClose }) {
  if (!validationResult) return null

  const { isValid, errors = [], warnings = [], completenessScore = 0, details = {} } = validationResult

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl font-bold ${
              isValid ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
            }`}
          >
            {isValid ? '✓' : '⚠'}
          </div>
          <div>
            <h4 className="font-bold text-gray-900 text-base">
              {isValid ? 'Quality Checks Passed' : 'Validation Issues Detected'}
            </h4>
            <p className="text-xs text-gray-500">
              {isValid
                ? 'Content meets DyslexAid educational standards and is ready for review.'
                : 'Please resolve blocking errors before submitting for review.'}
            </p>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-sm font-semibold p-1"
            aria-label="Close validation panel"
          >
            ✕
          </button>
        )}
      </div>

      {/* Completeness Score Bar */}
      <div>
        <div className="flex justify-between items-center text-xs font-semibold text-gray-600 mb-1">
          <span>Completeness & Quality Score</span>
          <span className={completenessScore >= 80 ? 'text-emerald-600' : completenessScore >= 50 ? 'text-amber-600' : 'text-rose-600'}>
            {completenessScore}/100
          </span>
        </div>
        <div className="w-full bg-gray-100 h-2.5 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              completenessScore >= 80 ? 'bg-emerald-500' : completenessScore >= 50 ? 'bg-amber-500' : 'bg-rose-500'
            }`}
            style={{ width: `${completenessScore}%` }}
          />
        </div>
      </div>

      {/* Diagnostic Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
          <span className="text-gray-500 block">Word Count</span>
          <span className="font-bold text-gray-800">{details.wordCount ?? 0}</span>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
          <span className="text-gray-500 block">Language</span>
          <span className="font-bold text-gray-800 uppercase">{details.language ?? 'en'}</span>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
          <span className="text-gray-500 block">Questions</span>
          <span className="font-bold text-gray-800">{details.questionCount ?? 0}</span>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
          <span className="text-gray-500 block">Vocabulary</span>
          <span className="font-bold text-gray-800">{details.vocabularyCount ?? 0}</span>
        </div>
      </div>

      {/* Blocking Errors */}
      {errors.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 space-y-1.5">
          <div className="flex items-center gap-2 text-rose-800 font-bold text-xs uppercase tracking-wider">
            <span>⛔ Blocking Errors ({errors.length})</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-xs text-rose-700">
            {errors.map((err, idx) => (
              <li key={idx} className="leading-relaxed">{err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 space-y-1.5">
          <div className="flex items-center gap-2 text-amber-800 font-bold text-xs uppercase tracking-wider">
            <span>⚠️ Recommendations & Warnings ({warnings.length})</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-xs text-amber-700">
            {warnings.map((warn, idx) => (
              <li key={idx} className="leading-relaxed">{warn}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Eligibility status */}
      <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
        <span>Phase 15 Discovery Gate:</span>
        <span className={`font-semibold ${isValid ? 'text-emerald-600' : 'text-gray-400'}`}>
          {isValid ? 'Eligible on Publish' : 'Not Eligible (Resolve Errors)'}
        </span>
      </div>
    </div>
  )
}
