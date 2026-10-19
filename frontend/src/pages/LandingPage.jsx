import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTranslation } from '../i18n/I18nContext'
import LanguageSelector from '../components/shared/LanguageSelector'
import { Button, Card, Badge } from '../components/ui'

export default function LandingPage() {
  const { user } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const getDashboardPath = () => {
    if (!user) return '/login'
    if (user.role === 'teacher') return '/teacher'
    if (user.role === 'parent') return '/parent/dashboard'
    return '/student'
  }

  return (
    <div
      className="min-h-screen flex flex-col bg-slate-50/70 text-slate-800"
      style={{ backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
    >
      {/* ─── Top Navigation Bar ─────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 sm:h-20 flex items-center justify-between">
          {/* Brand */}
          <Link
            to="/"
            className="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 rounded-xl p-1"
          >
            <div className="w-10 h-10 sm:w-11 sm:h-11 bg-indigo-600 text-white rounded-xl flex items-center justify-center text-xl shadow-xs">
              📖
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="dyslexia-text text-xl sm:text-2xl font-black text-slate-900 tracking-normal">
                  DyslexAid
                </span>
                <span className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-200 px-1.5 py-0.2 rounded-md">
                  V2
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium hidden sm:block">
                Accessible Reading Platform
              </p>
            </div>
          </Link>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-6 text-sm font-semibold text-slate-600 dyslexia-text">
            <a href="#how-it-works" className="hover:text-indigo-600 transition-colors">
              How It Works
            </a>
            <a href="#features" className="hover:text-indigo-600 transition-colors">
              Features
            </a>
            <a href="#for-whom" className="hover:text-indigo-600 transition-colors">
              For Whom
            </a>
            <a href="#accessibility" className="hover:text-indigo-600 transition-colors">
              Accessibility
            </a>
          </nav>

          {/* Top Actions */}
          <div className="hidden sm:flex items-center gap-3">
            <LanguageSelector />
            {user ? (
              <Button onClick={() => navigate(getDashboardPath())} size="md">
                Go to Dashboard →
              </Button>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={() => navigate('/login')}>
                  {t('auth.signIn', 'Sign In')}
                </Button>
                <Button size="sm" onClick={() => navigate('/register')}>
                  {t('auth.getStarted', 'Get Started Free')} →
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex items-center gap-2 sm:hidden">
            <LanguageSelector />
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600"
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? '✕' : '☰'}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="sm:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-5 space-y-3 shadow-md">
            <nav className="flex flex-col gap-2.5 font-semibold text-slate-700 dyslexia-text">
              <a
                href="#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-slate-100"
              >
                How It Works
              </a>
              <a
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-slate-100"
              >
                Features
              </a>
              <a
                href="#for-whom"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-slate-100"
              >
                For Whom
              </a>
              <a
                href="#accessibility"
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg hover:bg-slate-100"
              >
                Accessibility
              </a>
            </nav>
            <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
              {user ? (
                <Button onClick={() => navigate(getDashboardPath())} className="w-full">
                  Go to Dashboard →
                </Button>
              ) : (
                <>
                  <Button variant="outline" onClick={() => navigate('/login')} className="w-full">
                    {t('auth.signIn', 'Sign In')}
                  </Button>
                  <Button onClick={() => navigate('/register')} className="w-full">
                    {t('auth.getStarted', 'Get Started Free')} →
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ─── Hero Section ──────────────────────────────────────────────── */}
      <section className="relative overflow-hidden py-12 sm:py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
            {/* Left Content */}
            <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs sm:text-sm font-bold dyslexia-text shadow-2xs">
                <span>✨ Built for Neurodiverse Learners</span>
                <span className="hidden sm:inline">•</span>
                <span className="hidden sm:inline">WCAG AAA Contrast</span>
              </div>

              <h1 className="dyslexia-text text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 leading-tight">
                Reading with Confidence,{' '}
                <span className="text-indigo-600 underline decoration-indigo-200 decoration-wavy">
                  Learning Without Limits
                </span>
              </h1>

              <p className="dyslexia-text text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto lg:mx-0">
                DyslexAid is an intelligent, multisensory reading companion. Powered by real-time speech feedback,
                personalized pacing, and dyslexia-friendly typography, we empower learners to read with joy and ease.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3.5 pt-2">
                {user ? (
                  <Button onClick={() => navigate(getDashboardPath())} size="lg" className="w-full sm:w-auto">
                    Open Your Dashboard →
                  </Button>
                ) : (
                  <>
                    <Button onClick={() => navigate('/register')} size="lg" className="w-full sm:w-auto">
                      {t('auth.getStarted', 'Get Started Free')} →
                    </Button>
                    <Button variant="outline" onClick={() => navigate('/login')} size="lg" className="w-full sm:w-auto">
                      {t('auth.signIn', 'Sign In')}
                    </Button>
                  </>
                )}
                <a
                  href="#how-it-works"
                  className="text-xs sm:text-sm font-bold text-slate-500 hover:text-indigo-600 transition-colors py-2 px-3 dyslexia-text"
                >
                  See How It Works ↓
                </a>
              </div>

              {/* Trust Indicators */}
              <div className="pt-4 flex flex-wrap items-center justify-center lg:justify-start gap-4 text-xs font-semibold text-slate-500 dyslexia-text">
                <span className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold">✓</span> OpenDyslexic & Lexend Fonts
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold">✓</span> Real-Time Voice Coach
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="text-emerald-600 font-bold">✓</span> EN • मराठी • हिन्दी
                </span>
              </div>
            </div>

            {/* Right Interactive Mockup / Graphic */}
            <div className="lg:col-span-5">
              <Card className="p-5 sm:p-6 shadow-xl border-slate-200/80 bg-white relative">
                {/* Header of Mockup */}
                <div className="flex items-center justify-between pb-3.5 border-b border-slate-100 text-xs font-bold text-slate-500 dyslexia-text">
                  <span className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                    Reading Coach Live
                  </span>
                  <Badge color="indigo">Grade 4 • Oceans</Badge>
                </div>

                {/* Sample Passage with Dyslexia Spacing & Karaoke Highlighting */}
                <div className="py-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-indigo-700 bg-indigo-50/80 px-2.5 py-1 rounded-md">
                    <span>🔊 Text-to-Speech Active</span>
                    <span className="text-slate-400">•</span>
                    <span>Pacing: 110 WPM</span>
                  </div>

                  <p
                    className="dyslexia-text text-base sm:text-lg leading-relaxed text-slate-800"
                    style={{
                      lineHeight: 'var(--line-spacing, 1.8)',
                      letterSpacing: 'var(--letter-spacing, 0.04em)',
                      wordSpacing: 'var(--word-spacing, 0.04em)',
                    }}
                  >
                    The blue whale is the{' '}
                    <span className="bg-amber-200 text-amber-950 font-bold px-1 rounded-sm shadow-2xs">
                      largest
                    </span>{' '}
                    creature ever known to live on planet Earth. Even larger than the biggest dinosaurs!
                  </p>
                </div>

                {/* Mini Stats Ribbon */}
                <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100 text-center">
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-500 font-bold uppercase">Accuracy</p>
                    <p className="text-sm font-extrabold text-emerald-600">96%</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-500 font-bold uppercase">Streak</p>
                    <p className="text-sm font-extrabold text-amber-600">7 Days 🔥</p>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50">
                    <p className="text-[10px] text-slate-500 font-bold uppercase">Level</p>
                    <p className="text-sm font-extrabold text-indigo-600">Explorer</p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* ─── How It Works Section ──────────────────────────────────────── */}
      <section id="how-it-works" className="py-16 sm:py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
            <Badge color="teal" className="mb-3">
              Simple 4-Step Pathway
            </Badge>
            <h2 className="dyslexia-text text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900">
              How DyslexAid Works
            </h2>
            <p className="dyslexia-text text-slate-600 text-base sm:text-lg mt-3">
              From reading hesitation to joyful confidence — designed around each learner&apos;s unique cognitive style.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                icon: '🧠',
                title: 'Screening & Profiling',
                desc: 'A calm, 5-minute self-paced evaluation identifying phonemic strengths, pacing, and visual preferences.',
              },
              {
                step: '02',
                icon: '🎧',
                title: 'Multisensory Practice',
                desc: 'Karaoke word-by-word tracking, syllable chunking, and synchronized natural speech audio.',
              },
              {
                step: '03',
                icon: '🤖',
                title: 'AI Reading Coach',
                desc: 'Real-time gentle voice recognition with encouraging feedback and zero rush or frustration.',
              },
              {
                step: '04',
                icon: '📈',
                title: 'Holistic Growth',
                desc: 'Teachers and parents receive clear, actionable progress summaries to celebrate milestones together.',
              },
            ].map((item) => (
              <Card key={item.step} className="p-6 space-y-3 relative overflow-hidden border-slate-200">
                <span className="text-4xl font-black text-slate-100 absolute top-3 right-4 select-none">
                  {item.step}
                </span>
                <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-2xl">
                  {item.icon}
                </div>
                <h3 className="dyslexia-text text-lg font-bold text-slate-900">{item.title}</h3>
                <p className="dyslexia-text text-sm text-slate-600 leading-relaxed">{item.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Implemented Capabilities / Features ─────────────────────────── */}
      <section id="features" className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
            <Badge color="indigo" className="mb-3">
              Real-World Platform Tools
            </Badge>
            <h2 className="dyslexia-text text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900">
              Everything Needed to Support Every Reader
            </h2>
            <p className="dyslexia-text text-slate-600 text-base sm:text-lg mt-3">
              All tools are built natively into DyslexAid V2 — tested and validated for neurodiverse learning.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
            {[
              {
                icon: '🎙️',
                title: 'Adaptive Reading Coach',
                desc: 'Mic-driven speech analysis identifies hesitant or mispronounced words in real time, adjusting passage difficulty to build confidence.',
                tag: 'AI Speech',
              },
              {
                icon: '💬',
                title: '24/7 AI Tutor Companion',
                desc: 'A patient, non-judgmental conversational tutor available anytime to define difficult words and explain concepts in simple terms.',
                tag: 'Gemini AI',
              },
              {
                icon: '🔤',
                title: 'Dyslexia-First Typography',
                desc: 'OpenDyslexic, Lexend, and Comic Sans fonts with customizable text sizing, letter spacing, word spacing, and reading rulers.',
                tag: 'Accessibility',
              },
              {
                icon: '📸',
                title: 'Handout & Camera Scanner',
                desc: 'Upload or capture textbook photos. Our OCR engine cleans, reformats, and reads school handouts aloud with highlighted tracking.',
                tag: 'OCR Engine',
              },
              {
                icon: '🏆',
                title: 'Streaks & Gamification',
                desc: 'Celebrate effort with daily practice goals, reading badges, and milestones designed to build sustainable reading habits.',
                tag: 'Engagement',
              },
              {
                icon: '🌐',
                title: 'Multilingual Inclusivity',
                desc: 'Full platform translation, speech analysis, and tutor support across English, Marathi (मराठी), and Hindi (हिन्दी).',
                tag: 'Multilingual',
              },
            ].map((f, i) => (
              <Card key={i} className="p-6 space-y-3.5 border-slate-200 hover:border-indigo-300 transition-all">
                <div className="flex items-center justify-between">
                  <span className="text-3xl">{f.icon}</span>
                  <Badge color="gray">{f.tag}</Badge>
                </div>
                <h3 className="dyslexia-text text-lg font-bold text-slate-900">{f.title}</h3>
                <p className="dyslexia-text text-sm text-slate-600 leading-relaxed">{f.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ─── For Whom / Role Value ──────────────────────────────────────── */}
      <section id="for-whom" className="py-16 sm:py-20 bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
            <Badge color="amber" className="mb-3">
              One Unified Ecosystem
            </Badge>
            <h2 className="dyslexia-text text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900">
              Designed for the Entire Learning Community
            </h2>
            <p className="dyslexia-text text-slate-600 text-base sm:text-lg mt-3">
              Each user role gets a dedicated, specialized experience tailored to their goals.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Student Card */}
            <Card className="p-6 sm:p-8 space-y-5 border-2 border-indigo-100 hover:border-indigo-300 transition-all">
              <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center text-3xl">
                🧑‍🎓
              </div>
              <div>
                <h3 className="dyslexia-text text-xl font-bold text-slate-900">For Learners</h3>
                <p className="dyslexia-text text-sm text-slate-500 mt-1">
                  Read without pressure, shame, or visual fatigue.
                </p>
              </div>
              <ul className="space-y-2.5 text-sm text-slate-700 dyslexia-text">
                <li className="flex items-start gap-2">
                  <span className="text-indigo-600 font-bold">✓</span> Visual reading ruler & color tints
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-600 font-bold">✓</span> Personalized library of stories
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-indigo-600 font-bold">✓</span> Encouraging badges and daily rewards
                </li>
              </ul>
              <Button
                variant="outline"
                className="w-full mt-4"
                onClick={() => navigate('/register')}
              >
                Join as Student →
              </Button>
            </Card>

            {/* Teacher Card */}
            <Card className="p-6 sm:p-8 space-y-5 border-2 border-teal-100 hover:border-teal-300 transition-all">
              <div className="w-14 h-14 bg-teal-50 text-teal-600 rounded-2xl flex items-center justify-center text-3xl">
                👩‍🏫
              </div>
              <div>
                <h3 className="dyslexia-text text-xl font-bold text-slate-900">For Teachers</h3>
                <p className="dyslexia-text text-sm text-slate-500 mt-1">
                  Actionable classroom analytics and multi-tier intervention plans.
                </p>
              </div>
              <ul className="space-y-2.5 text-sm text-slate-700 dyslexia-text">
                <li className="flex items-start gap-2">
                  <span className="text-teal-600 font-bold">✓</span> Real-time fluency & phonemic dashboards
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-600 font-bold">✓</span> Curriculum authoring & classroom codes
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-600 font-bold">✓</span> Structured Tier 1–3 intervention tracking
                </li>
              </ul>
              <Button
                variant="outline"
                className="w-full mt-4"
                onClick={() => navigate('/register')}
              >
                Educator Portal →
              </Button>
            </Card>

            {/* Parent Card */}
            <Card className="p-6 sm:p-8 space-y-5 border-2 border-amber-100 hover:border-amber-300 transition-all">
              <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center text-3xl">
                👨‍👩‍👧
              </div>
              <div>
                <h3 className="dyslexia-text text-xl font-bold text-slate-900">For Parents</h3>
                <p className="dyslexia-text text-sm text-slate-500 mt-1">
                  Reassuring home progress summaries with actionable reading tips.
                </p>
              </div>
              <ul className="space-y-2.5 text-sm text-slate-700 dyslexia-text">
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold">✓</span> Clear weekly practice minutes & milestones
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold">✓</span> Evidence-backed tips for home reading support
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-600 font-bold">✓</span> Privacy-preserving learner linking
                </li>
              </ul>
              <Button
                variant="outline"
                className="w-full mt-4"
                onClick={() => navigate('/register')}
              >
                Parent Portal →
              </Button>
            </Card>
          </div>
        </div>
      </section>

      {/* ─── Accessibility Commitment ───────────────────────────────────── */}
      <section id="accessibility" className="py-16 sm:py-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card className="p-8 sm:p-12 bg-indigo-900 text-white rounded-3xl space-y-6 shadow-xl border-none">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-indigo-200 text-xs font-bold dyslexia-text">
              ♿ Accessibility Commitment
            </div>
            <h2 className="dyslexia-text text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white">
              Accessibility by Design, Not as an Afterthought
            </h2>
            <p className="dyslexia-text text-indigo-100 text-base sm:text-lg leading-relaxed">
              Every interface in DyslexAid V2 is engineered in alignment with WCAG 2.1 AAA contrast guidelines,
              supporting OpenDyslexic typography, variable letter and line spacing, high-contrast themes,
              and keyboard-accessible navigation. We build tools that adapt to human variability.
            </p>
            <div className="pt-2 flex flex-wrap gap-3">
              <Link to="/student/accessibility">
                <Button variant="accent">
                  Explore Reading Tools & Settings →
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </section>

      {/* ─── Footer ─────────────────────────────────────────────────────── */}
      <footer className="mt-auto bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-8 border-b border-slate-800">
            {/* Col 1 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-white">
                <span className="text-2xl">📖</span>
                <span className="dyslexia-text text-xl font-black">DyslexAid V2</span>
              </div>
              <p className="dyslexia-text text-xs text-slate-400 leading-relaxed">
                Universal accessible reading platform empowering neurodiverse learners, educators, and families.
              </p>
            </div>

            {/* Col 2 */}
            <div className="space-y-2 text-xs dyslexia-text">
              <p className="font-bold text-white uppercase tracking-wider mb-2">Platform</p>
              <p><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></p>
              <p><a href="#features" className="hover:text-white transition-colors">Features</a></p>
              <p><a href="#for-whom" className="hover:text-white transition-colors">Supported Roles</a></p>
              <p><a href="#accessibility" className="hover:text-white transition-colors">Accessibility Standards</a></p>
            </div>

            {/* Col 3 */}
            <div className="space-y-2 text-xs dyslexia-text">
              <p className="font-bold text-white uppercase tracking-wider mb-2">Access</p>
              <p><Link to="/login" className="hover:text-white transition-colors">Sign In</Link></p>
              <p><Link to="/register" className="hover:text-white transition-colors">Create Account</Link></p>
              <p><Link to="/student" className="hover:text-white transition-colors">Student Portal</Link></p>
              <p><Link to="/teacher" className="hover:text-white transition-colors">Teacher Portal</Link></p>
              <p><Link to="/parent/dashboard" className="hover:text-white transition-colors">Parent Portal</Link></p>
            </div>

            {/* Col 4 */}
            <div className="space-y-3 text-xs dyslexia-text">
              <p className="font-bold text-white uppercase tracking-wider">Language</p>
              <LanguageSelector />
              <p className="text-[11px] text-slate-500 pt-2">
                Supported in English, मराठी, and हिन्दी.
              </p>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 dyslexia-text gap-3">
            <p>© {new Date().getFullYear()} DyslexAid V2. Universal Accessible Learning.</p>
            <p>Designed with WCAG 2.1 AAA Accessibility Standards.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
