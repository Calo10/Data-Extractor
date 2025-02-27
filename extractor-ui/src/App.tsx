import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { DatabaseConfig } from './pages/DatabaseConfig.tsx'
import { QueryExport } from './pages/QueryExport.tsx'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <aside className="sidebar">
        <h1>Database Extractor</h1>
        <nav className="sidebar-nav">
          <Link to="/" className="nav-link">Database Config</Link>
          <Link to="/query" className="nav-link">Query & Export</Link>
        </nav>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<DatabaseConfig />} />
          <Route path="/query" element={<QueryExport />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
