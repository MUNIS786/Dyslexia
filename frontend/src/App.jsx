import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'
import { NotifProvider } from './context/NotifContext'
import { I18nProvider } from './i18n/I18nContext'
import { AccessibilityProvider } from './context/AccessibilityContext'
import { LoadingScreen } from './components/ui'
import { useSession } from './hooks/useSession'
import Layout from './components/shared/Layout'

// Eagerly loaded auth entrypoints
import { LoginPage, RegisterPage } from './pages/auth/AuthPages'

// Code-split route pages (Phase 17 bundle optimization)
const StudentHome = lazy(() => import('./pages/student/StudentHome'))
const StudentProfilePage = lazy(() => import('./pages/student/StudentProfilePage'))
const AdaptiveLearningPage = lazy(() => import('./pages/student/AdaptiveLearningPage'))
const ReadingCoachPage = lazy(() => import('./pages/student/ReadingCoachPage'))
const LearningInsightsPage = lazy(() => import('./pages/student/LearningInsightsPage'))
const LearningRecommendationsPage = lazy(() => import('./pages/student/LearningRecommendationsPage'))
const PersonalizedActivityPage = lazy(() => import('./pages/student/PersonalizedActivityPage'))
const TutorPage = lazy(() => import('./pages/student/TutorPage'))
const RewardsPage = lazy(() => import('./pages/student/RewardsPage'))
const ScreeningTest = lazy(() => import('./pages/student/ScreeningTest'))
const DailyTasks = lazy(() => import('./pages/student/DailyTasks'))
const ScanPage = lazy(() => import('./pages/student/ScanPage'))
const LibraryPage = lazy(() => import('./pages/student/LibraryPage'))
const LibraryDocPage = lazy(() => import('./pages/student/LibraryDocPage'))
const ProgressPage = lazy(() => import('./pages/student/ProgressPage'))
const PlanPage = lazy(() => import('./pages/student/PlanPage'))
const ChatPage = lazy(() => import('./pages/student/ChatPage'))
const SettingsPage = lazy(() => import('./pages/student/SettingsPage'))
const AccessibilitySettingsPage = lazy(() => import('./pages/student/AccessibilitySettingsPage'))
const JoinClassroom = lazy(() => import('./pages/student/JoinClassroom'))

const TeacherHome = lazy(() => import('./pages/teacher/TeacherHome'))
const StudentsPage = lazy(() => import('./pages/teacher/StudentsPage'))
const StudentDetailPage = lazy(() => import('./pages/teacher/StudentDetailPage'))
const AssignmentsPage = lazy(() => import('./pages/teacher/AssignmentsPage'))
const TeacherScanPage = lazy(() => import('./pages/teacher/TeacherScanPage'))
const TeacherAnalyticsPage = lazy(() => import('./pages/teacher/TeacherAnalyticsPage'))
const InterventionsPage = lazy(() => import('./pages/teacher/InterventionsPage'))
const ContentAuthoringPage = lazy(() => import('./pages/teacher/ContentAuthoringPage'))

const ParentDashboardPage = lazy(() => import('./pages/parent/ParentDashboardPage'))

function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) {
    return <Navigate to={user.role === 'teacher' ? '/teacher' : user.role === 'parent' ? '/parent/dashboard' : '/student'} replace />
  }
  if (
    user.role === 'student' &&
    !user.readingProfile &&
    !window.location.pathname.includes('screening') &&
    !window.location.pathname.includes('profile') &&
    !window.location.pathname.includes('adaptive-learning') &&
    !window.location.pathname.includes('reading-coach') &&
    !window.location.pathname.includes('insights') &&
    !window.location.pathname.includes('recommendations') &&
    !window.location.pathname.includes('activity') &&
    !window.location.pathname.includes('personalized-content') &&
    !window.location.pathname.includes('tutor') &&
    !window.location.pathname.includes('accessibility') &&
    !window.location.pathname.includes('settings')
  ) {
    return <Navigate to="/student/screening" replace />
  }
  return children
}

function AppRoutes() {
  useSession()
  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route path="/student" element={
          <ProtectedRoute role="student"><Layout><StudentHome /></Layout></ProtectedRoute>
        } />
        <Route path="/student/profile" element={
          <ProtectedRoute role="student"><Layout><StudentProfilePage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/adaptive-learning" element={
          <ProtectedRoute role="student"><Layout><AdaptiveLearningPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/reading-coach" element={
          <ProtectedRoute role="student"><Layout><ReadingCoachPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/insights" element={
          <ProtectedRoute role="student"><Layout><LearningInsightsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/recommendations" element={
          <ProtectedRoute role="student"><Layout><LearningRecommendationsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/activity" element={
          <ProtectedRoute role="student"><Layout><PersonalizedActivityPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/personalized-content" element={
          <ProtectedRoute role="student"><Layout><PersonalizedActivityPage /></Layout></ProtectedRoute>
        } />
        <Route path="/student/tutor" element={
          <ProtectedRoute role="student"><Layout><TutorPage /></Layout></ProtectedRoute>
        } />

        <Route path="/student/screening" element={
          <ProtectedRoute role="student"><ScreeningTest /></ProtectedRoute>
        } />
        <Route path="/student/tasks" element={
          <ProtectedRoute role="student"><Layout><DailyTasks /></Layout></ProtectedRoute>
        } />
        <Route path="/student/rewards" element={
          <ProtectedRoute role="student"><Layout><RewardsPage /></Layout></ProtectedRoute>
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
        <Route path="/student/accessibility" element={
          <ProtectedRoute role="student"><Layout><AccessibilitySettingsPage /></Layout></ProtectedRoute>
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
        <Route path="/teacher/analytics" element={
          <ProtectedRoute role="teacher"><Layout><TeacherAnalyticsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/teacher/interventions" element={
          <ProtectedRoute role="teacher"><Layout><InterventionsPage /></Layout></ProtectedRoute>
        } />
        <Route path="/teacher/content" element={
          <ProtectedRoute role="teacher"><Layout><ContentAuthoringPage /></Layout></ProtectedRoute>
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

        <Route path="/parent" element={<Navigate to="/parent/dashboard" replace />} />
        <Route path="/parent/dashboard" element={
          <ProtectedRoute role="parent"><Layout><ParentDashboardPage /></Layout></ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <I18nProvider>
          <AccessibilityProvider>
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
          </AccessibilityProvider>
        </I18nProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
