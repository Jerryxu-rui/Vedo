import { useState } from 'react'
import './Idea2Video.css'

interface GenerationStatus {
  status: 'idle' | 'processing' | 'completed' | 'error'
  progress: number
  message: string
  jobId?: string
}

function Idea2Video() {
  const [idea, setIdea] = useState('')
  const [style, setStyle] = useState('cinematic')
  const [duration, setDuration] = useState('30')
  const [generation, setGeneration] = useState<GenerationStatus>({
    status: 'idle',
    progress: 0,
    message: ''
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!idea.trim()) return

    setGeneration({
      status: 'processing',
      progress: 0,
      message: 'Initializing video generation...'
    })

    try {
      const response = await fetch('/api/v1/direct-pipeline/idea2video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          idea: idea,
          style: style,
          target_duration: parseInt(duration)
        })
      })

      if (!response.ok) {
        throw new Error('Failed to start generation')
      }

      const data = await response.json()
      
      setGeneration({
        status: 'processing',
        progress: 10,
        message: 'Video generation started. Processing your idea...',
        jobId: data.job_id
      })

      pollJobStatus(data.job_id)
    } catch (error) {
      setGeneration({
        status: 'error',
        progress: 0,
        message: 'Failed to start video generation. Please try again.'
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
        <h1>Idea to Video</h1>
        <p>Describe your video idea and let AI create it for you</p>
      </div>

      <div className="idea2video-layout">
        <div className="card input-section">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label">Your Video Idea</label>
              <textarea
                className="textarea"
                placeholder="Describe your video idea in detail. For example: 'A magical forest where glowing butterflies guide a lost child home. The atmosphere should be dreamlike with soft moonlight filtering through ancient trees.'"
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                rows={6}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="label">Visual Style</label>
                <select 
                  className="input"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                >
                  <option value="cinematic">Cinematic</option>
                  <option value="anime">Anime</option>
                  <option value="realistic">Realistic</option>
                  <option value="cartoon">Cartoon</option>
                  <option value="artistic">Artistic</option>
                </select>
              </div>

              <div className="form-group">
                <label className="label">Target Duration (seconds)</label>
                <select 
                  className="input"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                >
                  <option value="15">15 seconds</option>
                  <option value="30">30 seconds</option>
                  <option value="60">1 minute</option>
                  <option value="120">2 minutes</option>
                </select>
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary btn-full"
              disabled={!idea.trim() || generation.status === 'processing'}
            >
              {generation.status === 'processing' ? 'Generating...' : 'Generate Video'}
            </button>
          </form>
        </div>

        <div className="card status-section">
          <h3>Generation Status</h3>
          
          {generation.status === 'idle' && (
            <div className="status-idle">
              <div className="status-icon">🎬</div>
              <p>Enter your idea and click Generate to start creating your video</p>
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

export default Idea2Video
