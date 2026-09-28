import { useState } from 'react'

// ─── Spinner ───────────────────────────────────────────────────────────────
export function Spinner({ size = 'md', className = '' }) {
  const sz = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }[size]
  return (
    <div
      className={`${sz} border-4 border-[#1A6B6B] border-t-transparent rounded-full animate-spin ${className}`}
    />
  )
}

// ─── LoadingScreen ─────────────────────────────────────────────────────────
export function LoadingScreen() {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center gap-4"
      style={{ backgroundColor: 'var(--bg-color)' }}>
      <div className="text-4xl">📚</div>
      <Spinner size="lg" />
      <p className="dyslexia-text text-[var(--primary)] font-semibold">Loading DyslexAid…</p>
    </div>
  )
}

// ─── Card ──────────────────────────────────────────────────────────────────
export function Card({ children, className = '', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl shadow-sm border border-[#E5E0D8] p-5 ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

// ─── Button ────────────────────────────────────────────────────────────────
export function Button({
  children,
  onClick,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
  type = 'button',
}) {
  const base =
    'inline-flex items-center justify-center gap-2 font-semibold rounded-xl min-h-[44px] transition-all focus-visible:ring-2 focus-visible:ring-[#E8A020] focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-[#1A6B6B] text-white hover:bg-[#155858] active:scale-95',
    secondary: 'bg-[#FFF8F0] text-[#1A6B6B] border border-[#1A6B6B] hover:bg-[#1A6B6B] hover:text-white',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    ghost: 'bg-transparent text-[#1A6B6B] hover:bg-[#E8F4F4]',
    accent: 'bg-[#E8A020] text-white hover:bg-[#D09018] active:scale-95',
  }
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-5 py-2.5 text-base',
    lg: 'px-7 py-3.5 text-lg',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading ? <Spinner size="sm" /> : children}
    </button>
  )
}

// ─── Input ────────────────────────────────────────────────────────────────
export function Input({ label, error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="dyslexia-text font-semibold text-[var(--text-color)]">{label}</label>
      )}
      <input
        className={`w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white text-[var(--text-color)]
          focus:outline-none focus:border-[#1A6B6B] transition-colors min-h-[44px]
          dyslexia-text ${error ? 'border-red-400' : ''} ${className}`}
        {...props}
      />
      {error && <p className="text-red-500 text-sm flex items-center gap-1">⚠️ {error}</p>}
    </div>
  )
}

// ─── Select ───────────────────────────────────────────────────────────────
export function Select({ label, options = [], error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="dyslexia-text font-semibold text-[var(--text-color)]">{label}</label>
      )}
      <select
        className={`w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white text-[var(--text-color)]
          focus:outline-none focus:border-[#1A6B6B] transition-colors min-h-[44px] dyslexia-text ${className}`}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-red-500 text-sm">⚠️ {error}</p>}
    </div>
  )
}

// ─── Textarea ─────────────────────────────────────────────────────────────
export function Textarea({ label, error, className = '', ...props }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="dyslexia-text font-semibold text-[var(--text-color)]">{label}</label>
      )}
      <textarea
        className={`w-full px-4 py-3 rounded-xl border-2 border-[#E5E0D8] bg-white text-[var(--text-color)]
          focus:outline-none focus:border-[#1A6B6B] transition-colors dyslexia-text resize-none ${className}`}
        {...props}
      />
      {error && <p className="text-red-500 text-sm">⚠️ {error}</p>}
    </div>
  )
}

