import { useEffect } from 'react'

// ─── Spinner ───────────────────────────────────────────────────────────────
export function Spinner({ size = 'md', className = '', color = 'primary' }) {
  const sz = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
    xl: 'w-16 h-16 border-4',
  }[size] || 'w-8 h-8 border-3'

  const col = {
    primary: 'border-indigo-600',
    secondary: 'border-teal-600',
    accent: 'border-amber-500',
    white: 'border-white',
    legacy: 'border-[#1A6B6B]',
  }[color] || 'border-indigo-600'

  return (
    <div
      role="status"
      aria-label="Loading"
      className={`${sz} ${col} border-t-transparent rounded-full animate-spin shrink-0 ${className}`}
    >
      <span className="sr-only">Loading...</span>
    </div>
  )
}

// ─── LoadingScreen ─────────────────────────────────────────────────────────
export function LoadingScreen({ message = 'Loading DyslexAid…' }) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 p-6"
      style={{ backgroundColor: 'var(--bg-color, #F8FAFC)' }}
      role="alert"
      aria-live="polite"
    >
      <div className="w-16 h-16 bg-white rounded-2xl shadow-card border border-slate-200 flex items-center justify-center text-3xl animate-bounce">
        📖
      </div>
      <Spinner size="lg" color="primary" />
      <p className="dyslexia-text text-slate-800 font-bold text-lg">{message}</p>
    </div>
  )
}

// ─── Card ──────────────────────────────────────────────────────────────────
export function Card({ children, className = '', onClick, hover = false, as: Component = 'div', ...props }) {
  const isInteractive = Boolean(onClick) || hover
  return (
    <Component
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? 'button' : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick(e)
              }
            }
          : undefined
      }
      className={`bg-white rounded-2xl shadow-card border border-slate-200 p-5 sm:p-6 transition-all duration-200
        ${isInteractive ? 'cursor-pointer hover:shadow-card-hover hover:border-slate-300 active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:outline-none' : ''}
        ${className}`}
      {...props}
    >
      {children}
    </Component>
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
  icon,
  ...props
}) {
  const base =
    'inline-flex items-center justify-center gap-2 font-bold rounded-xl min-h-[44px] transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none'

  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 shadow-sm hover:shadow',
    secondary: 'bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 hover:text-indigo-800 active:scale-95',
    outline: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 active:scale-95',
    danger: 'bg-rose-600 text-white hover:bg-rose-700 active:scale-95 shadow-sm',
    ghost: 'bg-transparent text-slate-700 hover:bg-slate-100 hover:text-slate-900 active:scale-95',
    accent: 'bg-amber-500 text-white hover:bg-amber-600 active:scale-95 shadow-sm hover:shadow',
    teal: 'bg-teal-600 text-white hover:bg-teal-700 active:scale-95 shadow-sm',
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-xs sm:text-sm min-h-[38px]',
    md: 'px-5 py-2.5 text-sm sm:text-base',
    lg: 'px-7 py-3 text-base sm:text-lg min-h-[50px]',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading}
      className={`${base} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {loading ? (
        <Spinner
          size="sm"
          color={
            variant === 'primary' || variant === 'danger' || variant === 'accent' || variant === 'teal'
              ? 'white'
              : 'primary'
          }
        />
      ) : (
        <>
          {icon && <span className="shrink-0">{icon}</span>}
          {children}
        </>
      )}
    </button>
  )
}

// ─── Input ────────────────────────────────────────────────────────────────
export function Input({ label, error, helperText, id, className = '', ...props }) {
  const inputId = id || (label ? `input-${label.toLowerCase().replace(/[^a-z0-9]/g, '-')}` : undefined)
  const errorId = error && inputId ? `${inputId}-error` : undefined
  const helperId = helperText && inputId ? `${inputId}-helper` : undefined

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="dyslexia-text font-bold text-sm text-slate-800">
          {label}
        </label>
      )}
      <input
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={errorId || helperId}
        className={`w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-800
          focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition-colors min-h-[44px]
          placeholder:text-slate-400 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed
          dyslexia-text ${error ? 'border-rose-400 focus:border-rose-600 focus:ring-rose-100' : ''} ${className}`}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-rose-600 text-xs sm:text-sm font-semibold flex items-center gap-1.5" role="alert">
          <span aria-hidden="true">⚠️</span> {error}
        </p>
      )}
      {!error && helperText && (
        <p id={helperId} className="text-slate-500 text-xs">{helperText}</p>
      )}
    </div>
  )
}

// ─── Select ───────────────────────────────────────────────────────────────
export function Select({ label, options = [], error, helperText, id, className = '', ...props }) {
  const selectId = id || (label ? `select-${label.toLowerCase().replace(/[^a-z0-9]/g, '-')}` : undefined)
  const errorId = error && selectId ? `${selectId}-error` : undefined

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={selectId} className="dyslexia-text font-bold text-sm text-slate-800">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={selectId}
          aria-invalid={!!error}
          aria-describedby={errorId}
          className={`w-full appearance-none px-4 py-2.5 pr-10 rounded-xl border border-slate-200 bg-white text-slate-800
            focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition-colors min-h-[44px]
            disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed
            dyslexia-text ${error ? 'border-rose-400 focus:border-rose-600' : ''} ${className}`}
          {...props}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-xs" aria-hidden="true">
          ▼
        </span>
      </div>
      {error && (
        <p id={errorId} className="text-rose-600 text-xs sm:text-sm font-semibold flex items-center gap-1" role="alert">
          <span aria-hidden="true">⚠️</span> {error}
        </p>
      )}
      {!error && helperText && <p className="text-slate-500 text-xs">{helperText}</p>}
    </div>
  )
}

// ─── Textarea ─────────────────────────────────────────────────────────────
export function Textarea({ label, error, helperText, id, className = '', rows = 3, ...props }) {
  const textareaId = id || (label ? `textarea-${label.toLowerCase().replace(/[^a-z0-9]/g, '-')}` : undefined)
  const errorId = error && textareaId ? `${textareaId}-error` : undefined

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={textareaId} className="dyslexia-text font-bold text-sm text-slate-800">
          {label}
        </label>
      )}
      <textarea
        id={textareaId}
        rows={rows}
        aria-invalid={!!error}
        aria-describedby={errorId}
        className={`w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-800
          focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition-colors
          placeholder:text-slate-400 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed
          dyslexia-text resize-none ${error ? 'border-rose-400 focus:border-rose-600' : ''} ${className}`}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-rose-600 text-xs sm:text-sm font-semibold flex items-center gap-1" role="alert">
          <span aria-hidden="true">⚠️</span> {error}
        </p>
      )}
      {!error && helperText && <p className="text-slate-500 text-xs">{helperText}</p>}
    </div>
  )
}

// ─── Badge ────────────────────────────────────────────────────────────────
export function Badge({ children, color = 'teal', icon, className = '' }) {
  const colors = {
    teal: 'bg-teal-50 text-teal-800 border-teal-200',
    indigo: 'bg-indigo-50 text-indigo-800 border-indigo-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200',
    green: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    red: 'bg-rose-50 text-rose-700 border-rose-200',
    gray: 'bg-slate-100 text-slate-700 border-slate-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
  }
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs sm:text-sm font-bold border ${colors[color] || colors.teal} ${className}`}
    >
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  )
}

