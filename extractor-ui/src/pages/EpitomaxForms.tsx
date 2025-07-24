import { useState } from 'react'
import { ProgressModal } from '../components/ProgressModal'

const API_BASE_URL = 'http://localhost:8000'

interface PreviewData {
  status: string
  columns: string[]
  data: Record<string, any>[]
  row_count: number
}

interface FTPConfig {
  host: string
  port: number
  user: string
  password: string
  directory: string
  use_tls: boolean
  passive_mode: boolean
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
  output_destination?: 'local' | 'ftp'
  ftp_config?: FTPConfig
}

export function EpitomaxForms() {
  const [user, setUser] = useState('')
  const [password, setPassword] = useState('')
  const [url, setUrl] = useState('')
  const [outputDestination, setOutputDestination] = useState<'local' | 'ftp'>('local')
  const [ftpConfig, setFtpConfig] = useState<FTPConfig>({
    host: '',
    port: 21,
    user: '',
    password: '',
    directory: '/',
    use_tls: false,
    passive_mode: true
  })
  const [authTriggered, setAuthTriggered] = useState(false)
  const [query, setQuery] = useState('SELECT * FROM my_table')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [showProgress, setShowProgress] = useState(false)
  const [progress, setProgress] = useState(0)
  const [jobStatus, setJobStatus] = useState('')
  const [jobSummary, setJobSummary] = useState<JobSummary | undefined>(undefined)
  const [error, setError] = useState<string | undefined>()

  const handleAuth = async () => {
    if (!user || !password || !url) {
      alert('Please enter user, password, and url.')
      return
    }
    setError(undefined)
    setShowProgress(false)
    setJobSummary(undefined)
    setProgress(0)
    setJobStatus('')
    setAuthTriggered(false)
    try {
      const payload: any = {
        username: user,
        password,
        url,
        output_destination: outputDestination
      }
      if (outputDestination === 'ftp') {
        payload.ftp_config = ftpConfig
      }
      const response = await fetch(`${API_BASE_URL}/DownloadEpitomaxFormsSelenium`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!response.ok) throw new Error(`Auth failed: ${response.status} ${response.statusText}`)
      const data: JobResponse = await response.json()
      const jobId = data.job_id
      setShowProgress(true)
      setProgress(0)
      setJobStatus('Initializing...')
      setAuthTriggered(true)
      // Poll status
      const statusInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/epitomax_status/${jobId}`)
          const statusData: JobStatus = await statusResponse.json()
          setProgress(statusData.progress)
          setJobStatus(statusData.status)
          if (statusData.progress >= 100 || statusData.status === 'completed') {
            clearInterval(statusInterval)
            setShowProgress(true)
            setProgress(100)
            setJobStatus('Completed')
            setTimeout(async () => {
              try {
                const summaryResponse = await fetch(`${API_BASE_URL}/epitomax_summary/${jobId}`)
                const summaryData: JobSummary = await summaryResponse.json()
                setJobSummary(summaryData)
              } catch (err) {
                setError('Failed to fetch summary')
              }
            }, 2000)
          }
        } catch (err) {
          clearInterval(statusInterval)
          setShowProgress(false)
          setError('Failed to fetch status')
        }
      }, 1000)
    } catch (err: any) {
      setError('Error: ' + (err.message || err))
    }
  }

  const handleCloseModal = () => {
    setShowProgress(false)
    setJobSummary(undefined)
    setProgress(0)
    setJobStatus('')
  }

  const handlePreview = async () => {
    setIsPreviewLoading(true)
    setPreviewError(null)
    setPreviewData(null)
    try {
      const dbConfig = JSON.parse(localStorage.getItem('dbConfig') || '{}')
      const response = await fetch(`${API_BASE_URL}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, db_config: dbConfig })
      })
      if (!response.ok) {
        throw new Error(`Preview failed: ${response.status} ${response.statusText}`)
      }
      const data = await response.json()
      setPreviewData(data)
    } catch (err: any) {
      setPreviewError(err.message || 'Unknown error')
    }
    setIsPreviewLoading(false)
  }

  return (
    <div className="container">
      <div className="page-header">
        <h2>Epitomax Forms Access</h2>
      </div>
      <form className="form-container" onSubmit={e => e.preventDefault()}>
        <div className="form-body">
          <div className="form-group">
            <label htmlFor="epitomax-user">User</label>
            <input
              id="epitomax-user"
              type="text"
              value={user}
              onChange={e => setUser(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="epitomax-password">Password</label>
            <input
              id="epitomax-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="epitomax-url">URL</label>
            <input
              id="epitomax-url"
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              required
            />
          </div>
          <div className="form-section">
            <label className="section-label">Output Destination</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="output_destination"
                  value="local"
                  checked={outputDestination === 'local'}
                  onChange={() => setOutputDestination('local')}
                />
                Local
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="output_destination"
                  value="ftp"
                  checked={outputDestination === 'ftp'}
                  onChange={() => setOutputDestination('ftp')}
                />
                FTP
              </label>
            </div>
            {outputDestination === 'ftp' && (
              <div className="ftp-config">
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="ftp_host">Host</label>
                    <input
                      type="text"
                      id="ftp_host"
                      name="ftp_host"
                      value={ftpConfig.host}
                      onChange={e => setFtpConfig({ ...ftpConfig, host: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_port">Port</label>
                    <input
                      type="number"
                      id="ftp_port"
                      name="ftp_port"
                      value={ftpConfig.port}
                      onChange={e => setFtpConfig({ ...ftpConfig, port: Number(e.target.value) })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_user">Username</label>
                    <input
                      type="text"
                      id="ftp_user"
                      name="ftp_user"
                      value={ftpConfig.user}
                      onChange={e => setFtpConfig({ ...ftpConfig, user: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_password">Password</label>
                    <input
                      type="password"
                      id="ftp_password"
                      name="ftp_password"
                      value={ftpConfig.password}
                      onChange={e => setFtpConfig({ ...ftpConfig, password: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="ftp_directory">Directory</label>
                    <input
                      type="text"
                      id="ftp_directory"
                      name="ftp_directory"
                      value={ftpConfig.directory}
                      onChange={e => setFtpConfig({ ...ftpConfig, directory: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group checkboxes">
                    <label>
                      <input
                        type="checkbox"
                        name="use_tls"
                        checked={ftpConfig.use_tls}
                        onChange={e => setFtpConfig({ ...ftpConfig, use_tls: e.target.checked })}
                      />
                      Use TLS
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        name="passive_mode"
                        checked={ftpConfig.passive_mode}
                        onChange={e => setFtpConfig({ ...ftpConfig, passive_mode: e.target.checked })}
                      />
                      Passive Mode
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="form-group">
            <button
              type="button"
              className="generate-btn"
              onClick={handleAuth}
              disabled={!user || !password || !url || (outputDestination === 'ftp' && (!ftpConfig.host || !ftpConfig.user || !ftpConfig.password || !ftpConfig.directory))}
            >
              Download
            </button>
            {error && <div style={{ marginTop: 12, color: 'red' }}>{error}</div>}
          </div>
          <div className="form-group">
            <label htmlFor="epitomax-query">SQL Query</label>
            <textarea
              id="epitomax-query"
              className="query-textarea"
              value={query}
              onChange={e => setQuery(e.target.value)}
              rows={4}
              required
            />
            <button
              type="button"
              className="secondary-btn"
              onClick={handlePreview}
              disabled={isPreviewLoading || !query.trim()}
              style={{ marginTop: 16 }}
            >
              {isPreviewLoading ? 'Loading Preview...' : 'Preview Results'}
            </button>
            {previewError && <div className="error-message" style={{ marginTop: 8 }}>{previewError}</div>}
            {previewData && (
              <div className="preview-table-container" style={{ marginTop: 24 }}>
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
          </div>
        </div>
      </form>
      <ProgressModal
        isOpen={showProgress}
        progress={progress}
        status={jobStatus}
        summary={jobSummary}
        onClose={handleCloseModal}
      />
    </div>
  )
} 