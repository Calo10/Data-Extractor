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
  spark_config: {
    driver_memory: string
    executor_memory: string
    executor_cores: number
    shuffle_partitions: number
    default_parallelism: number
    off_heap_enabled: boolean
    off_heap_size: string
    fetch_size: number
    num_partitions: number
  }
}

export function QueryExport() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [queryError, setQueryError] = useState('')

  const validateQuery = (query: string) => {
    if (query.includes(';')) {
      setQueryError('SQL query should not contain semicolons (;)')
      return false
    }
    setQueryError('')
    return true
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const query = formData.get('query') as string
    
    if (!validateQuery(query)) {
      return
    }
    
    const dbConfig = JSON.parse(localStorage.getItem('dbConfig') || '{}')
    const sparkConfig = JSON.parse(localStorage.getItem('sparkConfig') || '{}')
    
    let filename = formData.get('output_filename') as string
    const format = formData.get('output_format') as string
    
    if (!filename.endsWith(`.${format}`)) {
      filename += `.${format}`
    }

    const exportData: ExportData = {
      query,
      output_filename: filename,
      output_format: format,
      db_config: dbConfig,
      spark_config: sparkConfig
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
              onChange={(e) => validateQuery(e.target.value)}
              className={queryError ? 'error' : ''}
            />
            {queryError && <div className="error-message">{queryError}</div>}
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