// ─── ProgressBar ──────────────────────────────────────────────────────────
export function ProgressBar({ value = 0, max = 100, color = 'teal', label, showValue = true, className = '' }) {
  const pct = Math.max(0, Math.min(100, Math.round(((value || 0) / (max || 100)) * 100)))
  const colors = {
    indigo: 'bg-indigo-600',
    teal: 'bg-teal-600',
    amber: 'bg-amber-500',
    green: 'bg-emerald-500',
    red: 'bg-rose-500',
  }
  return (
    <div className={className}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5 text-xs sm:text-sm">
          {label && <span className="font-medium text-slate-700 dyslexia-text">{label}</span>}
          {showValue && <span className="font-bold text-slate-800 dyslexia-text">{pct}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || 'Progress'}
        className="w-full h-2.5 sm:h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60"
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${colors[color] || colors.teal}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ─── StatCard ─────────────────────────────────────────────────────────────
export function StatCard({ icon, label, value, sub, color = 'teal', className = '' }) {
  const colors = {
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
    teal: 'bg-teal-50 text-teal-700 border-teal-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    red: 'bg-rose-50 text-rose-700 border-rose-100',
    purple: 'bg-purple-50 text-purple-700 border-purple-100',
  }
  return (
    <Card className={`flex items-center gap-4 ${className}`}>
      <div className={`w-12 h-12 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center text-2xl border shrink-0 ${colors[color] || colors.teal}`}>
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs sm:text-sm font-medium text-slate-500 dyslexia-text truncate">{label}</p>
        <p className="text-xl sm:text-2xl font-bold text-slate-800 dyslexia-text leading-tight">{value}</p>
        {sub && <p className="text-xs text-slate-400 dyslexia-text mt-0.5 truncate">{sub}</p>}
      </div>
    </Card>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────
export function EmptyState({ icon = '📭', title, message, action, className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center py-12 sm:py-16 px-4 text-center gap-3 bg-white/60 rounded-2xl border border-dashed border-slate-200 ${className}`}>
      <div className="text-5xl sm:text-6xl mb-1" aria-hidden="true">{icon}</div>
      <h3 className="dyslexia-text text-lg sm:text-xl font-bold text-slate-800">{title}</h3>
      {message && <p className="dyslexia-text text-sm text-slate-500 max-w-md leading-relaxed">{message}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

// ─── PageHeader ───────────────────────────────────────────────────────────
export function PageHeader({ icon, title, subtitle, action, breadcrumb, className = '' }) {
  return (
    <div className={`mb-6 sm:mb-8 ${className}`}>
      {breadcrumb && <div className="mb-2 text-xs text-slate-500 font-medium">{breadcrumb}</div>}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="dyslexia-text text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2.5">
            {icon && <span aria-hidden="true" className="text-2xl sm:text-3xl shrink-0">{icon}</span>}
            <span>{title}</span>
          </h1>
          {subtitle && <p className="dyslexia-text text-slate-500 text-sm sm:text-base mt-1 leading-relaxed">{subtitle}</p>}
        </div>
        {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
      </div>
    </div>
  )
}

// ─── Modal ────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, size = 'md' }) {
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose?.()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }[size] || 'max-w-lg'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog Container */}
      <div
        className={`relative w-full ${sizeClasses} bg-white rounded-2xl shadow-modal border border-slate-200 p-6 my-8 z-10 animate-in fade-in zoom-in-95 duration-150`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
          <h2 id="modal-title" className="dyslexia-text text-lg sm:text-xl font-bold text-slate-800">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
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
export function Alert({ type = 'info', title, children, onClose, className = '' }) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    error: 'bg-rose-50 border-rose-200 text-rose-900',
  }
  const iconColors = {
    info: 'text-blue-500',
    success: 'text-emerald-500',
    warning: 'text-amber-500',
    error: 'text-rose-500',
  }
  const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' }

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 p-4 rounded-xl border text-sm sm:text-base dyslexia-text ${styles[type] || styles.info} ${className}`}
    >
      <span className={`text-lg shrink-0 mt-0.5 ${iconColors[type]}`} aria-hidden="true">
        {icons[type] || 'ℹ️'}
      </span>
      <div className="flex-1 min-w-0">
        {title && <h4 className="font-bold mb-1 leading-snug">{title}</h4>}
        <div className="leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss alert"
          className="shrink-0 p-1 rounded-lg hover:bg-black/5 text-slate-500 transition-colors"
        >
          ✕
        </button>
      )}
    </div>
  )
}

// ─── ReadingText ──────────────────────────────────────────────────────────
export function ReadingText({ text = '', highlights = [], wordIndex = -1 }) {
  if (!text) return null
  const highlightSet = new Set((highlights || []).map((h) => h.toLowerCase()))

  const textWords = text.split(/(\s+)/)
  let wordCount = 0

  return (
    <p
      className="dyslexia-text"
      style={{ lineHeight: 'var(--line-spacing, 1.75)', letterSpacing: 'var(--letter-spacing, 0.04em)' }}
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
      type="button"
      onClick={() => onToggle(text, speed)}
      aria-pressed={speaking}
      aria-label={speaking ? 'Pause speech audio' : 'Listen to text with speech audio'}
      className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold min-h-[44px]
        transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600
        ${speaking
          ? 'bg-amber-500 text-white shadow-sm hover:bg-amber-600'
          : 'bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-600 hover:text-white'}
        ${className}`}
    >
      <span aria-hidden="true">{speaking ? '⏸' : '▶'}</span>
      <span>{speaking ? 'Pause' : 'Listen'}</span>
    </button>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────
export function Skeleton({ className = '' }) {
  return (
    <div
      className={`animate-pulse bg-slate-200/70 rounded-xl ${className}`}
      aria-hidden="true"
    />
  )
}

