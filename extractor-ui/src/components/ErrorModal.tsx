interface ErrorDetail {
  error: string
  message: string
  details: string
  suggestions: string[]
}

interface ErrorModalProps {
  isOpen: boolean
  error?: { detail: ErrorDetail }
  onClose: () => void
}

export function ErrorModal({ isOpen, error, onClose }: ErrorModalProps) {
  if (!isOpen || !error) return null

  return (
    <div className="modal-overlay">
      <div className="modal-content error-modal">
        <div className="error-modal-header">
          <h3>{error.detail.error}</h3>
        </div>
        <div className="error-modal-body">
          <p className="error-message">{error.detail.message}</p>
          {error.detail.suggestions.length > 0 && (
            <div className="error-suggestions">
              <h4>Suggestions:</h4>
              <ul>
                {error.detail.suggestions.map((suggestion, i) => (
                  <li key={i}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <button className="close-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  )
} 