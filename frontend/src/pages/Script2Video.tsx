import { useState } from 'react'
import './Script2Video.css'

interface GenerationStatus {
  status: 'idle' | 'processing' | 'completed' | 'error'
  progress: number
  message: string
  jobId?: string
}

function Script2Video() {
  const [script, setScript] = useState('')
  const [uploadMode, setUploadMode] = useState<'paste' | 'upload'>('paste')
  const [fileName, setFileName] = useState('')
  const [generation, setGeneration] = useState<GenerationStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  })

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setFileName(file.name)
    
    const text = await file.text()
    setScript(text)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!script.trim()) return

    setGeneration({
      status: 'processing',
      progress: 0,
      message: 'Analyzing your script...'
    })

    try {
      const response = await fetch('/api/v1/direct-pipeline/script2video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          script: script
        })
      })

      if (!response.ok) {
        throw new Error('Failed to start generation')
      }

      const data = await response.json()
      
      setGeneration({
        status: 'processing',
        progress: 10,
        message: 'Script analysis complete. Extracting characters...',
        jobId: data.job_id
      })

      pollJobStatus(data.job_id)
    } catch (error) {
      setGeneration({
        status: 'error',
        progress: 0,
        message: 'Failed to process script. Please check your input and try again.'
      })
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/v1/jobs/${jobId}`)
        if (!response.ok) return

        const data = await response.json()
        
        const progress = Math.min(data.progress || 0, 100)
        
        if (data.status === 'completed') {
          setGeneration({
            status: 'completed',
            progress: 100,
            message: 'Video generation completed!',
            jobId
          })
        } else if (data.status === 'failed') {
          setGeneration({
            status: 'error',
            progress: progress,
            message: data.error || 'Generation failed',
            jobId
          })
        } else {
          setGeneration({
            status: 'processing',
            progress: progress,
            message: data.current_step || 'Processing...',
            jobId
          })
          setTimeout(checkStatus, 3000)
        }
      } catch {
        setTimeout(checkStatus, 5000)
      }
    }

    checkStatus()
  }

  return (
    <div className="container">
      <div className="page-header">
        <h1>Script to Video</h1>
        <p>Upload or paste your script and convert it to video</p>
      </div>

      <div className="script2video-layout">
        <div className="card input-section">
          <div className="mode-toggle">
            <button 
              className={`mode-btn ${uploadMode === 'paste' ? 'active' : ''}`}
              onClick={() => setUploadMode('paste')}
            >
              Paste Script
            </button>
            <button 
              className={`mode-btn ${uploadMode === 'upload' ? 'active' : ''}`}
              onClick={() => setUploadMode('upload')}
            >
              Upload File
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {uploadMode === 'upload' ? (
              <div className="form-group">
                <label className="label">Script File</label>
                <div className="file-upload">
                  <input 
                    type="file" 
                    accept=".txt,.md,.doc,.docx"
                    onChange={handleFileUpload}
                    id="script-file"
                  />
                  <label htmlFor="script-file" className="file-upload-label">
                    <span className="file-icon">📄</span>
                    {fileName ? fileName : 'Click to upload or drag and drop'}
                  </label>
                </div>
                {script && (
                  <div className="script-preview">
                    <label className="label">Preview</label>
                    <pre>{script.slice(0, 500)}{script.length > 500 ? '...' : ''}</pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="form-group">
                <label className="label">Your Script</label>
                <textarea
                  className="textarea script-textarea"
                  placeholder="Paste your complete script here. Include scene descriptions, dialogue, and any character information..."
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  rows={15}
                />
              </div>
            )}

            <button 
              type="submit" 
              className="btn btn-primary btn-full"
              disabled={!script.trim() || generation.status === 'processing'}
            >
              {generation.status === 'processing' ? 'Processing...' : 'Generate Video'}
            </button>
          </form>
        </div>

        <div className="card status-section">
          <h3>Generation Progress</h3>
          
          {generation.status === 'idle' && (
            <div className="status-idle">
              <div className="status-icon">📝</div>
              <p>Upload or paste your script to begin</p>
            </div>
          )}

          {generation.status === 'processing' && (
            <div className="status-processing">
              <div className="status-badge status-processing">Processing</div>
              <div className="progress-container">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${generation.progress}%` }}
                  />
                </div>
                <span className="progress-text">{generation.progress}%</span>
              </div>
              <p className="status-message">{generation.message}</p>
              
              <div className="process-steps">
                <div className={`process-step ${generation.progress >= 10 ? 'active' : ''}`}>
                  <span className="step-icon">✓</span>
                  <span>Script Analysis</span>
                </div>
                <div className={`process-step ${generation.progress >= 30 ? 'active' : ''}`}>
                  <span className="step-icon">✓</span>
                  <span>Character Extraction</span>
                </div>
                <div className={`process-step ${generation.progress >= 50 ? 'active' : ''}`}>
                  <span className="step-icon">✓</span>
                  <span>Portrait Generation</span>
                </div>
                <div className={`process-step ${generation.progress >= 70 ? 'active' : ''}`}>
                  <span className="step-icon">✓</span>
                  <span>Storyboard Creation</span>
                </div>
                <div className={`process-step ${generation.progress >= 90 ? 'active' : ''}`}>
                  <span className="step-icon">✓</span>
                  <span>Video Generation</span>
                </div>
              </div>
            </div>
          )}

          {generation.status === 'completed' && (
            <div className="status-completed">
              <div className="status-badge status-completed">Completed</div>
              <div className="status-icon success">✓</div>
              <p>{generation.message}</p>
              <a 
                href={`/api/v1/videos/episode/${generation.jobId}/download`}
                className="btn btn-primary"
              >
                Download Video
              </a>
            </div>
          )}

          {generation.status === 'error' && (
            <div className="status-error">
              <div className="status-badge status-error">Error</div>
              <p>{generation.message}</p>
              <button 
                className="btn btn-secondary"
                onClick={() => setGeneration({ status: 'idle', progress: 0, message: '' })}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Script2Video
