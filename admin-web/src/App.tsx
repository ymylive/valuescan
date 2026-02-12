import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Controls } from './pages/Controls'
import { Params } from './pages/Params'
import { Logs } from './pages/Logs'
import { DataSources } from './pages/DataSources'

export const App = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/controls" element={<Controls />} />
          <Route path="/params" element={<Params />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/data-sources" element={<DataSources />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
