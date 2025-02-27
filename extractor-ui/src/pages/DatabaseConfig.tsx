import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

interface DbConfig {
  db_type: string
  host: string
  port: string
  database: string
  user: string
  password: string
}

const DB_PORTS = {
  postgresql: "5432",
  mysql: "3306",
  sqlserver: "1433"
}

export function DatabaseConfig() {
  const navigate = useNavigate()
  const [selectedDbType, setSelectedDbType] = useState('postgresql')

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const dbConfig: DbConfig = {
      db_type: formData.get('db_type') as string,
      host: formData.get('host') as string,
      port: formData.get('port') as string,
      database: formData.get('database') as string,
      user: formData.get('user') as string,
      password: formData.get('password') as string,
    }

    localStorage.setItem('dbConfig', JSON.stringify(dbConfig))
    navigate('/spark')
  }

  return (
    <div className="container">
      <div className="page-header">
        <h2>Database Configuration</h2>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="form-header">
          <h3>Connection Details</h3>
        </div>

        <div className="form-body">
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="db_type">Database Type</label>
              <select 
                id="db_type" 
                name="db_type" 
                required 
                defaultValue="postgresql"
                onChange={(e) => setSelectedDbType(e.target.value)}
              >
                <option value="postgresql">PostgreSQL</option>
                <option value="mysql">MySQL</option>
                <option value="sqlserver">SQL Server</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="host">Host</label>
              <input type="text" id="host" name="host" defaultValue="localhost" required />
            </div>

            <div className="form-group">
              <label htmlFor="port">Port</label>
              <select
                id="port"
                name="port"
                required
                value={DB_PORTS[selectedDbType as keyof typeof DB_PORTS]}
              >
                <option value="5432">5432 (PostgreSQL)</option>
                <option value="3306">3306 (MySQL)</option>
                <option value="1433">1433 (SQL Server)</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="database">Database Name</label>
              <input type="text" id="database" name="database" required />
            </div>

            <div className="form-group">
              <label htmlFor="user">Username</label>
              <input type="text" id="user" name="user" required />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input type="password" id="password" name="password" required />
            </div>
          </div>
        </div>

        <div className="form-footer">
          <button type="submit" className="generate-btn">
            Next: Query & Export
          </button>
        </div>
      </form>
    </div>
  )
} 