import { useState, useEffect, useRef } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useNotifs } from '../../context/NotifContext'
import { useTranslation } from '../../i18n/I18nContext'
import LanguageSelector from './LanguageSelector'
import { AccessibilityToolbar, ReadingRuler, VisualTintOverlay } from '../accessibility'

const STUDENT_NAV = [
  { to: '/student', label: 'Home', i18nKey: 'nav.home', icon: '🏠', end: true },
  { to: '/student/profile', label: 'Learning Profile', i18nKey: 'nav.profile', icon: '🌟' },
  { to: '/student/adaptive-learning', label: 'Adaptive Practice', i18nKey: 'nav.adaptivePractice', icon: '🎯' },
  { to: '/student/reading-coach', label: 'Reading Coach', i18nKey: 'nav.readingCoach', icon: '📖' },
  { to: '/student/insights', label: 'Learning Insights', i18nKey: 'nav.insights', icon: '📈' },
  { to: '/student/recommendations', label: 'Next Steps & Plan', i18nKey: 'nav.recommendations', icon: '🧭' },
  { to: '/student/activity', label: 'Personalized Activities', i18nKey: 'nav.personalizedContent', icon: '✨' },
  { to: '/student/tutor', label: 'AI Tutor', i18nKey: 'nav.tutor', icon: '🤖' },
  { to: '/student/tasks', label: 'Daily Tasks', i18nKey: 'nav.tasks', icon: '✅' },
  { to: '/student/rewards', label: 'Rewards', i18nKey: 'nav.rewards', icon: '🏆' },
  { to: '/student/scan', label: 'Scan Text', i18nKey: 'nav.scan', icon: '📷' },
  { to: '/student/library', label: 'My Library', i18nKey: 'nav.library', icon: '📚' },
  { to: '/student/progress', label: 'Progress', i18nKey: 'nav.progress', icon: '📊' },
  { to: '/student/plan', label: 'My Plan', i18nKey: 'nav.plan', icon: '🧠' },
  { to: '/student/chat', label: 'AI Chat', i18nKey: 'nav.chat', icon: '💬' },
  { to: '/student/classroom', label: 'Classroom', i18nKey: 'nav.classroom', icon: '🏫' },
  { to: '/student/accessibility', label: 'Reading Tools', i18nKey: 'nav.accessibility', icon: '👓' },
  { to: '/student/settings', label: 'Settings', i18nKey: 'nav.settings', icon: '⚙️' },
]

const TEACHER_NAV = [
  { to: '/teacher', label: 'Dashboard', i18nKey: 'nav.dashboard', icon: '📊', end: true },
  { to: '/teacher/analytics', label: 'Class Analytics', i18nKey: 'nav.classAnalytics', icon: '📈' },
  { to: '/teacher/interventions', label: 'Interventions', i18nKey: 'nav.interventions', icon: '🎯' },
  { to: '/teacher/content', label: 'Content Authoring', i18nKey: 'nav.contentAuthoring', icon: '✍️' },
  { to: '/teacher/students', label: 'Students', i18nKey: 'nav.students', icon: '👥' },
  { to: '/teacher/assignments', label: 'Assignments', i18nKey: 'nav.assignments', icon: '📝' },
  { to: '/teacher/scan', label: 'Scan & Convert', i18nKey: 'nav.scanConvert', icon: '📷' },
  { to: '/teacher/chat', label: 'AI Chat', i18nKey: 'nav.chat', icon: '💬' },
]

