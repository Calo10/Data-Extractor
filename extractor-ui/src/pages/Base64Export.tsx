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

interface Base64ExportData {
  table_name: string
  name_column: string
  file_column: string
  extension_column: string
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
  output_destination?: 'local' | 'ftp' | 'sftp'
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

export function Base64Export() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [showProgress, setShowProgress] = useState(false)
  const [progress, setProgress] = useState(0)
  const [exportStatus, setExportStatus] = useState('')
  const [jobSummary, setJobSummary] = useState<JobSummary | undefined>(undefined)
  const [error, setError] = useState<{ detail: ErrorDetail } | undefined>()
  const [selectedDestination, setSelectedDestination] = useState<'local' | 'ftp' | 'sftp'>('local')

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    
    const dbConfig = JSON.parse(localStorage.getItem('dbConfig') || '{}')
    const sparkConfig = JSON.parse(localStorage.getItem('sparkConfig') || '{}')

    const exportData: Base64ExportData = {
      table_name: formData.get('table_name') as string,
      name_column: formData.get('name_column') as string,
      file_column: formData.get('file_column') as string,
      extension_column: formData.get('extension_column') as string,
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
      setExportStatus('Initializing base64 export')
      setJobSummary(undefined)

      // Start base64 export
      const response = await axios.post<JobResponse>(
        `${API_BASE_URL}/download_files`, 
        exportData
      )
      const jobId = response.data.job_id

      // Poll status every second
      const statusInterval = setInterval(async () => {
        try {
          const statusResponse = await axios.get<StatusResponse>(`${API_BASE_URL}/file_download_status/${jobId}`)
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
                  const summaryResponse = await axios.get<JobSummary>(`${API_BASE_URL}/file_download_summary/${jobId}`)
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

  return (
    <div className="container">
      <div className="page-header">
        <h2>Base64 Export Configuration</h2>
      </div>

      <form onSubmit={handleSubmit} className="form-container">
        <div className="form-header">
          <h3>Base64 Export Settings</h3>
        </div>

        <div className="form-body">
          {/* Column Configuration Form */}
          <div className="form-section">
            <h4>Column Configuration</h4>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="table_name">Table Name</label>
                <input
                  type="text"
                  id="table_name"
                  name="table_name"
                  required
                  placeholder="e.g., documents"
                />
              </div>

              <div className="form-group">
                <label htmlFor="name_column">File Name Column</label>
                <input
                  type="text"
                  id="name_column"
                  name="name_column"
                  required
                  placeholder="e.g., filename"
                />
              </div>

              <div className="form-group">
                <label htmlFor="file_column">File Column</label>
                <input
                  type="text"
                  id="file_column"
                  name="file_column"
                  required
                  placeholder="e.g., file_data"
                />
              </div>

              <div className="form-group">
                <label htmlFor="extension_column">File Extension Column</label>
                <input
                  type="text"
                  id="extension_column"
                  name="extension_column"
                  required
                  placeholder="e.g., file_extension"
                />
              </div>
            </div>
          </div>

          {/* Output Destination */}
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
                Generating Base64 Export...
              </>
            ) : (
              'Generate Base64 Export'
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
    </div>
  )
} 