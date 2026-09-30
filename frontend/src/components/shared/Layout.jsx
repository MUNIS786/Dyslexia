import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useNotifs } from '../../context/NotifContext'

const STUDENT_NAV = [
  { to: '/student', label: 'Home', icon: '🏠', end: true },
  { to: '/student/profile', label: 'Learning Profile', icon: '🌟' },
  { to: '/student/adaptive-learning', label: 'Adaptive Practice', icon: '🎯' },
  { to: '/student/reading-coach', label: 'Reading Coach', icon: '📖' },
  { to: '/student/tutor', label: 'AI Tutor', icon: '🤖' },
  { to: '/student/tasks', label: 'Daily Tasks', icon: '✅' },
  { to: '/student/scan', label: 'Scan Text', icon: '📷' },
  { to: '/student/library', label: 'My Library', icon: '📚' },
  { to: '/student/progress', label: 'Progress', icon: '📊' },
  { to: '/student/plan', label: 'My Plan', icon: '🧠' },
  { to: '/student/chat', label: 'AI Chat', icon: '💬' },
  { to: '/student/classroom', label: 'Classroom', icon: '🏫' },
  { to: '/student/settings', label: 'Settings', icon: '⚙️' },
]

const TEACHER_NAV = [
  { to: '/teacher', label: 'Dashboard', icon: '📊', end: true },
  { to: '/teacher/students', label: 'Students', icon: '👥' },
  { to: '/teacher/assignments', label: 'Assignments', icon: '📝' },
  { to: '/teacher/scan', label: 'Scan & Convert', icon: '📷' },
  { to: '/teacher/chat', label: 'AI Chat', icon: '💬' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { unread } = useNotifs()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const { notifs, markAllRead } = useNotifs()

  const nav = user?.role === 'teacher' ? TEACHER_NAV : STUDENT_NAV

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: 'var(--bg-color)' }}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full z-30 w-64 bg-[#1A6B6B] flex flex-col
          sidebar-transition transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:static lg:flex`}
      >
        {/* Logo */}
        <div className="p-5 border-b border-white/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#E8A020] rounded-xl flex items-center justify-center text-xl">
              📖
            </div>
            <div>
              <p className="text-white font-bold text-lg leading-tight">DyslexAid</p>
              <p className="text-white/60 text-xs capitalize">{user?.role}</p>
            </div>
          </div>
        </div>

        {/* User info */}
        <div className="px-4 py-3 border-b border-white/20">
          <p className="text-white/80 text-sm">Hello,</p>
          <p className="text-white font-semibold truncate">{user?.name}</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl mb-1 transition-all text-sm font-medium
                ${isActive
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-white/20">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-white/70
              hover:bg-white/10 hover:text-white transition-all text-sm font-medium"
          >
            <span>🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-[#E5E0D8] px-4 py-3 flex items-center justify-between gap-3">
          <button
            className="lg:hidden w-10 h-10 flex items-center justify-center rounded-xl hover:bg-gray-100"
            onClick={() => setSidebarOpen(true)}
          >
            ☰
          </button>
          <div className="flex-1" />
          {/* Notification bell */}
          <div className="relative">
            <button
              onClick={() => setNotifOpen((o) => !o)}
              className="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-gray-100 relative"
            >
              🔔
              {unread > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-12 w-80 bg-white rounded-2xl shadow-xl border border-[#E5E0D8] overflow-hidden z-50">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E0D8]">
                  <span className="font-bold dyslexia-text">Notifications</span>
                  <button
                    onClick={markAllRead}
                    className="text-xs text-[#1A6B6B] font-semibold hover:underline"
                  >
                    Mark all read
                  </button>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifs.length === 0 ? (
                    <div className="p-6 text-center text-gray-400 text-sm">No notifications</div>
                  ) : (
                    notifs.slice(0, 20).map((n) => (
                      <div
                        key={n.id}
                        className={`px-4 py-3 border-b border-[#E5E0D8] last:border-0 ${!n.read ? 'bg-[#E0F2F2]' : ''}`}
                      >
                        <p className="dyslexia-text text-sm font-semibold">{n.title}</p>
                        <p className="dyslexia-text text-xs text-gray-500">{n.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-5 max-w-4xl mx-auto w-full">{children}</main>
      </div>
    </div>
  )
}
