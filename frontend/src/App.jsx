import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import { JobProvider } from './context/JobContext'
import YouTubeAnalysisPage from './pages/YouTubeAnalysisPage'
import RumbleAnalysisPage from './pages/RumbleAnalysisPage'
import HistoryPage from './pages/HistoryPage'

function App() {
  return (
    <JobProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/analysis/youtube" replace />} />
        <Route
          path="/analysis/youtube"
          element={<Layout><YouTubeAnalysisPage /></Layout>}
        />
        <Route
          path="/analysis/rumble"
          element={<Layout><RumbleAnalysisPage /></Layout>}
        />
        <Route
          path="/history"
          element={<Layout><HistoryPage /></Layout>}
        />
      </Routes>
    </JobProvider>
  )
}

export default App