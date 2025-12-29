import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Toaster } from 'sonner'
import { MinimalSettingsPage } from './pages/MinimalSettingsPage'
import './styles/minimal.css'

function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#000000' }}>
        {/* Header */}
        <header
          style={{
            borderBottom: '1px solid #1A1A1A',
            padding: '1rem 2rem',
          }}
        >
          <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
            <h1
              style={{
                color: '#FFFFFF',
                fontSize: '1.25rem',
                fontWeight: 600,
                letterSpacing: '0.05em',
              }}
            >
              VALUESCAN
            </h1>
          </div>
        </header>

        {/* Main Content */}
        <main>
          <Routes>
            <Route path="/" element={<MinimalSettingsPage />} />
            <Route path="/settings" element={<MinimalSettingsPage />} />
          </Routes>
        </main>

        {/* Toast Notifications */}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#0A0A0A',
              color: '#FFFFFF',
              border: '1px solid #1A1A1A',
            },
          }}
        />
      </div>
    </BrowserRouter>
  )
}

export default App
