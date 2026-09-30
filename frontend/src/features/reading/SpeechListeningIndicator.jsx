/**
 * frontend/src/features/reading/SpeechListeningIndicator.jsx
 *
 * Child-friendly live speech recognition control bar & waveform indicator:
 * - Clear microphone status: Ready, Requesting, Listening, Processing, Analyzed, Unsupported, Denied
 * - Live feedback: elapsed time, detected word count, interim transcript preview
 * - Large, accessible, encouraging action buttons
 * - Privacy assurance note: "No audio is recorded or stored."
 */
import React from 'react'

export default function SpeechListeningIndicator({
  speechState,
  speakingSeconds = 0,
  detectedWordCount = 0,
  interimTranscript = '',
  onStart,
  onStop,
  onReset,
  isSpeechSupported = true,
  errorMessage = null,
}) {
  const formatTime = (secs) => {
    const mins = Math.floor(secs / 60)
    const rem = secs % 60
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`
  }

  // Unsupported Browser Banner
  if (!isSpeechSupported || speechState === 'unsupported') {
    return (
      <div className="p-4 mb-5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs sm:text-sm flex items-center gap-3">
        <span className="text-2xl">🎙️</span>
        <div className="flex-1">
          <p className="font-bold">Read Aloud is not supported in this browser.</p>
          <p className="text-amber-700 mt-0.5">
            You can still enjoy reading silently, using Focus Mode, or listening with audio!
          </p>
        </div>
      </div>
    )
  }

  // Permission Denied Banner
  if (speechState === 'permission_denied') {
    return (
      <div className="p-4 mb-5 rounded-2xl bg-stone-100 border border-stone-300 text-stone-800 text-xs sm:text-sm flex items-center gap-3">
        <span className="text-2xl">🔒</span>
        <div className="flex-1">
          <p className="font-bold">Microphone access was not granted.</p>
          <p className="text-stone-600 mt-0.5">
            That's totally okay! You can continue reading silently or switch to Listen Mode anytime.
          </p>
        </div>
        <button
          onClick={onStart}
          className="px-3 py-1.5 bg-[#1A6B6B] text-white rounded-xl text-xs font-bold hover:bg-[#155757] transition-all cursor-pointer"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="mb-6 p-4 sm:p-5 rounded-3xl bg-gradient-to-r from-teal-50 via-cyan-50 to-emerald-50 border border-teal-200 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Status & Micro-Animation */}
        <div className="flex items-center gap-3">
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl transition-all shadow-sm ${
              speechState === 'listening'
                ? 'bg-red-500 text-white animate-pulse shadow-red-200'
                : speechState === 'processing'
                ? 'bg-amber-400 text-white animate-spin'
                : 'bg-white text-teal-800 border border-teal-200'
            }`}
          >
            {speechState === 'listening' ? '🎙️' : speechState === 'processing' ? '⚙️' : '🎤'}
          </div>

          <div>
            <h4 className="text-sm font-extrabold text-stone-900 flex items-center gap-2">
              <span>
                {speechState === 'listening'
                  ? 'Listening to your voice...'
                  : speechState === 'requesting'
                  ? 'Requesting microphone...'
                  : speechState === 'processing'
                  ? 'Checking your reading...'
                  : speechState === 'analyzed'
                  ? 'Reading Checked! 🎉'
                  : 'Ready to Read Aloud'}
              </span>
              {speechState === 'listening' && (
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
              )}
            </h4>

            <p className="text-xs text-stone-600 font-medium">
              {speechState === 'listening'
                ? 'Read the passage at your comfortable pace. Speak clearly.'
                : 'Tap "Start Reading Aloud" when you are ready.'}
            </p>
          </div>
        </div>

        {/* Right: Action Buttons & Counters */}
        <div className="flex items-center gap-2 sm:gap-3">
          {speechState === 'listening' && (
            <div className="flex items-center gap-3 px-3 py-1.5 bg-white/80 rounded-2xl border border-teal-100 text-xs font-bold text-stone-700">
              <span>⏱️ {formatTime(speakingSeconds)}</span>
              <span className="text-stone-300">|</span>
              <span>🗣️ {detectedWordCount} words</span>
            </div>
          )}

          {speechState === 'ready' && (
            <button
              onClick={onStart}
              className="px-4 sm:px-5 py-2.5 rounded-2xl bg-[#1A6B6B] text-white font-extrabold text-xs sm:text-sm hover:bg-[#155757] shadow-sm transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>🎤</span>
              <span>Start Reading Aloud</span>
            </button>
          )}

          {speechState === 'listening' && (
            <button
              onClick={onStop}
              className="px-4 sm:px-5 py-2.5 rounded-2xl bg-red-600 text-white font-extrabold text-xs sm:text-sm hover:bg-red-700 shadow-sm transition-all flex items-center gap-2 cursor-pointer"
            >
              <span>⏹️</span>
              <span>Done Reading!</span>
            </button>
          )}

          {speechState === 'analyzed' && (
            <button
              onClick={onReset}
              className="px-3 sm:px-4 py-2 rounded-2xl bg-white border border-teal-300 text-teal-800 font-extrabold text-xs hover:bg-teal-50 shadow-sm transition-all cursor-pointer"
            >
              Read Again 🔄
            </button>
          )}
        </div>
      </div>

      {/* Live Interim Transcript Bubble */}
      {speechState === 'listening' && interimTranscript && (
        <div className="mt-3 pt-3 border-t border-teal-100 text-xs font-medium text-stone-600 italic bg-white/60 p-2.5 rounded-xl">
          "{interimTranscript}..."
        </div>
      )}

      {/* Error message if any */}
      {errorMessage && speechState === 'error' && (
        <div className="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-medium">
          {errorMessage}
        </div>
      )}

      {/* Privacy Guarantee Note */}
      <p className="mt-2 text-[10px] text-stone-600 flex items-center gap-1 font-medium">
        <span>🔒</span>
        <span>Privacy-first: Your voice is analyzed directly in your browser. No audio is recorded or stored.</span>
      </p>
    </div>
  )
}
