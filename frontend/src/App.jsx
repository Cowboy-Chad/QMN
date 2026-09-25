import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import { JobProvider } from './context/JobContext'
import YouTubeAnalysisPage from './youtube/YouTubeAnalysisPage'
import RumbleAnalysisPage from './rumble/RumbleAnalysisPage'
import HistoryPage from './history/HistoryPage'

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