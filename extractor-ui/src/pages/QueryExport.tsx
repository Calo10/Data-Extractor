import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_BASE_URL = 'http://0.0.0.0:8000'

interface ExportData {
  query: string
  output_filename: string
  output_format: string
  db_config: {
    db_type: string
    host: string
    port: string
    database: string
    user: string
    password: string
  }
}

export function QueryExport() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const dbConfig = JSON.parse(localStorage.getItem('dbConfig') || '{}')
    
    let filename = formData.get('output_filename') as string
    const format = formData.get('output_format') as string
    
    if (!filename.endsWith(`.${format}`)) {
      filename += `.${format}`
    }

    const exportData: ExportData = {
      query: formData.get('query') as string,
      output_filename: filename,
      output_format: format,
      db_config: dbConfig
    }

    try {
      setIsLoading(true)
      await axios.post(`${API_BASE_URL}/extract_${format}`, exportData, {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      })
      alert('Export completed successfully!')
    } catch (error) {
      alert(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="page-header">
        <h2>Query & Export Configuration</h2>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="form-header">
          <h3>Export Settings</h3>
        </div>

        <div className="form-body">
          <div className="form-group">
            <label htmlFor="query">SQL Query</label>
            <textarea
              id="query"
              name="query"
              required
              defaultValue="SELECT * FROM employees"
            />
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="output_filename">Output Filename</label>
              <input
                type="text"
                id="output_filename"
                name="output_filename"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="output_format">Output Format</label>
              <select
                id="output_format"
                name="output_format"
                required
                defaultValue="csv"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xml">XML</option>
                <option value="parquet">Parquet</option>
                <option value="sql">SQL</option>
              </select>
            </div>
          </div>
        </div>

        <div className="form-footer">
          <button
            type="button"
            className="secondary-btn"
            onClick={() => navigate('/')}
            disabled={isLoading}
          >
            Back
          </button>
          <button type="submit" className="generate-btn" disabled={isLoading}>
            {isLoading ? (
              <>
                <span className="loading-spinner" />
                Generating...
              </>
            ) : (
              'Generate Export'
            )}
          </button>
        </div>
      </form>
    </div>
  )
} 