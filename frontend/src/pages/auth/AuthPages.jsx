import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTranslation } from '../../i18n/I18nContext'
import LanguageSelector from '../../components/shared/LanguageSelector'
import { authAPI } from '../../api/client'
import { Button, Input, Card, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

export function AuthShell({ children, title, subtitle }) {
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
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => {
    setError('')
    setForm((f) => ({ ...f, [k]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    const trimmedEmail = form.email.trim()
    if (!trimmedEmail || !form.password) {
      setError(t('auth.fillAllFields', 'Please fill in all required fields.'))
      return
    }
    setLoading(true)
    try {
      const user = await login(trimmedEmail, form.password)
      toast.success(t('auth.welcomeBack', { name: user.name }))
      const destination =
        location.state?.from ||
        (user.role === 'teacher' ? '/teacher' : user.role === 'parent' ? '/parent/dashboard' : '/student')
      navigate(destination, { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.loginFailed', 'Login failed. Please check your credentials.'))
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
        <div>
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
          <div className="flex justify-end mt-1.5">
            <Link
              to="/forgot-password"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline dyslexia-text focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-600 rounded px-1"
            >
              {t('auth.forgotPasswordLink', 'Forgot password?')}
            </Link>
          </div>
        </div>

        <Button
          type="submit"
          loading={loading}
          disabled={loading}
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
  const { signup } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'student',
    schoolName: '',
    age: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => {
    setError('')
    setForm((f) => ({ ...f, [k]: e.target.value }))
  }

  const hasLength = form.password.length >= 8
  const hasLetter = /[A-Za-z]/.test(form.password)
  const hasNumberOrSymbol = /[\d\W_]/.test(form.password)
  const passwordsMatch = form.password.length > 0 && form.password === form.confirmPassword

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    const trimmedName = form.name.trim()
    const trimmedEmail = form.email.trim()

    if (!trimmedName || !trimmedEmail || !form.password || !form.confirmPassword) {
      setError(t('auth.fillAllFields', 'Please fill in all required fields.'))
      return
    }
    if (trimmedName.length < 2) {
      setError(t('auth.nameTooShort', 'Full name must be at least 2 characters.'))
      return
    }
    if (!hasLength || !hasLetter || !hasNumberOrSymbol) {
      setError(t('auth.passwordCriteriaError', 'Password must be at least 8 characters with letters and numbers/symbols.'))
      return
    }
    if (!passwordsMatch) {
      setError(t('auth.passwordMismatch', 'Passwords do not match.'))
      return
    }

    setLoading(true)
    try {
      const data = await signup({
        name: trimmedName,
        email: trimmedEmail,
        password: form.password,
        confirmPassword: form.confirmPassword,
        role: form.role,
        schoolName: form.schoolName?.trim() || '',
        age: form.age ? parseInt(form.age, 10) : undefined,
      })

      if (data.requiresVerification) {
        toast.success(t('auth.verifyNotice', 'Account created! Please check your email for the verification link.'))
      } else {
        toast.success(t('auth.welcome', { name: data.user.name }))
      }

      const role = data.user.role
      navigate(role === 'teacher' ? '/teacher' : role === 'parent' ? '/parent/dashboard' : '/student/screening')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.registerFailed', 'Registration failed. Please check your information.'))
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
          placeholder="At least 8 characters"
          value={form.password}
          onChange={set('password')}
          autoComplete="new-password"
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
        <Input
          label={t('auth.confirmPassword', '🔒 Confirm Password')}
          type={showConfirmPassword ? 'text' : 'password'}
          placeholder="Re-enter your password"
          value={form.confirmPassword}
          onChange={set('confirmPassword')}
          autoComplete="new-password"
          required
          rightAdornment={
            <button
              type="button"
              onClick={() => setShowConfirmPassword((prev) => !prev)}
              className="p-1 text-slate-400 hover:text-slate-600 focus:outline-none focus:text-indigo-600 rounded"
              aria-label={showConfirmPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
              title={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? '👁️' : '🙈'}
            </button>
          }
        />

        {/* Real-time Password Rules Checklist */}
        <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 text-xs space-y-1.5 dyslexia-text">
          <p className="font-bold text-slate-700">Password requirements:</p>
          <div className="grid grid-cols-2 gap-1.5 pt-0.5">
            <span className={hasLength ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
              {hasLength ? '✓' : '○'} At least 8 characters
            </span>
            <span className={hasLetter ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
              {hasLetter ? '✓' : '○'} Includes letters
            </span>
            <span className={hasNumberOrSymbol ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
              {hasNumberOrSymbol ? '✓' : '○'} Numbers or symbols
            </span>
            <span className={passwordsMatch ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
              {passwordsMatch ? '✓' : '○'} Passwords match
            </span>
          </div>
        </div>

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
          disabled={loading}
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

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    const trimmed = email.trim()
    if (!trimmed) {
      setError(t('auth.enterEmail', 'Please enter your account email address.'))
      return
    }

    setLoading(true)
    try {
      await authAPI.forgotPassword({ email: trimmed })
      setSubmitted(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.forgotPasswordFailed', 'Unable to process request. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.forgotPasswordTitle', 'Reset your password 🔐')}
      subtitle={t('auth.forgotPasswordSubtitle', 'Enter your email to receive recovery instructions')}
    >
      {submitted ? (
        <div className="flex flex-col gap-4 text-center py-2">
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center text-2xl mx-auto border border-emerald-200">
            ✉️
          </div>
          <Alert type="success">
            {t(
              'auth.resetInstructionsSent',
              'If an account with that email exists, we have sent password reset instructions. Please check your inbox and spam folder.'
            )}
          </Alert>
          <p className="text-xs text-slate-500 dyslexia-text">
            For security, the password reset link is time-limited and single-use.
          </p>
          <div className="flex flex-col gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setSubmitted(false)
                setEmail('')
              }}
            >
              {t('auth.sendAnother', 'Send another link')}
            </Button>
            <Link
              to="/login"
              className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 hover:underline pt-2 dyslexia-text"
            >
              ← {t('auth.backToSignIn', 'Back to sign in')}
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && <Alert type="error">{error}</Alert>}
          <p className="text-xs text-slate-600 dyslexia-text">
            Enter the email address registered with your DyslexAid account. We will send a secure password reset link.
          </p>
          <Input
            label={t('auth.email', '📧 Email Address')}
            type="email"
            placeholder="your@email.com"
            value={email}
            onChange={(e) => {
              setError('')
              setEmail(e.target.value)
            }}
            autoComplete="email"
            required
          />
          <Button
            type="submit"
            loading={loading}
            disabled={loading}
            size="lg"
            className="w-full mt-2"
          >
            {t('auth.sendResetLink', 'Send Reset Link')} →
          </Button>
          <p className="dyslexia-text text-center text-sm text-slate-600 pt-2">
            <Link to="/login" className="text-indigo-600 font-bold hover:underline">
              ← {t('auth.backToSignIn', 'Back to sign in')}
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  )
}

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const hasLength = password.length >= 8
  const hasLetter = /[A-Za-z]/.test(password)
  const hasNumberOrSymbol = /[\d\W_]/.test(password)
  const passwordsMatch = password.length > 0 && password === confirmPassword

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    setError('')
    if (!token) {
      setError(t('auth.missingToken', 'Missing reset token. Please request a new reset link.'))
      return
    }
    if (!hasLength || !hasLetter || !hasNumberOrSymbol) {
      setError(t('auth.passwordCriteriaError', 'Password must be at least 8 characters with letters and numbers/symbols.'))
      return
    }
    if (!passwordsMatch) {
      setError(t('auth.passwordMismatch', 'Passwords do not match.'))
      return
    }

    setLoading(true)
    try {
      await authAPI.resetPassword({
        token,
        password,
        confirmPassword,
      })
      setSuccess(true)
      toast.success(t('auth.passwordResetSuccess', 'Password reset successfully!'))
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.resetFailed', 'Unable to reset password. The link may have expired.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.setNewPasswordTitle', 'Set New Password 🔑')}
      subtitle={t('auth.setNewPasswordSubtitle', 'Create a strong, secure password for your account')}
    >
      {!token ? (
        <div className="flex flex-col gap-4 text-center py-2">
          <Alert type="error">
            {t('auth.invalidResetLink', 'Invalid or missing password reset link. Please request a new recovery link.')}
          </Alert>
          <Button
            type="button"
            onClick={() => navigate('/forgot-password')}
            className="w-full mt-2"
          >
            {t('auth.goToForgot', 'Request New Reset Link')}
          </Button>
        </div>
      ) : success ? (
        <div className="flex flex-col gap-4 text-center py-2">
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center text-2xl mx-auto border border-emerald-200">
            ✓
          </div>
          <Alert type="success">
            {t('auth.resetCompleteAlert', 'Your password has been reset successfully. You can now sign in with your new password.')}
          </Alert>
          <Button
            type="button"
            onClick={() => navigate('/login')}
            size="lg"
            className="w-full mt-3"
          >
            {t('auth.signInNow', 'Sign In Now')} →
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && <Alert type="error">{error}</Alert>}
          <Input
            label={t('auth.newPassword', '🔑 New Password')}
            type={showPassword ? 'text' : 'password'}
            placeholder="At least 8 characters"
            value={password}
            onChange={(e) => {
              setError('')
              setPassword(e.target.value)
            }}
            autoComplete="new-password"
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
          <Input
            label={t('auth.confirmNewPassword', '🔒 Confirm New Password')}
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="Re-enter new password"
            value={confirmPassword}
            onChange={(e) => {
              setError('')
              setConfirmPassword(e.target.value)
            }}
            autoComplete="new-password"
            required
            rightAdornment={
              <button
                type="button"
                onClick={() => setShowConfirmPassword((prev) => !prev)}
                className="p-1 text-slate-400 hover:text-slate-600 focus:outline-none focus:text-indigo-600 rounded"
                aria-label={showConfirmPassword ? t('auth.hidePassword', 'Hide password') : t('auth.showPassword', 'Show password')}
                title={showConfirmPassword ? 'Hide password' : 'Show password'}
              >
                {showConfirmPassword ? '👁️' : '🙈'}
              </button>
            }
          />

          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 text-xs space-y-1.5 dyslexia-text">
            <p className="font-bold text-slate-700">Password requirements:</p>
            <div className="grid grid-cols-2 gap-1.5 pt-0.5">
              <span className={hasLength ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
                {hasLength ? '✓' : '○'} At least 8 characters
              </span>
              <span className={hasLetter ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
                {hasLetter ? '✓' : '○'} Includes letters
              </span>
              <span className={hasNumberOrSymbol ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
                {hasNumberOrSymbol ? '✓' : '○'} Numbers or symbols
              </span>
              <span className={passwordsMatch ? 'text-emerald-700 font-semibold' : 'text-slate-500'}>
                {passwordsMatch ? '✓' : '○'} Passwords match
              </span>
            </div>
          </div>

          <Button
            type="submit"
            loading={loading}
            disabled={loading}
            size="lg"
            className="w-full mt-2"
          >
            {t('auth.savePassword', 'Save New Password')} →
          </Button>
          <p className="dyslexia-text text-center text-sm text-slate-600 pt-2">
            <Link to="/login" className="text-indigo-600 font-bold hover:underline">
              ← {t('auth.cancelToSignIn', 'Cancel and return to sign in')}
            </Link>
          </p>
        </form>
      )}
    </AuthShell>
  )
}

export function VerifyEmailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [resendEmail, setResendEmail] = useState('')
  const [resendSuccess, setResendSuccess] = useState(false)
  const [resending, setResending] = useState(false)

  const verifyToken = useCallback(async (tok) => {
    setLoading(true)
    setError('')
    try {
      await authAPI.verifyEmail({ token: tok })
      setSuccess(true)
      toast.success(t('auth.emailVerifiedToast', 'Email verified successfully!'))
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.verifyFailed', 'Email verification link is invalid or has expired.'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (token) {
      verifyToken(token)
    }
  }, [token, verifyToken])

  const handleResend = async (e) => {
    if (e) e.preventDefault()
    if (!resendEmail.trim()) return
    setResending(true)
    try {
      await authAPI.resendVerification({ email: resendEmail.trim() })
      setResendSuccess(true)
      toast.success(t('auth.resendSuccessToast', 'Verification link sent if account is pending.'))
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(detail || t('auth.resendFailed', 'Unable to resend verification. Please try again.'))
    } finally {
      setResending(false)
    }
  }

  return (
    <AuthShell
      title={t('auth.verifyEmailTitle', 'Email Verification 📬')}
      subtitle={t('auth.verifyEmailSubtitle', 'Confirming your account email address')}
    >
      <div className="flex flex-col gap-4 text-center py-2">
        {loading ? (
          <div className="py-8 space-y-3">
            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm font-semibold text-slate-700 dyslexia-text">
              {t('auth.verifying', 'Verifying your email address...')}
            </p>
          </div>
        ) : success ? (
          <div className="space-y-4">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center text-2xl mx-auto border border-emerald-200">
              ✓
            </div>
            <Alert type="success">
              {t('auth.emailVerifiedMsg', 'Your email address has been verified successfully. Your account is fully active!')}
            </Alert>
            <Button
              type="button"
              onClick={() => navigate('/login')}
              size="lg"
              className="w-full mt-2"
            >
              {t('auth.continueToSignIn', 'Continue to Sign In')} →
            </Button>
          </div>
        ) : (
          <div className="space-y-4 text-left">
            {error && <Alert type="error">{error}</Alert>}
            {!token && (
              <Alert type="warning">
                {t('auth.noTokenProvided', 'No verification token was found in the link. Please check your email or request a new link below.')}
              </Alert>
            )}

            {resendSuccess ? (
              <Alert type="success">
                {t('auth.resendNotice', 'If the account is pending verification, a new link has been sent.')}
              </Alert>
            ) : (
              <form onSubmit={handleResend} className="space-y-3 pt-2">
                <p className="text-xs text-slate-600 dyslexia-text">
                  Need a new verification link? Enter your email address:
                </p>
                <Input
                  label={t('auth.email', '📧 Email Address')}
                  type="email"
                  placeholder="your@email.com"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  required
                />
                <Button
                  type="submit"
                  loading={resending}
                  disabled={resending || !resendEmail.trim()}
                  className="w-full"
                >
                  {t('auth.resendLinkBtn', 'Resend Verification Email')}
                </Button>
              </form>
            )}

            <div className="text-center pt-2">
              <Link to="/login" className="text-sm font-bold text-indigo-600 hover:underline dyslexia-text">
                ← {t('auth.backToSignIn', 'Back to sign in')}
              </Link>
            </div>
          </div>
        )}
      </div>
    </AuthShell>
  )
}