// ─── Badge ────────────────────────────────────────────────────────────────
export function Badge({ children, color = 'teal', className = '' }) {
  const colors = {
    teal: 'bg-[#E0F2F2] text-[#1A6B6B]',
    amber: 'bg-[#FFF3DC] text-[#B07818]',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-700',
    gray: 'bg-gray-100 text-gray-600',
    blue: 'bg-blue-100 text-blue-700',
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold ${colors[color]} ${className}`}
    >
      {children}
    </span>
  )
}

// ─── ProgressBar ──────────────────────────────────────────────────────────
export function ProgressBar({ value = 0, max = 100, color = 'teal', label, className = '' }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const colors = {
    teal: 'bg-[#1A6B6B]',
    amber: 'bg-[#E8A020]',
    green: 'bg-green-500',
    red: 'bg-red-500',
  }
  return (
    <div className={className}>
      {label && (
        <div className="flex justify-between mb-1">
          <span className="text-sm dyslexia-text">{label}</span>
          <span className="text-sm font-semibold dyslexia-text">{pct}%</span>
        </div>
      )}
      <div className="w-full h-3 bg-[#E5E0D8] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colors[color]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ─── StatCard ─────────────────────────────────────────────────────────────
export function StatCard({ icon, label, value, sub, color = 'teal' }) {
  const colors = {
    teal: 'bg-[#E0F2F2] text-[#1A6B6B]',
    amber: 'bg-[#FFF3DC] text-[#B07818]',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
  }
  return (
    <Card className="flex items-center gap-4">
      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl ${colors[color]}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500 dyslexia-text">{label}</p>
        <p className="text-2xl font-bold dyslexia-text">{value}</p>
        {sub && <p className="text-xs text-gray-400 dyslexia-text">{sub}</p>}
      </div>
    </Card>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────
export function EmptyState({ icon = '📭', title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
      <div className="text-6xl">{icon}</div>
      <h3 className="dyslexia-text text-xl font-bold text-[var(--text-color)]">{title}</h3>
      {message && <p className="dyslexia-text text-gray-500 max-w-sm">{message}</p>}
      {action}
    </div>
  )
}

// ─── PageHeader ───────────────────────────────────────────────────────────
export function PageHeader({ icon, title, subtitle, action }) {
  return (
    <div className="flex items-center justify-between mb-6 gap-4">
      <div>
        <h1 className="dyslexia-text text-2xl font-bold flex items-center gap-2">
          {icon && <span>{icon}</span>}
          {title}
        </h1>
        {subtitle && <p className="dyslexia-text text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

// ─── Modal ────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="dyslexia-text text-xl font-bold">{title}</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-gray-100 text-gray-500"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ─── Alert ────────────────────────────────────────────────────────────────
export function Alert({ type = 'info', children }) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    error: 'bg-red-50 border-red-200 text-red-800',
  }
  const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' }
  return (
    <div className={`flex gap-3 p-4 rounded-xl border dyslexia-text ${styles[type]}`}>
      <span>{icons[type]}</span>
      <div>{children}</div>
    </div>
  )
}

// ─── ReadingText ──────────────────────────────────────────────────────────
export function ReadingText({ text = '', highlights = [], wordIndex = -1, words = [] }) {
  if (!text) return null
  const highlightSet = new Set((highlights || []).map((h) => h.toLowerCase()))

  const textWords = text.split(/(\s+)/)
  let wordCount = 0

  return (
    <p
      className="dyslexia-text"
      style={{ lineHeight: 'var(--line-spacing)', letterSpacing: 'var(--letter-spacing)' }}
    >
      {textWords.map((chunk, i) => {
        if (/^\s+$/.test(chunk)) return <span key={i}>{chunk}</span>
        const idx = wordCount++
        const isHighlighted = highlightSet.has(chunk.toLowerCase().replace(/[^a-z]/g, ''))
        const isCurrent = idx === wordIndex
        return (
          <span
            key={i}
            className={isCurrent ? 'current-word' : isHighlighted ? 'highlight-word' : ''}
          >
            {chunk}
          </span>
        )
      })}
    </p>
  )
}

// ─── TTSButton ────────────────────────────────────────────────────────────
export function TTSButton({ text, speed = 1, speaking, onToggle, className = '' }) {
  return (
    <button
      onClick={() => onToggle(text, speed)}
      className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold min-h-[44px]
        transition-all focus-visible:ring-2 focus-visible:ring-[#E8A020]
        ${speaking
          ? 'bg-[#E8A020] text-white'
          : 'bg-[#E0F2F2] text-[#1A6B6B] hover:bg-[#1A6B6B] hover:text-white'}
        ${className}`}
    >
      {speaking ? '⏸ Pause' : '▶ Listen'}
    </button>
  )
}
