import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Shield, History, MonitorPlay, Video, Menu, X } from 'lucide-react'
import { useJob } from '../context/JobContext'

const linkClass = ({ isActive }) =>
  `flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
    isActive
      ? 'bg-violet-600 text-white'
      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
  }`

const mobileLinkClass = ({ isActive }) =>
  `block px-4 py-3 rounded-lg font-medium transition ${
    isActive
      ? 'bg-violet-600 text-white'
      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
  }`

const NAV_ITEMS = [
  { to: '/analysis/youtube', icon: MonitorPlay, label: 'YouTube' },
  { to: '/analysis/rumble', icon: Video, label: 'Rumble' },
  { to: '/history', icon: History, label: 'History' },
]

export default function Layout({ children }) {
  const { isJobRunning } = useJob()
  const [menuOpen, setMenuOpen] = useState(false)

  const disabledClass = ' opacity-40 pointer-events-none cursor-not-allowed'

  const handleNavClick = () => {
    setMenuOpen(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/analysis/youtube"
            className={`flex items-center gap-2 text-lg font-bold ${isJobRunning ? 'opacity-40 pointer-events-none' : ''}`}
            onClick={handleNavClick}
          >
            <Shield className="text-violet-400" size={22} />
            Marina's Wisdom
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={isJobRunning ? ({ isActive }) => linkClass({ isActive }) + disabledClass : linkClass}
              >
                <Icon size={16} /> {label}
              </NavLink>
            ))}
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen((o) => !o)}
            className="md:hidden p-2 rounded-lg text-gray-300 hover:bg-gray-800 transition"
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile menu dropdown */}
        {menuOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-900 px-4 py-3 space-y-1">
            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={isJobRunning ? ({ isActive }) => mobileLinkClass({ isActive }) + disabledClass : mobileLinkClass}
                onClick={handleNavClick}
              >
                <Icon size={16} className="inline mr-2" />
                {label}
              </NavLink>
            ))}
          </div>
        )}
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}