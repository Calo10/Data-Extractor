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

interface PreviewData {
  status: string
  columns: string[]
  data: Record<string, any>[]
  row_count: number
}

export function QueryExport() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [queryError, setQueryError] = useState('')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)

  const validateQuery = (query: string) => {
    if (query.includes(';')) {
      setQueryError('SQL query should not contain semicolons (;)')
      return false
    }
    setQueryError('')
    return true
  }

  const handlePreview = async (query: string) => {
    const dbConfig = JSON.parse(localStorage.getItem('dbConfig') || '{}')
    
    try {
      setIsPreviewLoading(true)
      const response = await axios.post(`${API_BASE_URL}/preview`, {
        query,
        db_config: dbConfig
      })
      setPreviewData(response.data as PreviewData)
    } catch (error) {
      alert(`Preview failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsPreviewLoading(false)
    }
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
            <button
              type="button"
              className="secondary-btn preview-btn"
              onClick={() => handlePreview(document.querySelector<HTMLTextAreaElement>('#query')?.value || '')}
              disabled={isPreviewLoading || !!queryError}
            >
              {isPreviewLoading ? 'Loading Preview...' : 'Preview Results'}
            </button>
          </div>

          {previewData && (
            <div className="preview-table-container">
              <h4>Query Preview ({previewData.row_count} rows)</h4>
              <div className="table-wrapper">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {previewData.columns.map((column, i) => (
                        <th key={i}>{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.data.map((row, i) => (
                      <tr key={i}>
                        {previewData.columns.map((column, j) => (
                          <td key={j}>{row[column]?.toString() ?? 'null'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

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