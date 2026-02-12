import { Link, useLocation } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'

export const Layout = ({ children }: { children: React.ReactNode }) => {
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  const isDark = theme === 'day'
  const bg = isDark ? 'bg-black' : 'bg-white'
  const text = isDark ? 'text-white' : 'text-black'
  const border = isDark ? 'border-white/20' : 'border-black/20'
  const hover = isDark ? 'hover:bg-white/10' : 'hover:bg-black/10'

  const links = [
    { path: '/', label: 'Dashboard' },
    { path: '/controls', label: 'Controls' },
    { path: '/params', label: 'Params' },
    { path: '/logs', label: 'Logs' },
    { path: '/data-sources', label: 'Data Sources' }
  ]

  return (
    <div className={`min-h-screen ${bg} ${text} font-mono`}>
      <nav className={`border-b ${border} px-6 py-4`}>
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-bold">ValuScan Admin</h1>
            <div className="flex gap-1">
              {links.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-4 py-2 border ${border} ${hover} transition-colors ${
                    location.pathname === link.path ? (isDark ? 'bg-white/20' : 'bg-black/20') : ''
                  }`}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
          <button
            onClick={toggleTheme}
            className={`px-4 py-2 border ${border} ${hover} transition-colors`}
          >
            {theme === 'day' ? '☀' : '☾'}
          </button>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}
