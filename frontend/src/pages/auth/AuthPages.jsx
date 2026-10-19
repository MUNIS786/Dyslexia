import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTranslation } from '../../i18n/I18nContext'
import LanguageSelector from '../../components/shared/LanguageSelector'
import { authAPI } from '../../api/client'
import { Button, Input, Card, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

function AuthShell({ children, title, subtitle }) {
  const { t } = useTranslation()

  return (
    <div
      className="min-h-screen flex flex-col justify-between p-4 sm:p-6 relative bg-slate-50/70"
      style={{ backgroundColor: 'var(--bg-color)' }}
    >
      {/* Top Header Bar */}
      <header className="w-full max-w-4xl mx-auto flex items-center justify-between py-2">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-slate-700 hover:text-indigo-600 font-bold transition-colors text-sm dyslexia-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 rounded-lg px-2 py-1"
          aria-label={t('auth.backToHome', 'Back to Home')}
        >
          <span aria-hidden="true">←</span>
          <span>{t('auth.backToHome', 'Back to Home')}</span>
        </Link>
        <div className="flex items-center gap-3">
          <LanguageSelector />
        </div>
      </header>

      {/* Main Container */}
      <main className="w-full max-w-md mx-auto my-auto py-4">
        {/* Brand Banner */}
        <div className="text-center mb-6">
          <Link to="/" className="inline-flex flex-col items-center group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 rounded-2xl p-1">
            <div className="w-14 h-14 bg-indigo-600 text-white rounded-2xl flex items-center justify-center text-2xl mb-2.5 shadow-md group-hover:scale-105 transition-transform">
              📖
            </div>
            <div className="flex items-center gap-2">
              <span className="dyslexia-text text-2xl font-black text-slate-900 tracking-normal">
                DyslexAid
              </span>
              <span className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded-md">
                V2
              </span>
            </div>
          </Link>
          <p className="dyslexia-text text-slate-500 text-sm mt-1">
            {t('auth.tagline', 'Reading companion for every student')}
          </p>
        </div>

        {/* Card Form */}
        <Card className="p-6 sm:p-8 space-y-5 shadow-card border-slate-200">
          <div className="border-b border-slate-100 pb-3">
            <h1 className="dyslexia-text text-xl sm:text-2xl font-extrabold text-slate-900 leading-snug">
              {title}
            </h1>
            {subtitle && (
              <p className="dyslexia-text text-slate-500 text-sm mt-1">
                {subtitle}
              </p>
            )}
          </div>
          {children}
        </Card>

        {/* Audience Indicator */}
        <div className="mt-6 text-center text-xs text-slate-400 dyslexia-text">
          <span>Accessible Learning for </span>
          <span className="font-semibold text-slate-600">Students</span> •{' '}
          <span className="font-semibold text-slate-600">Teachers</span> •{' '}
          <span className="font-semibold text-slate-600">Parents</span>
        </div>
      </main>

      {/* Subtle Footer */}
      <footer className="w-full max-w-4xl mx-auto text-center py-4 text-xs text-slate-400 dyslexia-text">
        DyslexAid V2 • Universal Accessible Reading Platform
      </footer>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    if (!form.email || !form.password) {
      setError(t('auth.fillAllFields', 'Please fill in all required fields.'))
      return
    }
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      toast.success(t('auth.welcomeBack', { name: user.name }))
      navigate(user.role === 'teacher' ? '/teacher' : user.role === 'parent' ? '/parent/dashboard' : '/student')
    } catch (err) {
      setError(err.response?.data?.detail || t('auth.loginFailed', 'Login failed. Check your details.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.loginTitle', 'Welcome back 👋')}
      subtitle={t('auth.loginSubtitle', 'Sign in to continue learning')}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <Alert type="error">{error}</Alert>}
        <Input
          label={t('auth.email', '📧 Email Address')}
          type="email"
          placeholder="your@email.com"
          value={form.email}
          onChange={set('email')}
          autoComplete="email"
          required
        />
        <Input
          label={t('auth.password', '🔑 Password')}
          type={showPassword ? 'text' : 'password'}
          placeholder="Your password"
          value={form.password}
          onChange={set('password')}
          autoComplete="current-password"
          required
          rightAdornment={
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="p-1 text-slate-400 hover:text-slate-600 focus:outline-none focus:text-indigo-600 rounded"
              aria-label={showPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? '👁️' : '🙈'}
            </button>
          }
        />
        <Button
          type="submit"
          loading={loading}
          size="lg"
          className="w-full mt-2"
        >
          {t('auth.signIn', 'Sign In')} →
        </Button>
        <p className="dyslexia-text text-center text-sm text-slate-600 pt-2">
          {t('auth.newUser', 'New user?')}{' '}
          <Link to="/register" className="text-indigo-600 font-bold hover:underline">
            {t('auth.createAccount', 'Create account')}
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}

export function RegisterPage() {
  const { login } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'student',
    schoolName: '',
    age: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    if (!form.name || !form.email || !form.password) {
      setError(t('auth.fillAllFields', 'Please fill in all required fields.'))
      return
    }
    if (form.password.length < 6) {
      setError(t('auth.passwordTooShort', 'Password must be at least 6 characters.'))
      return
    }
    setLoading(true)
    try {
      const data = await authAPI.signup({
        ...form,
        age: form.age ? parseInt(form.age, 10) : undefined,
      })
      localStorage.setItem('dyslexaid_token', data.token)
      await login(form.email, form.password)
      toast.success(t('auth.welcome', { name: data.user.name }))
      navigate(data.user.role === 'teacher' ? '/teacher' : data.user.role === 'parent' ? '/parent/dashboard' : '/student/screening')
    } catch (err) {
      setError(err.response?.data?.detail || t('auth.registerFailed', 'Registration failed. Try a different email.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.registerTitle', 'Create your account ✨')}
      subtitle={t('auth.registerSubtitle', 'Join thousands of learners today')}
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <Alert type="error">{error}</Alert>}
        <Input
          label={t('auth.fullName', '👤 Full Name')}
          placeholder="Your full name"
          value={form.name}
          onChange={set('name')}
          required
        />
        <Input
          label={t('auth.email', '📧 Email Address')}
          type="email"
          placeholder="your@email.com"
          value={form.email}
          onChange={set('email')}
          autoComplete="email"
          required
        />
        <Input
          label={t('auth.password', '🔑 Password')}
          type={showPassword ? 'text' : 'password'}
          placeholder="At least 6 characters"
          value={form.password}
          onChange={set('password')}
          autoComplete="new-password"
          required
          helperText={t('auth.passwordTooShort', 'Password must be at least 6 characters.')}
          rightAdornment={
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="p-1 text-slate-400 hover:text-slate-600 focus:outline-none focus:text-indigo-600 rounded"
              aria-label={showPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? '👁️' : '🙈'}
            </button>
          }
        />

        {/* Role Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="dyslexia-text font-bold text-sm text-slate-800">
            {t('auth.role', '👔 I am a...')}
          </label>
          <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Account Role">
            {[
              { value: 'student', icon: '🧑‍🎓', label: t('auth.student', 'Student') },
              { value: 'teacher', icon: '👩‍🏫', label: t('auth.teacher', 'Teacher') },
              { value: 'parent', icon: '👨‍👩‍👧', label: t('auth.parent', 'Parent') },
            ].map((r) => {
              const isSelected = form.role === r.value
              return (
                <button
                  key={r.value}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setForm((f) => ({ ...f, role: r.value }))}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-xl border-2 transition-all min-h-[58px] dyslexia-text cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 ${
                    isSelected
                      ? 'border-indigo-600 bg-indigo-50/70 text-indigo-900 font-bold shadow-2xs'
                      : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                  }`}
                >
                  <span className="text-xl mb-1">{r.icon}</span>
                  <span className="text-xs leading-none">{r.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <Input
          label={t('auth.schoolName', '🏫 School Name')}
          placeholder="Your school name"
          value={form.schoolName}
          onChange={set('schoolName')}
        />

        {form.role === 'student' && (
          <Input
            label={t('auth.age', '🎂 Age')}
            type="number"
            placeholder="Your age"
            value={form.age}
            onChange={set('age')}
            min="5"
            max="25"
          />
        )}

        <Button
          type="submit"
          loading={loading}
          size="lg"
          className="w-full mt-2"
        >
          {t('auth.createAccount', 'Create Account')} →
        </Button>
        <p className="dyslexia-text text-center text-sm text-slate-600 pt-2">
          {t('auth.haveAccount', 'Already have an account?')}{' '}
          <Link to="/login" className="text-indigo-600 font-bold hover:underline">
            {t('auth.signIn', 'Sign in')}
          </Link>
        </p>
      </form>
    </AuthShell>
  )
}
