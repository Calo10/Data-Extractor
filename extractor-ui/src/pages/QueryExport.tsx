import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { ProgressModal } from '../components/ProgressModal'
import { ErrorModal } from '../components/ErrorModal'

const API_BASE_URL = 'http://localhost:8000'

interface FTPConfig {
  host: string
  port: number
  user: string
  password: string
  directory: string
  use_tls: boolean
  passive_mode: boolean
}

interface ExportData {
  query: string
  output_filename: string
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
  output_destination: 'local' | 'ftp' | 'sftp'
  ftp_config?: FTPConfig
}

interface PreviewData {
  status: string
  columns: string[]
  data: Record<string, any>[]
  row_count: number
}

interface JobResponse {
  job_id: string
}

interface JobStatus {
  progress: number
  status: string
}

interface JobSummary {
  job_id: string
  start_time: string
  end_time: string
  elapsed_time: number
  status: string
  total_records: number
  output_file: string
  format: string
  errors: string[]
  output_destination: 'local' | 'ftp' | 'sftp'
  ftp_config?: {
    host: string
    port: number
    user: string
    directory: string
    use_tls: boolean
    passive_mode: boolean
  }
}

interface ErrorDetail {
  error: string
  message: string
  details: string
  timestamp: string
  suggestions: string[]
}

type StatusResponse = JobStatus | { 
  detail: ErrorDetail
}

interface SavedQuery {
  name: string
  query: string
  created_at: string
}

