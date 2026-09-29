import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'
import { NotifProvider } from './context/NotifContext'
import { LoadingScreen } from './components/ui'
import { useSession } from './hooks/useSession'

import { LoginPage, RegisterPage } from './pages/auth/AuthPages'
import StudentHome from './pages/student/StudentHome'
import StudentProfilePage from './pages/student/StudentProfilePage'
import ScreeningTest from './pages/student/ScreeningTest'
import DailyTasks from './pages/student/DailyTasks'
import ScanPage from './pages/student/ScanPage'
import LibraryPage from './pages/student/LibraryPage'
import LibraryDocPage from './pages/student/LibraryDocPage'
import ProgressPage from './pages/student/ProgressPage'
import PlanPage from './pages/student/PlanPage'
import ChatPage from './pages/student/ChatPage'
import SettingsPage from './pages/student/SettingsPage'
import JoinClassroom from './pages/student/JoinClassroom'
import TeacherHome from './pages/teacher/TeacherHome'
import StudentsPage from './pages/teacher/StudentsPage'
import StudentDetailPage from './pages/teacher/StudentDetailPage'
import AssignmentsPage from './pages/teacher/AssignmentsPage'
import TeacherScanPage from './pages/teacher/TeacherScanPage'
import Layout from './components/shared/Layout'

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) {
    return <Navigate to={user.role === 'teacher' ? '/teacher' : '/student'} replace />
  }
  if (
    user.role === 'student' &&
    !user.readingProfile &&
    !window.location.pathname.includes('screening') &&
    !window.location.pathname.includes('profile')
  ) {
    return <Navigate to="/student/screening" replace />
  }
  return children
}

function AppRoutes() {
  useSession()
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route path="/student" element={
        <ProtectedRoute role="student"><Layout><StudentHome /></Layout></ProtectedRoute>
      } />
      <Route path="/student/profile" element={
        <ProtectedRoute role="student"><Layout><StudentProfilePage /></Layout></ProtectedRoute>
      } />

      <Route path="/student/screening" element={
        <ProtectedRoute role="student"><ScreeningTest /></ProtectedRoute>
      } />
      <Route path="/student/tasks" element={
        <ProtectedRoute role="student"><Layout><DailyTasks /></Layout></ProtectedRoute>
      } />
      <Route path="/student/scan" element={
        <ProtectedRoute role="student"><Layout><ScanPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/library" element={
        <ProtectedRoute role="student"><Layout><LibraryPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/library/:id" element={
        <ProtectedRoute role="student"><Layout><LibraryDocPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/progress" element={
        <ProtectedRoute role="student"><Layout><ProgressPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/plan" element={
        <ProtectedRoute role="student"><Layout><PlanPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/chat" element={
        <ProtectedRoute role="student"><Layout><ChatPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/settings" element={
        <ProtectedRoute role="student"><Layout><SettingsPage /></Layout></ProtectedRoute>
      } />
      <Route path="/student/classroom" element={
        <ProtectedRoute role="student"><Layout><JoinClassroom /></Layout></ProtectedRoute>
      } />

      <Route path="/teacher" element={
        <ProtectedRoute role="teacher"><Layout><TeacherHome /></Layout></ProtectedRoute>
      } />
      <Route path="/teacher/students" element={
        <ProtectedRoute role="teacher"><Layout><StudentsPage /></Layout></ProtectedRoute>
      } />
      <Route path="/teacher/students/:id" element={
        <ProtectedRoute role="teacher"><Layout><StudentDetailPage /></Layout></ProtectedRoute>
      } />
      <Route path="/teacher/assignments" element={
        <ProtectedRoute role="teacher"><Layout><AssignmentsPage /></Layout></ProtectedRoute>
      } />
      <Route path="/teacher/scan" element={
        <ProtectedRoute role="teacher"><Layout><TeacherScanPage /></Layout></ProtectedRoute>
      } />
      <Route path="/teacher/chat" element={
        <ProtectedRoute role="teacher"><Layout><ChatPage /></Layout></ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotifProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                fontFamily: 'var(--font-family)',
                fontSize: '1rem',
              },
            }}
          />
          <AppRoutes />
        </NotifProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
