import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTranslation } from '../../i18n/I18nContext'
import LanguageSelector from '../../components/shared/LanguageSelector'
import { authAPI } from '../../api/client'
import { Button, Input, Select, Alert } from '../../components/ui'
import toast from 'react-hot-toast'

function AuthShell({ children, title, subtitle }) {
  const { t } = useTranslation()
  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative"
      style={{ backgroundColor: 'var(--bg-color)' }}
    >
      {/* Top right language selector */}
      <div className="absolute top-4 right-4 z-20">
        <LanguageSelector />
      </div>

      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-[#1A6B6B] rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-lg">
            📖
          </div>
          <h1 className="dyslexia-text text-3xl font-bold text-[#1A6B6B]">DyslexAid</h1>
          <p className="dyslexia-text text-gray-500 mt-1">{t('auth.tagline', 'Reading companion for every student')}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-md border border-[#E5E0D8] p-6">
          <h2 className="dyslexia-text text-xl font-bold mb-1">{title}</h2>
          <p className="dyslexia-text text-gray-500 text-sm mb-6">{subtitle}</p>
          {children}
        </div>
      </div>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async () => {
    setError('')
    if (!form.email || !form.password) {
      setError(t('auth.fillAllFields', 'Please fill in all fields.'))
      return
    }
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      toast.success(t('auth.welcomeBack', { name: user.name }))
      navigate(user.role === 'teacher' ? '/teacher' : '/student')
    } catch (err) {
      setError(err.response?.data?.detail || t('auth.loginFailed', 'Login failed. Check your details.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell title={t('auth.loginTitle', 'Welcome back 👋')} subtitle={t('auth.loginSubtitle', 'Sign in to continue learning')}>
      <div className="flex flex-col gap-4">
        {error && <Alert type="error">{error}</Alert>}
        <Input
          label={t('auth.email', '📧 Email')}
          type="email"
          placeholder="your@email.com"
          value={form.email}
          onChange={set('email')}
          autoComplete="email"
        />
        <Input
          label={t('auth.password', '🔑 Password')}
          type="password"
          placeholder="Your password"
          value={form.password}
          onChange={set('password')}
          autoComplete="current-password"
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        />
        <Button onClick={handleSubmit} loading={loading} size="lg" className="w-full mt-2">
          {t('auth.signIn', 'Sign In')}
        </Button>
        <p className="dyslexia-text text-center text-sm text-gray-500">
          {t('auth.newUser', 'New user?')}{' '}
          <Link to="/register" className="text-[#1A6B6B] font-semibold hover:underline">
            {t('auth.createAccount', 'Create account')}
          </Link>
        </p>
      </div>
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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async () => {
    setError('')
    if (!form.name || !form.email || !form.password) {
      setError(t('auth.fillAllFields', 'Please fill in all required fields.'))
      return
    }
    setLoading(true)
    try {
      const data = await authAPI.signup({
        ...form,
        age: form.age ? parseInt(form.age) : undefined,
      })
      localStorage.setItem('dyslexaid_token', data.token)
      await login(form.email, form.password)
      toast.success(t('auth.welcome', { name: data.user.name }))
      navigate(data.user.role === 'teacher' ? '/teacher' : '/student/screening')
    } catch (err) {
      setError(err.response?.data?.detail || t('auth.registerFailed', 'Registration failed. Try a different email.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell title={t('auth.registerTitle', 'Create your account ✨')} subtitle={t('auth.registerSubtitle', 'Join thousands of learners today')}>
      <div className="flex flex-col gap-4">
        {error && <Alert type="error">{error}</Alert>}
        <Input
          label={t('auth.fullName', '👤 Full Name')}
          placeholder="Your full name"
          value={form.name}
          onChange={set('name')}
        />
        <Input
          label={t('auth.email', '📧 Email')}
          type="email"
          placeholder="your@email.com"
          value={form.email}
          onChange={set('email')}
        />
        <Input
          label={t('auth.password', '🔑 Password')}
          type="password"
          placeholder="Choose a strong password"
          value={form.password}
          onChange={set('password')}
        />
        <Select
          label={t('auth.role', '👔 I am a...')}
          value={form.role}
          onChange={set('role')}
          options={[
            { value: 'student', label: t('auth.student', '🧑‍🎓 Student') },
            { value: 'teacher', label: t('auth.teacher', '👩‍🏫 Teacher') },
          ]}
        />
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
        <Button onClick={handleSubmit} loading={loading} size="lg" className="w-full mt-2">
          {t('auth.createAccount', 'Create Account')}
        </Button>
        <p className="dyslexia-text text-center text-sm text-gray-500">
          {t('auth.haveAccount', 'Already have an account?')}{' '}
          <Link to="/login" className="text-[#1A6B6B] font-semibold hover:underline">
            {t('auth.signIn', 'Sign in')}
          </Link>
        </p>
      </div>
    </AuthShell>
  )
}