const PARENT_NAV = [
  { to: '/parent/dashboard', label: 'Parent Portal', i18nKey: 'nav.parentPortal', icon: '👨‍👩‍👧', end: true },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { unread, notifs, markAllRead } = useNotifs()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const notifRef = useRef(null)
  const mobileToggleRef = useRef(null)

  const nav =
    user?.role === 'teacher' ? TEACHER_NAV : user?.role === 'parent' ? PARENT_NAV : STUDENT_NAV

  const roleLabels = {
    student: { title: 'Learner', badge: 'bg-amber-50 text-amber-800 border-amber-200' },
    teacher: { title: 'Educator', badge: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
    parent: { title: 'Guardian', badge: 'bg-teal-50 text-teal-800 border-teal-200' },
  }
  const currentRole = roleLabels[user?.role] || { title: 'User', badge: 'bg-slate-100 text-slate-700 border-slate-200' }

  // Close menus on route change
  useEffect(() => {
    setSidebarOpen(false)
    setNotifOpen(false)
  }, [location.pathname])

  // Handle escape key to close menus & outside click
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (sidebarOpen) {
          setSidebarOpen(false)
          mobileToggleRef.current?.focus()
        }
        if (notifOpen) {
          setNotifOpen(false)
        }
      }
    }
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [sidebarOpen, notifOpen])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg-color,#F8FAFC)] text-[var(--text-color,#1E293B)]">
      {/* Skip to Main Content Link for Keyboard Access */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Accessibility Focus Tools & Visual Stress Tints */}
      <ReadingRuler />
      <VisualTintOverlay />

      {/* Mobile Drawer Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        id="app-sidebar"
        aria-label="Main Navigation"
        className={`fixed top-0 left-0 h-full z-50 w-64 bg-white border-r border-slate-200 flex flex-col shadow-sm
          sidebar-transition transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:static lg:flex`}
      >
        {/* Brand Header */}
        <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-xl text-white shadow-sm shrink-0">
              📖
            </div>
            <div>
              <p className="font-extrabold text-slate-900 text-lg leading-tight tracking-tight">
                DyslexAid <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded-md">V2</span>
              </p>
              <span
                className={`inline-block mt-0.5 text-[11px] font-bold px-2 py-0.5 rounded-full border ${currentRole.badge}`}
              >
                {currentRole.title}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="lg:hidden p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-700"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation sidebar"
          >
            ✕
          </button>
        </div>

        {/* User Card */}
        <div className="px-4 py-3 mx-3 my-2 rounded-xl bg-slate-50 border border-slate-100 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 font-bold text-sm flex items-center justify-center shrink-0">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">{t('common.hello', 'Hello')}</p>
            <p className="text-sm font-bold text-slate-800 truncate">{user?.name || 'Friend'}</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 group
                ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700 shadow-sm border-l-4 border-indigo-600 pl-2.5'
                    : 'text-slate-600 hover:text-indigo-600 hover:bg-slate-50'
                }`
              }
            >
              <span className="text-lg shrink-0 transition-transform group-hover:scale-110">{item.icon}</span>
              <span className="truncate">{t(item.i18nKey, item.label)}</span>
            </NavLink>
          ))}
        </nav>

        {/* Logout Footer */}
        <div className="p-3 border-t border-slate-100">
          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-600
              hover:bg-rose-50 hover:text-rose-600 transition-colors text-sm font-semibold"
          >
            <span className="text-lg shrink-0">🚪</span>
            <span>{t('common.logout', 'Logout')}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 shadow-xs">
          {/* Mobile hamburger button */}
          <button
            ref={mobileToggleRef}
            type="button"
            className="lg:hidden w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-700 transition-colors"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label="Toggle navigation menu"
            aria-expanded={sidebarOpen}
            aria-controls="app-sidebar"
          >
            <span className="text-xl">☰</span>
          </button>

          <div className="flex-1" />

          {/* Quick Accessibility & Reading Tools */}
          <AccessibilityToolbar />

          {/* Language Selector */}
          <LanguageSelector />

          {/* Notification Bell */}
          <div className="relative" ref={notifRef}>
            <button
              type="button"
              onClick={() => setNotifOpen((o) => !o)}
              className="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-700 transition-colors relative"
              aria-label={`Notifications ${unread > 0 ? `(${unread} unread)` : ''}`}
              aria-expanded={notifOpen}
            >
              <span className="text-xl" aria-hidden="true">🔔</span>
              {unread > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-rose-600 text-white text-[11px] rounded-full flex items-center justify-center font-bold shadow-xs">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>

            {notifOpen && (
              <div
                role="region"
                aria-label="Notification Center"
                className="absolute right-0 top-12 w-80 sm:w-96 bg-white rounded-2xl shadow-modal border border-slate-200 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/70">
                  <span className="font-bold text-sm text-slate-800 dyslexia-text">
                    {t('common.notifications', 'Notifications')}
                  </span>
                  {unread > 0 && (
                    <button
                      type="button"
                      onClick={markAllRead}
                      className="text-xs text-indigo-600 font-bold hover:text-indigo-800 hover:underline transition-colors"
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                  {notifs.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 text-sm dyslexia-text">
                      No notifications right now
                    </div>
                  ) : (
                    notifs.slice(0, 20).map((n) => (
                      <div
                        key={n.id}
                        className={`px-4 py-3 transition-colors ${
                          !n.read ? 'bg-indigo-50/50' : 'hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <p className="dyslexia-text text-sm font-bold text-slate-800">{n.title}</p>
                          {!n.read && (
                            <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0 mt-1.5" aria-hidden="true" />
                          )}
                        </div>
                        <p className="dyslexia-text text-xs text-slate-500 mt-0.5 leading-relaxed">{n.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page Content Viewport */}
        <main
          id="main-content"
          tabIndex="-1"
          className="flex-1 p-4 sm:p-6 lg:p-8 mx-auto w-full transition-[max-width] duration-150 outline-none"
          style={{ maxWidth: 'var(--reading-max-width, 56rem)' }}
        >
          {children}
        </main>
      </div>
    </div>
  )
}

