import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import { JobProvider } from './context/JobContext'
import YouTubeAnalysisPage from './youtube/YouTubeAnalysisPage'
import RumbleAnalysisPage from './rumble/RumbleAnalysisPage'
import HistoryPage from './history/HistoryPage'
import LoginPage from './auth/LoginPage'
import RegisterPage from './auth/RegisterPage'
import ProtectedRoute from './auth/ProtectedRoute'
import SubscriptionGuard from './auth/SubscriptionGuard'

function App() {
  return (
    <AuthProvider>
      <JobProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<Navigate to="/analysis/rumble" replace />} />
          {/* ProtectedRoute must run BEFORE SubscriptionGuard: the guard assumes an
              authenticated user, and nested the other way round its own /login
              redirect was unreachable (the guard rendered the modal instead). */}
          <Route
            path="/analysis/youtube"
            element={
              <ProtectedRoute>
                <SubscriptionGuard>
                  <YouTubeAnalysisPage />
                </SubscriptionGuard>
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/rumble"
            element={<Layout><RumbleAnalysisPage /></Layout>}
          />
          <Route
            path="/history"
            element={<Layout><HistoryPage /></Layout>}
          />
          {/* Unknown paths land on the free Rumble page rather than a blank screen. */}
          <Route path="*" element={<Navigate to="/analysis/rumble" replace />} />
        </Routes>
      </JobProvider>
    </AuthProvider>
  )
}

export default App