export function QueryExport() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [queryError, setQueryError] = useState('')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [showProgress, setShowProgress] = useState(false)
  const [progress, setProgress] = useState(0)
  const [exportStatus, setExportStatus] = useState('')
  const [jobSummary, setJobSummary] = useState<JobSummary | undefined>(undefined)
  const [error, setError] = useState<{ detail: ErrorDetail } | undefined>()
  const [selectedDestination, setSelectedDestination] = useState<'local' | 'ftp' | 'sftp'>('local')
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>(() => {
    const saved = localStorage.getItem('savedQueries')
    return saved ? JSON.parse(saved) : []
  })

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
      setShowSaveDialog(true)
    } catch (error) {
      if (error && typeof error === 'object' && 'response' in error) {
        const errorData = (error as any).response.data
        setError({
          detail: {
            ...errorData.detail,
            suggestions: errorData.detail.suggestions || []
          }
        })
      } else {
        setError({
          detail: {
            error: 'Preview Error',
            message: error instanceof Error ? error.message : 'Unknown error occurred',
            details: '',
            timestamp: new Date().toISOString(),
            suggestions: []
          }
        })
      }
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
      db_config: dbConfig,
      spark_config: sparkConfig,
      output_destination: formData.get('output_destination') as 'local' | 'ftp' | 'sftp'
    }

    // Add FTP config if FTP is selected
    if (exportData.output_destination === 'ftp') {
      exportData.ftp_config = {
        host: formData.get('ftp_host') as string,
        port: parseInt(formData.get('ftp_port') as string),
        user: formData.get('ftp_user') as string,
        password: formData.get('ftp_password') as string,
        directory: formData.get('ftp_directory') as string,
        use_tls: formData.get('use_tls') === 'on',
        passive_mode: formData.get('passive_mode') === 'on'
      }
    }

    // Store FTP config in state if selected
    const ftpConfig = exportData.output_destination === 'ftp' ? exportData.ftp_config : undefined
    
    try {
      setIsLoading(true)
      setShowProgress(true)
      setProgress(0)
      setExportStatus('Initializing export')
      setJobSummary(undefined)  // Reset summary

      // Start export - use format-specific endpoint
      const response = await axios.post<JobResponse>(
        `${API_BASE_URL}/extract_${format}`, 
        exportData
      )
      const jobId = response.data.job_id

      // Poll status every second
      const statusInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get<StatusResponse>(`${API_BASE_URL}/status/${jobId}`)
          const status = statusResponse.data
          
          if ('detail' in status) {
            clearInterval(statusInterval)
            setShowProgress(false)
            setIsLoading(false)
            setError({
              detail: {
                ...status.detail,
                suggestions: []
              }
            })
          } else if (isJobStatus(status)) {
            setProgress(status.progress)
            setExportStatus(status.status)
            
            if (status.progress >= 100 || status.status === 'completed') {
              clearInterval(statusInterval)
              setIsLoading(false)
              
              setTimeout(async () => {
                try {
                  const summaryResponse = await axios.get<JobSummary>(`${API_BASE_URL}/summary/${jobId}`)
                  // Add the FTP config and destination to the summary
                  setJobSummary({
                    ...summaryResponse.data,
                    output_destination: exportData.output_destination,
                    ftp_config: ftpConfig
                  })
                } catch (error) {
                  console.error('Failed to fetch job summary:', error)
                }
              }, 3000)
            }
          }
        } catch (error) {
          clearInterval(statusInterval)
          setShowProgress(false)
          setIsLoading(false)
          
          if (error && typeof error === 'object' && 'response' in error) {
            const errorData = (error as any).response.data
            setError({
              detail: {
                ...errorData.detail,
                suggestions: []
              }
            })
          }
        }
      }, 1000)

    } catch (error) {
      setShowProgress(false)
      setIsLoading(false)
      
      if (error && typeof error === 'object' && 'response' in error) {
        setError((error as any).response.data)
      }
    }
  }

  const handleCloseModal = () => {
    setShowProgress(false)
    setJobSummary(undefined)
  }

  const isJobStatus = (data: any): data is JobStatus => {
    return 'progress' in data && 'status' in data
  }

  const handleSaveQuery = (name: string, query: string) => {
    const newQuery: SavedQuery = {
      name,
      query,
      created_at: new Date().toISOString()
    }
    
    const updatedQueries = [...savedQueries, newQuery]
    setSavedQueries(updatedQueries)
    localStorage.setItem('savedQueries', JSON.stringify(updatedQueries))
    setShowSaveDialog(false)
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

          <div className="form-section">
            <label className="section-label">Output Destination</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="output_destination"
                  value="local"
                  defaultChecked
                  onChange={(e) => setSelectedDestination(e.target.value as 'local' | 'ftp' | 'sftp')}
                />
                Local
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="output_destination"
                  value="ftp"
                  onChange={(e) => setSelectedDestination(e.target.value as 'local' | 'ftp' | 'sftp')}
                />
                FTP
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="output_destination"
                  value="sftp"
                  onChange={(e) => setSelectedDestination(e.target.value as 'local' | 'ftp' | 'sftp')}
                />
                SFTP
              </label>
            </div>

            {/* FTP Configuration Form */}
            {selectedDestination === 'ftp' && (
              <div className="ftp-config">
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="ftp_host">Host</label>
                    <input
                      type="text"
                      id="ftp_host"
                      name="ftp_host"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_port">Port</label>
                    <input
                      type="number"
                      id="ftp_port"
                      name="ftp_port"
                      defaultValue={21}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_user">Username</label>
                    <input
                      type="text"
                      id="ftp_user"
                      name="ftp_user"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_password">Password</label>
                    <input
                      type="password"
                      id="ftp_password"
                      name="ftp_password"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_directory">Directory</label>
                    <input
                      type="text"
                      id="ftp_directory"
                      name="ftp_directory"
                      defaultValue="/"
                      required
                    />
                  </div>
                  <div className="form-group checkboxes">
                    <label>
                      <input
                        type="checkbox"
                        name="use_tls"
                        defaultChecked
                      />
                      Use TLS
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        name="passive_mode"
                        defaultChecked
                      />
                      Passive Mode
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="form-footer">
          <button
            type="button"
            className="secondary-btn"
            onClick={() => navigate('/spark')}
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

      <ProgressModal 
        isOpen={showProgress}
        progress={progress}
        status={exportStatus}
        summary={jobSummary}
        onClose={handleCloseModal}
      />
      <ErrorModal 
        isOpen={!!error}
        error={error}
        onClose={() => setError(undefined)}
      />

      {showSaveDialog && previewData && (
        <div className="modal-overlay">
          <div className="modal-content save-query-modal">
            <div className="modal-header">
              <h3>Save Query</h3>
            </div>
            <form onSubmit={(e) => {
              e.preventDefault()
              const name = new FormData(e.currentTarget).get('queryName') as string
              const query = (document.querySelector('#query') as HTMLTextAreaElement).value
              handleSaveQuery(name, query)
            }}>
              <div className="form-group">
                <label htmlFor="queryName">Query Name</label>
                <input 
                  type="text" 
                  id="queryName" 
                  name="queryName" 
                  required 
                  placeholder="Enter a name for this query"
                />
              </div>
              <div className="modal-footer">
                <button type="button" className="secondary-btn" onClick={() => setShowSaveDialog(false)}>
                  Cancel
                </button>
                <button type="submit" className="generate-btn">
                  Save Query
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add saved queries dropdown */}
      <div className="form-group">
        <label htmlFor="savedQueries">Saved Queries</label>
        <select 
          id="savedQueries" 
          onChange={(e) => {
            if (e.target.value) {
              const selected = savedQueries.find(q => q.name === e.target.value)
              if (selected) {
                const textarea = document.querySelector('#query') as HTMLTextAreaElement
                textarea.value = selected.query
                setPreviewData(null)  // Clear preview data when switching queries
              }
            }
          }}
        >
          <option value="">Select a saved query</option>
          {savedQueries.map(query => (
            <option key={query.name} value={query.name}>
              {query.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}